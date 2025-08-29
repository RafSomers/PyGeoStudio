"""
Testing pgs_dike_Model_Builder
===============

"""
import matplotlib.pyplot as plt
import PyGeoStudio as pgs
import pgs_dike_modelbuilder as pgs_mb

# Inputs
#########
# Work folder main path
main_path = r"C:\Users\XZ6583\Desktop\Work Docs\Sigma 3.0\pythonProject\PyGeoStudio-main"

# Scenario ID selection
analysis_type = 'A0'
river_id = 'R0'
quantile_id = 'Q0'
soil_id = 'S2'
xtra_id = 'X1'
# todo: variables to be set automatically based unique scenario_id)
quantile = 0.5
quantile_excel_filepath = main_path + "/" + r"examples\sigma_dikes" + "/" + "cross_sections_schelde_quantiles.xlsx"
low_wl, high_wl = 0.23, 5.65
cover_present = True
cover_thickness = 0.5
clay_layer_thickness = 0.5


# Create empty GSZ file
#######################
src_file = "examples/GeoStudio_files/test.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)
geometry = geofile.getGeometryByID(1)
geometry.delete()


# Generate geometry
####################
# Get dike basic points
_, profile_pts, _ = pgs_mb.get_profile_points_from_quantile_excel(quantile_excel_filepath, quantile)

# Make landside horizontal
profile_pts = pgs_mb.make_landside_horizontal(profile_pts)

# Get soil levels
# todo: fix the rest of bottom layers (done)
bot_l1, bot_l2, bot_l3 = pgs_mb.calc_soillayers_bottom_levels(profile_pts, soil_id, low_wl, clay_layer_thickness)
print("soil levels:", bot_l1, bot_l2, bot_l3)

# Create cover layer
cover_inside_pts = pgs_mb.calc_cover_layer_points(profile_pts, cover_thickness, low_wl, high_wl, bot_l1, bot_l2)

# Create slurry layer
# todo: remove layer1,2 intersections (done)
slurry_outside_pts = pgs_mb.calc_slurry_layer_points(profile_pts, cover_thickness, low_wl)
# geometry.addPoints(slurry_outside_pts)

# Add extra points to surface points
# todo: update function to create additional points(lowwl, highwl, gl, layer1, layer2) (done)
updated_profile_pts = pgs_mb.update_profile_points(profile_pts, low_wl, high_wl, bot_l1, bot_l2)

# todo: add points that correspond to the right side of the model to layer 1, 2, 3 (done)
# add right side boundary points
right_boundary_pts = pgs_mb.add_right_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3)

# add right side boundary points
left_boundary_pts = pgs_mb.add_left_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3)

# Check geometry
geometry.addPoints(updated_profile_pts)  # includes profile_points
geometry.addPoints(cover_inside_pts)    # cover layer
geometry.addPoints(slurry_outside_pts)  # slurry layer
geometry.addPoints(right_boundary_pts)  # right boundary points
geometry.addPoints(left_boundary_pts)   # left boundary points
hyd_boundary_lns = [[i, i+1] for i in range(1, len(updated_profile_pts))]  # always last in updated_profile_pts
geometry.addLines(hyd_boundary_lns)
print(geometry.point_table)
fig, ax = geometry.draw()   # todo: do we still need the plot?
plt.show()



"""
# Normalize into cover_p1 / cover_p2 attributes
if isinstance(cover_parts, dict):
    geometry.cover_p1 = cover_parts.get('part1', [])   # slope part (low→high)
    geometry.cover_p2 = cover_parts.get('part2', [])   # top part (from high WL over top)
else:
    geometry.cover_p1 = []
    geometry.cover_p2 = cover_parts

# --- COVER INNER POINTS (top section offset as points) --------------------
# Compute ONCE (no de-dupe)
cover_inner_pts = pgs_mb.calc_cover_layer_points(
    profile_pts, start_id=4, end_id=7, thickness=0.50
)

# Add ONCE
geometry.addPoints(cover_inner_pts)
print(f"Generated {len(cover_inner_pts)} cover layer points.")

# Optional: quick introspection
print(dir(geometry))
print(vars(geometry))
geometry.listProperties()

# The cover function returns two pieces; save both on geometry so region maker can find them.
geometry.cover_p1 = cover_parts['part1']   # low→high on the river slope
geometry.cover_p2 = cover_parts['part2']   # above high WL across the top
geometry.cover_inner_pts = cover_parts['part1'] + cover_parts['part2']  # if other code expects this


# make a thin cover polygon by mirroring a bottom edge thickness below part1+part2
cover_top = cover_parts['part1'] + cover_parts['part2']
if cover_top:
    # simple bottom edge: reuse same x’s, drop by thickness
    t = 0.50  # your cover thickness
    cover_bottom = [[x, y - t] for (x, y) in reversed(cover_top)]
    geometry.cover_inner_pts = cover_top + cover_bottom  # now a closed loop when mapped to IDs

# Add slurry layer (points from start_id to end_id)
slurry_pts = pgs_mb.add_slurry_layer(profile_pts, thickness=1.0, start_id=1, end_id=4)
geometry.addPoints(slurry_pts)
print(f"Added slurry layer with {len(slurry_pts)} points.")

# Add subground layers and add them directly to the geometry
Subground_layers = pgs_mb.add_subground_layers(profile_pts, layer_thickness=2.0, num_layers=3)


# Add to geometry and store for region creation
for i, layer in enumerate(Subground_layers, start=1):
    geometry.addPoints(layer)
    print(f"Layer {i}: {layer}")

geometry.subground_layers = Subground_layers

# Store layer points in geometry attributes
geometry.profile_pts = profile_pts
geometry.cover_inner_pts = cover_inner_pts
geometry.slurry_layer_pts = slurry_pts
geometry.subground_layers = Subground_layers

geometry.subground_layers = Subground_layers  

# --- Create regions 
# Expose the surface points so the auto-detector can use them too
geometry.profile_pts = profile_pts

regions_df = pgs_mb.create_all_regions(geometry)
print("✅ Regions created.")
if regions_df is not None:
    try:
        print(regions_df.to_string(index=False))
    except Exception:
        print(regions_df)
"""

# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/test-Model-Builder-New.gsz"
geofile.saveAs(main_path+"/"+out_file)

print('end')