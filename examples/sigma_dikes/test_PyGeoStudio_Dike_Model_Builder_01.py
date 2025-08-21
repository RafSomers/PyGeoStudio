"""
Testing pgs_dike_Model_Builder
===============

"""

# %%
# Open example GeoStudio study
import importlib
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
surface_pt_table, surface_pts, surface_notes = pgs_mb.get_surface_points_from_quantile_excel(quantile_excel_filepath, 0.5)
surface_pt_table

# Make landside horizontal
surface_pts = pgs_mb.make_landside_horizontal(surface_pts)
surface_pts

# Add extra points to surface points
low_wl, high_wl = 0.23, 5.62
surface_pts = pgs_mb.add_extra_points_on_river_slope(surface_pts, low_wl, high_wl)
surface_pts

# Add surface points of dike to geometry & connect with lines
geometry.addPoints(surface_pts)
surface_lns = [[i, i+1] for i in range(1, len(geometry.points))]
geometry.addLines(surface_lns)




# --- COVER (two parts) ----------------------------------------------------
# We ask the builder to return BOTH parts (slope + top) AND also write them to the model.
cover_parts = pgs_mb.calc_cover_layer_points(
    surface_pts,
    low_wl=low_wl,
    high_wl=high_wl,
    start_id=4,          # P4..P7 is the “top” section
    end_id=7,
    thickness=0.50,      # bump to 1.0 once to confirm visibility, then set back
    geometry=geometry,   # <- this draws COVER_P1 and COVER_P2 as real lines
    return_parts=True     # <- this makes sure we get a dict with both parts back
)

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
    surface_pts, start_id=4, end_id=7, thickness=0.50
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
slurry_pts = pgs_mb.add_slurry_layer(surface_pts, thickness=1.0, start_id=1, end_id=4)
geometry.addPoints(slurry_pts)
print(f"Added slurry layer with {len(slurry_pts)} points.")

# Add subground layers and add them directly to the geometry
Subground_layers = pgs_mb.add_subground_layers(surface_pts, layer_thickness=2.0, num_layers=3)


# Add to geometry and store for region creation
for i, layer in enumerate(Subground_layers, start=1):
    geometry.addPoints(layer)
    print(f"Layer {i}: {layer}")

geometry.subground_layers = Subground_layers

# Store layer points in geometry attributes
geometry.surface_pts = surface_pts
geometry.cover_inner_pts = cover_inner_pts
geometry.slurry_layer_pts = slurry_pts
geometry.subground_layers = Subground_layers

geometry.subground_layers = Subground_layers  

# --- Create regions 
# Expose the surface points so the auto-detector can use them too
geometry.surface_pts = surface_pts

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
out_file = "examples/GeoStudio_files/test-Model-Builder.gsz"
geofile.saveAs(main_path+"/"+out_file)

