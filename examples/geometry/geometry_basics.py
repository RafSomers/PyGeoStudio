"""
Geometry basics
===============

"""

# %%
# Open example GeoStudio study
import PyGeoStudio as pgs

# Check main path
main_path = "/"

# Open file
src_file = "examples/GeoStudio_files/test.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)

# %%
# Show the geometries defined in the study and select the one with ID 1 to draw it
geofile.showGeometries()
geometry = geofile.getGeometryByID(1)
geometry.listProperties()
geometry.draw()


# %%
# Add new point
geometry.addPoints([[2, 0], [3, 0], [2.5, -0.5]],["A", "B", "C"])
geometry.draw(listProperties=True)

# %%
# Add new region from point IDs:
new_region = [7, 8, 9]
geometry.addRegions(new_region)
geometry.draw(listProperties=True)

# %%
# Create new region directly from point IDs:


# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/test-basics-geom.gsz"
geofile.saveAs(main_path+"/"+out_file)
  
