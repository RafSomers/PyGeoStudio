"""
Analysis advanced
===============
- Checking materials in geofile
- Testing assigning materials to regions via Context

"""

# %%
# Open example GeoStudio study
import PyGeoStudio as pgs

# Work folder main path
main_path = "C:/Users/WQ5783/OneDrive - ENGIE/5_PyProjects/PyGeoStudio"

# Load GSZ file
src_file = "examples/GeoStudio_files/Test1-SEEP-model_Schelde_T4000_NoClay.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)

# Show tree
geofile.showAnalysisTree()

# Show properties first analysis
analysis = geofile.getAnalysisByID(1)
print(analysis.getAllProperties())

# Show materials
geofile.showMaterials()

# Grab a material in python
mat_1 = geofile.getMaterialByID(1)
print(mat_1)

# Materials & Hydraulic boundary conditions are linked to geometry in object 'analysis.data["Context"]'
context = analysis.data["Context"]
geometry = geofile.getGeometryByID(1)
if "GeometryUsesMaterials" not in context.data:
  print("No materials assigned to regions. Only geometry is shown.")
else:
  mat_ids_used_per_region = context.data["GeometryUsesMaterials"]
  for reg, mat_id in mat_ids_used_per_region.items():
      print(reg)
      print("Material:", mat_id)
      pts = geometry["Regions"][reg][0]
      print("Point numbers:", pts)

# Show problem with regions colored based on mat_id (uses 'draw' from Geometry.py)
analysis.showProblem()

# Change material of inner dike (= Region-4) to Clay (Drained) with ID = 3
mat_ids_used_per_region['Regions-4'] = 3
print(mat_ids_used_per_region)
analysis.showProblem()

# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/Test-adv-1-SEEP-model_Schelde_T4000.gsz"
geofile.saveAs(main_path+"/"+out_file)

print("End script!")