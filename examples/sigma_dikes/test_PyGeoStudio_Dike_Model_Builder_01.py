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
main_path = r"C:\Users\WQ5783\OneDrive - ENGIE\5_PyProjects\PyGeoStudio"

# Scenario ID selection
Full_code = 'A0-R0-C0-S3-X1-Y0'
analysis_type = 'A0'
river_id = 'R0'
quantile_id = 'C0'
soil_id = 'S0'
xtra_id = 'X1'
cover_variation_id = 'Y0'
# todo: variables to be set automatically based unique scenario_id)
quantile = 0.5
quantile_excel_filepath = main_path + "/" + r"examples\sigma_dikes" + "/" + "cross_sections_schelde_quantiles.xlsx"
low_wl, high_wl = 1.643332, 5.65
cover_present = True
slurry_present = True
cover_thickness, slurry_thickness = 0.5, 0.5
clay_layer_thickness = 0.5


# Create empty GSZ file
#######################
src_file = "examples/GeoStudio_files/test.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)
analysis = geofile.getAnalysisByID(1)
context = analysis.data["Context"]
geometry = geofile.getGeometryByID(1)
print(geometry.point_table)
geometry.delete()


# Generate geometry
####################
# Get dike basic points
_, profile_pts, _ = pgs_mb.get_profile_points_from_quantile_excel(quantile_excel_filepath, quantile)

# Make landside horizontal
profile_pts = pgs_mb.make_landside_horizontal(profile_pts)

# Get soil levels
bot_l1, bot_l2, bot_l3 = pgs_mb.calc_soillayers_bottom_levels(profile_pts, soil_id, low_wl, clay_layer_thickness)
print("soil levels:", bot_l1, bot_l2, bot_l3)

# Create cover layer
cover_inside_pts = pgs_mb.calc_cover_layer_points(profile_pts, cover_thickness, low_wl, high_wl, bot_l1, bot_l2)

# Create slurry layer
slurry_outside_pts = pgs_mb.calc_slurry_layer_points(profile_pts, cover_thickness, low_wl)

# Update profile points (add extra ones)
updated_profile_pts = pgs_mb.update_profile_points(profile_pts, low_wl, high_wl, bot_l1, bot_l2)

# add bottom of layer points if on model boundary (left or right)
# todo: Raf check code in pgs_mb for points that correspond to the bottom of layer 1, 2, 3
right_boundary_pts = pgs_mb.add_right_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3)
left_boundary_pts = pgs_mb.add_left_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3)

# Add hydraulic bpoundary lines
# todo: river hyd bc up to crest (not high wl)
river_hydb_ln = pgs_mb.get_river_boundary_lines(updated_profile_pts, high_wl)
# hyd boundary 2
ground_w_hydb_ln = pgs_mb.get_ground_water_boundary_lines(updated_profile_pts)

# todo: Prepare list that contain the points for specific regions

# Check geometry
geometry.addPoints(updated_profile_pts, "UPP")  # includes profile_points
if cover_present:
    geometry.addPoints(cover_inside_pts, "c_in")    # cover layer
if slurry_present:
    geometry.addPoints(slurry_outside_pts, "s_out")  # slurry layer
geometry.addPoints(right_boundary_pts, "r_bnd")  # right boundary points
geometry.addPoints(left_boundary_pts, "l_bnd")   # left boundary points
geometry.addLines(river_hydb_ln)  # River bed to high water level
geometry.addLines(ground_w_hydb_ln)  # Ground level (right side) boundary line
print(geometry.point_table)

# define points of layers
df = geometry.point_table   # Data frame of point table
landside_x = profile_pts[5][0]
landside_y = profile_pts[5][1]

# region inner dike
if cover_present:
    source_text = "c_in"
else:
    source_text = "UPP"
in_dike_reg_pts = df.loc[(df['Source'] == source_text) & (df['X'] <= landside_x) & (df['Y'] >= landside_y),
                         'Point_num'].to_list()
# region slurry layer
if slurry_present:
    # for the slurry layer
    s_out_pts = df.loc[(df['Source'] == 's_out') & (df['Y'] <= low_wl), 'Point_num'].tolist()
    # Get 'UPP' points in inverse order
    s_in_pts = df.loc[(df['Source'] == 'UPP') & (df['Y'] <= low_wl), 'Point_num'].tolist()[::-1]
    slurry_reg_pts = s_out_pts + s_in_pts      # slurry layer points
else:
    slurry_reg_pts = []

# region cover layer wet (part below high_wl and above low_wl)
if cover_present:
    # for the cover layer (inverse of cover pts to create region)
    c_in_pts_w = df.loc[(df['Source'] == 'c_in') & (df['Y'] <= high_wl), 'Point_num'].tolist()[::-1]
    # Get 'UPP' points in original order
    c_out_pts_w = df.loc[(df['Source'] == 'UPP') & (df['Y'] >= low_wl) & (df['Y'] <= high_wl), 'Point_num'].tolist()
    cover_w_reg_pts = c_out_pts_w + c_in_pts_w
else:
    # cover layer wet empty
    cover_w_reg_pts = []

