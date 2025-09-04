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

# Show boundary conditions
geofile.showBoundaryConditions()

# Materials & Hydraulic boundary conditions are linked to geometry in object 'analysis.data["Context"]'
context = analysis.data["Context"]
geometry = geofile.getGeometryByID(1)
mat_ids_used_per_region = context.data["GeometryUsesMaterials"]
for reg, mat_id in mat_ids_used_per_region.items():
    print(reg)
    pts = geometry["Regions"][reg][0]
    print("Point numbers:", pts)
    print("Material:", mat_id)

hydBC_ids_used_per_line = context.data["GeometryUsesHydraulicBCs"]
for ln, hydBC_id in hydBC_ids_used_per_line.items():
    print(ln)
    pt_ids = geometry["Lines"][int(ln.split('-')[1])-1]
    pt_nums = [int(id + 1) for id in pt_ids]
    print("Point numbers:", pt_nums)
    print("HydraulicBC:", hydBC_id)


# Show problem with regions colored based on mat_id (uses 'draw' from Geometry.py)
analysis.showProblem()

# Change material of inner dike (= Region-4) to Clay (Drained) with ID = 3
mat_ids_used_per_region['Regions-4'] = 3
print(mat_ids_used_per_region)

# Change boundary condition of landside (= Lines-4) to Drainage with ID = 5
hydBC_ids_used_per_line['Lines-4'] = 5
print(hydBC_ids_used_per_line)

# Show problem again with regions colored based on mat_id (uses 'draw' from Geometry.py)
analysis.showProblem()

# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/Test2_mat_hydbc_out.gsz"
geofile.saveAs(main_path+"/"+out_file)

print("End script!")