"""
Delete geometry and make new one
=================================

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
# Show the geometries defined in the study and select the one with ID 1 to draw & list it
geofile.showGeometries()
geometry = geofile.getGeometryByID(1)
geometry.draw(listProperties=True)
geometry.delete()
geometry.listProperties()
geometry.draw()

# Add new point
geometry.addPoints([[0, 0], [0,1], [1,1]])
geometry.addLines([[1, 2], [2, 3], [3,1]])
geometry.addRegions([1, 2, 3])
geometry.draw(listProperties=True)

# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/test-new-geom.gsz"
geofile.saveAs(main_path+"/"+out_file)