# region cover layer dry (part above high_wl)
if cover_present:
    # for the cover layer (inverse of cover pts to create region)
    c_in_pts_d = df.loc[(df['Source'] == 'c_in') & (df['Y'] >= high_wl), 'Point_num'].tolist()[::-1]
    # Get 'UPP' points in original order
    c_out_pts_d = df.loc[(df['Source'] == 'UPP') & (df['X'] <= landside_x) & (df['Y'] >= high_wl), 'Point_num'].tolist()
    cover_d_reg_pts = c_out_pts_d + c_in_pts_d
else:
    cover_d_reg_pts = []

# upper subground region layer
# c_in_pts = df.loc[(df['Source'] == 'c_in') & (df['Y'] >= low_wl), 'Point_num'].tolist()
if cover_present:
    sub1_l_bn_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l1), 'Point_num'].tolist()
    sub1_UPP_pts = df.loc[(df['Source'] == "UPP") & (df['Y'] >= bot_l1) & (df['Y'] <= low_wl), 'Point_num'].tolist()
    sub1_c_in_pts = df.loc[(df['Source'] == "c_in") & (df['Y'] >= bot_l1) & (df['Y'] <= landside_y),
                           'Point_num'].tolist()
    sub1_dike_pts = sub1_l_bn_pts + sub1_UPP_pts + sub1_c_in_pts
else:
    sub1_l_bn_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l1), 'Point_num'].tolist()
    sub1_UPP_pts = df.loc[(df['Source'] == 'UPP') & (df['Y'] >= bot_l1) & (df['Y'] <= landside_y) &
                           (df['X'] < landside_x), 'Point_num'].tolist()
    sub1_dike_pts =  sub1_l_bn_pts + sub1_UPP_pts
sub1_land_pts = df.loc[(df['Source'] == 'UPP') & (df['X'] >= landside_x), 'Point_num'].tolist()
sub1_r_bnd_pts = df.loc[(df['Source'] == 'r_bnd') & (df['Y'] < landside_y) & (df['Y'] >= bot_l1), 'Point_num'].tolist()
sub1_reg_pts = sub1_dike_pts + sub1_land_pts + sub1_r_bnd_pts

# region middle subground layer
if cover_present:
    sub2_l_bnd_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l2) & (df['Y'] <= bot_l1),
                            'Point_num'].tolist()[::-1]
    sub2_UPP_pts = df.loc[(df['Source'] == "UPP") & (df['Y'] <= low_wl) & (df['Y'] <= bot_l1) & (df['Y'] >= bot_l2),
                          'Point_num'].tolist()
    sub2_c_in_pts = df.loc[(df['Source'] == "c_in") & (df['Y'] <= bot_l1), 'Point_num'].tolist()
    sub2_dike_pts = sub2_l_bnd_pts + sub2_UPP_pts + sub2_c_in_pts
else:
    sub2_l_bnd_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l2) & (df['Y'] <= bot_l1),
                            'Point_num'].tolist()[::-1]
    sub2_UPP_pts = df.loc[(df['Source'] == 'UPP') & (df['Y'] >= bot_l2) & (df['Y'] <= bot_l1) &
                           (df['X'] < landside_x), 'Point_num'].tolist()
    sub2_dike_pts = sub2_l_bnd_pts + sub2_UPP_pts
sub2_r_bnd_pts = df.loc[(df['Source'] == 'r_bnd') & (df['Y'] <= bot_l1) & (df['Y'] >= bot_l2), 'Point_num'].tolist()
sub2_reg_pts = sub2_dike_pts + sub2_r_bnd_pts

# region bottom subground layer
if cover_present:
    sub3_l_bnd_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l3) & (df['Y'] <= bot_l2),
                            'Point_num'].tolist()[::-1]
    sub3_UPP_pts = df.loc[(df['Source'] == "UPP") & (df['Y'] >= bot_l3) & (df['Y'] <= bot_l2) & (df['Y'] <= low_wl),
                          'Point_num'].tolist()
    sub3_c_in_pts = df.loc[(df['Source'] == "c_in") & (df['Y'] <= bot_l2), 'Point_num'].tolist()
    sub3_dike_pts = sub3_l_bnd_pts + sub3_UPP_pts + sub3_c_in_pts
else:
    sub3_l_bnd_pts = df.loc[(df['Source'] == "l_bnd") & (df['Y'] >= bot_l3) & (df['Y'] <= bot_l2),
                            'Point_num'].tolist()[::-1]
    sub3_UPP_pts = df.loc[(df['Source'] == 'UPP') & (df['Y'] >= bot_l3) & (df['Y'] <= bot_l2) &(df['X'] < landside_x),
                          'Point_num'].tolist()
    sub3_dike_pts = sub3_l_bnd_pts + sub3_UPP_pts
sub3_r_bnd_pts = df.loc[(df['Source'] == 'r_bnd') & (df['Y'] <= bot_l2) & (df['Y'] >= bot_l3), 'Point_num'].tolist()
sub3_reg_pts = sub3_dike_pts + sub3_r_bnd_pts

print(in_dike_reg_pts)
geometry.addRegions(in_dike_reg_pts)
geometry.addRegions(slurry_reg_pts)
geometry.addRegions(cover_w_reg_pts)
geometry.addRegions(cover_d_reg_pts)
geometry.addRegions(sub1_reg_pts)
geometry.addRegions(sub2_reg_pts)
geometry.addRegions(sub3_reg_pts)
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
# out_file = "examples/GeoStudio_files/test-Model-Builder.gsz"
# geofile.saveAs(main_path+"/"+out_file)

print('end')