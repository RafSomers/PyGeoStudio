# This file is part of PyGeoStudio, an interface to GeoStudio 
# hydrogeotechnical software.
# Copyright (C) 2023, Moïse Rousseau
# 
# PyGeoStudio is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# PyGeoStudio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import numpy as np
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
from prettytable import PrettyTable

from .BasePropertiesClass import BasePropertiesClass
from .Results import Results


# Note in the GeoStudioFile, material distribution / BC are defined through a Context element.
# We add it in this class because their is one context per analysis...


class TimeIncrements(BasePropertiesClass):
  """
  TimeIncrement holds the time for which the simulation results must be saved
  
  :param Start: Starting time of the simulation
  :type Start: float
  :param Duration: Duration of the simulation
  :type Duration: float
  :param IncrementOption: `Exponential` or `Linear` timesteps
  :type IncrementOption: str
  :param IncrementCount: Number of timesteps
  :type IncrementCount: int
  :param InitialIncrementSize: If `Exponential`, size of the first increment
  :type InitialIncrementSize: float
  :param SaveMultiplesOf: Saving each timestep
  :type SaveMultiplesOf: int
  :param TimeSteps: Timesteps dictionnary
  :type TimeSteps: dict
  """
  parameter_type = {
    "Start" : float,
    "Duration" : float, #total duration of the simulation
    "IncrementOption" : str, #Exponential
    "IncrementCount" : int,
    "InitialIncrementSize" : float,
    "SaveMultiplesOf" : int,
    "TimeSteps" : list,
  }
  
  def read(self, et):
    """
    Read the XML element tree and populate the class
    """
    for prop in et:
      if prop.tag == "TimeSteps":
        if "TimeSteps" not in self.data.keys(): self.data["TimeSteps"] = []
        n = int(prop.attrib["Len"])
        for i,time in enumerate(prop):
          self.data["TimeSteps"].append(dict(time.attrib))
      else:
        self.data[prop.tag] = prop.text
    return
  
  def __write__(self, et):
    for tag,val in self.data.items():
      if tag == "TimeSteps":
        sub = ET.SubElement(et, tag)
        sub.attrib = {"Len" : str(len(self.data[tag]))}
        for time in self.data["TimeSteps"]:
          sub_time = ET.SubElement(sub, "TimeStep")
          sub_time.attrib = time
        continue
      if tag in self.parameter_type.keys() and self.parameter_type[tag] is None:
        sub = ET.SubElement(et, tag)
        val.__write__(sub)
        continue
      sub = ET.SubElement(et, tag)
      sub.text = val
    return

  def showTimeSteps(self):
    """
    Print a pretty looking table showing simulation timestepping.
    """
    res = PrettyTable()
    res.field_names = ["ID", "Step size","Time","Saved"]
    res.add_row(["0", "", "0", ""])
    for i,x in enumerate(self.data["TimeSteps"]):
      res.add_row([
        str(i+1),
        x['Step'],
        x['ElapsedTime'],
        str(x.get('Save',"false")),
      ])
    print(res)
    return
  
  def getSavedTimeStep(self):
    """
    Return the list of saved timesteps
    """
    return [float(x["ElapsedTime"]) for x in self.data["TimeSteps"] if x["Save"]]

  def getTimeStep(self):
    """
    Return the list of all timesteps
    """
    return [float(x["ElapsedTime"]) for x in self.data["TimeSteps"]]

  def setTimeSteps(self, timesteps, saved):
    """
    Set simulation timestep
    
    :param timesteps: Timestep times. Can be unsorted. Must NOT include the starting time.
    :type timesteps: list
    :param saved: If true, the timestep will be saved in simulation
    :type saved: list (same size as `timesteps`)
    """
    if len(timesteps) != len(saved):
      raise ValueError("timestep and saved parameter must be of the same size")
    indices = np.argsort(timesteps)
    timesteps_ = np.array(timesteps)[indices]
    saved_ = np.array(saved)[indices]
    start = self.data.get("Start", 0)
    res = []
    temp = {
      "Step" : str(timesteps_[0]-start),
      "ElapsedTime" : str(timesteps_[0]),
    }
    if saved_[0]: temp["Save"] = "true"
    res.append(temp)
    for i in range(1, len(timesteps)):
      temp = {
        "Step" : str(timesteps_[i]-timesteps_[i-1]),
        "ElapsedTime" : str(timesteps_[i]),
      }
      if saved_[i]: temp["Save"] = "true"
      res.append(temp)
    self.data["IncrementCount"] = str(len(timesteps))
    self.data["TimeSteps"] = res
    return


