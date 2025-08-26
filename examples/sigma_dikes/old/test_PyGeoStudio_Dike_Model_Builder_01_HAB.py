"""
Testing pgs_dike_Model_Builder
===============

"""

# %%
# Open example GeoStudio study
import importlib
import matplotlib.pyplot as plt
import PyGeoStudio as pgs
import pgs_dike_modelbuilder as pgs_mb

# Check main path
main_path = r"C:\Users\XZ6583\Desktop\Work Docs\Sigma 3.0\pythonProject\PyGeoStudio-main"

# Open file
src_file = "examples/GeoStudio_files/test.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)

# Delete all
geofile.showGeometries()
geometry = geofile.getGeometryByID(1)
geometry.delete()

geometry.listProperties()

# Get dike basic points
quantile_excel_filepath = r"C:\Users\XZ6583\Desktop\Work Docs\Sigma 3.0\pythonProject\PyGeoStudio-main\examples\sigma_dikes" + "/" + "cross_sections_schelde_quantiles.xlsx"
profile_pt_table, profile_pts, profile_notes = pgs_mb.get_profile_points_from_quantile_excel(quantile_excel_filepath, 0.50)


# Make landside horizontal
profile_pts = pgs_mb.make_landside_horizontal(profile_pts)

# Set water levels and cover thickness
low_wl, high_wl = 0.23, 5.65
cover_t = 0.5

# Soil levels
b1, b2, b3 = pgs_mb.soil_levels(profile_pts, "s1", low_wl)
print("soil levels:", b1, b2, b3)

# Creqte cover lqyer
cover_inside_pts = pgs_mb.calc_cover_layer_points(profile_pts, 0.5, low_wl, high_wl, b1, b2)

"""
# Add extra points to surface points
low_wl, high_wl = 0.23, 5.65
profile_pts = pgs_mb.add_extra_points_on_river_slope(profile_pts, low_wl, high_wl)


# Add surface points of dike to geometry & connect with lines
geometry.addPoints(profile_pts,["left boundary", "bottom of river slope", "Low wl", "Mid point", "ground lvl", "high wl", "Top of river slope",
                                "Top of landside slope", "Bottom of landside slope", "right boundary"])
surface_lns = [[i, i+1] for i in range(1, len(geometry.points))]
geometry.addLines(surface_lns)


# Create cover layer
cover_inside_pts = pgs_mb.calc_cover_layer_points(profile_pts, 0.5, low_wl)
geometry.addPoints(cover_inside_pts)

# Create slurry layer
slurry_outside_pts = pgs_mb.calc_slurry_layer_points(profile_pts, 0.5, low_wl)
geometry.addPoints(slurry_outside_pts)
"""

# Create bottom border
bottom_border_pts = pgs_mb.calc_bottom_border_points(profile_pts, b3)


# Create Sub ground layers
"""
sub_layers_pts = pgs_mb.calc_subground_layers_points(surface_pts, t_top=2, t_mid=7, cover_line_pts=cover_inside_pts)
"""
sub_layers_pts = pgs_mb.calc_subground_layers_points(profile_pts, y_top_level=-2, y_mid_level=-4)

# Create cover layer (including the subground layer intersection with cover)

cover_inside_pts, cover_C_pts, cover_C_names = pgs_mb.calc_cover_layer_points(
    profile_pts,            # profile_points
    cover_t,        # thickness
    low_wl,                 # low water level
    sub_levels = [b1, b2, b3]      # required: the Y-levels to intersect)
)
# Create regions


# Check geometry
print(geometry.point_table)
fig, ax = geometry.draw()
plt.show()

# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/test-Model-Builder50.gsz"
geofile.saveAs(main_path+"/"+out_file)