class Analysis(BasePropertiesClass):
  """
  :param ID: Index of the analysis in GeoStudio file
  :type ID: int
  :param Name: Name of the analysis in GeoStudio file
  :type Name: str
  :param Kind: Type of analysis (SEEP or SLOPE)
  :type Kind: str
  :param Description: More information about the analysis
  :type Description: str
  :param ParentID: Index of the parent analysis in GeoStudio file
  :type ParentID: int
  :param Method:
  :type Method: str
  :param GeometryId: Index of the Geometry of the analysis in GeoStudio file. Handle automatically by PyGeoStudio. Do not change until you know what you are doing.
  :type GeometryId: str
  :param Geometry: Geometry of the analysis. Use the method ``setGeometry()`` below to change this property.
  :type Geometry: Geometry object
  :param Context: Boundary condition and material distribution coupler. Use the method ``setContext()`` below to change this property.
  :type Context: Context object
  :param ExcludeInitDeformation:
  :type ExcludeInitDeformation: bool
  :param Results: Interface to analysis results
  :type Results: Results object
  :param TimeIncrements: Timestepping control 
  :type TimeIncrements: TimeIncrements object
  :param ComputedPhysics:
  :type ComputedPhysics: dict
  :param PhysicsOptions:
  :type PhysicsOptions: dict
  """
  parameter_type = {
    "ID" : int,
    "Name" : str,
    "Kind" : str,
    "Description": str,
    "ParentID" : int,
    "Method" : str,
    "GeometryId" : int,
    "Geometry" : None,
    "Context" : None,
    "ExcludeInitDeformation" : bool,
    "Results": Results,
    "TimeIncrements" : TimeIncrements,
    "ComputedPhysics" : dict,
    "PhysicsOptions" : dict,
#      "ConvergenceCriteria" : None,
#      "IterationControls" : None,
#      "UnderRelaxationCriteria" : None,
  }
  my_data = ["Geometry", "Context", "Results"]
  
  def __repr__(self):
    res = f"<PyGeoStudio.Analysis object, (ID: {self.data['ID']}, Name: \"{self.data['Name']}\")>"
    return res
  
  def setGeometry(self, geom):
    """
    Set a new geometry to the analysis
    
    :param geom: The new geometry of the analysis
    :type geom: Geometry object
    """
    self.data["Geometry"] = geom   # pointer toward the geometry, so we can access the geometry defined in this class
    self.data["GeometryID"] = geom.data["ID"]
    return
  
  def setContext(self, context):
    """
    Set a new material distribution and boundary conditions to the analysis
    
    :param geom: The new material distribution and boundary condition of the analysis
    :type geom: Context object
    """
    self.context = context
    return

  def showProblem(self):
    """
    Plot the conceptual problem defined in the analysis (with material distribution)
    """
    if "Geometry" not in self.data:
      print("No geometry defined, thus can't show problem.")
      return
    fig, ax = self.data["Geometry"].draw(show=False)

    if "Context" not in self.data:
      raise KeyError("Analysis not properly defined. 'Context' is not available in data.")

    context = self.data["Context"]
    if "GeometryUsesMaterials" not in context.data:
      print("No materials assigned to regions. Only geometry is shown.")
    else:
      mat_ids_used_per_region = context.data["GeometryUsesMaterials"]
      cmap = plt.get_cmap('tab20', np.max(list(mat_ids_used_per_region.values())))
      for reg, mat_id in mat_ids_used_per_region.items():
        pts = self["Geometry"]["Regions"][reg][0]
        X_pts = [self["Geometry"]["Points"][x-1,0] for x in pts]
        Y_pts = [self["Geometry"]["Points"][x-1,1] for x in pts]
        ax.fill(X_pts, Y_pts,color=cmap(mat_id-1))

    plt.show()
    return
