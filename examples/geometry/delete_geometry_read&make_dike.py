"""
Delete geometry and read excel, then make dike profile
======================================================

"""
import pandas as pd
import numpy as np
from shapely.geometry import LineString, MultiPoint
from shapely.ops import substring

# %%
# Open example GeoStudio study
import PyGeoStudio as pgs

# Check main path
main_path = "/"

# Open file
src_file = "examples/GeoStudio_files/test.gsz"
geofile = pgs.GeoStudioFile(main_path+"/"+src_file)

# Delete all
geofile.showGeometries()
geometry = geofile.getGeometryByID(1)
geometry.delete()

# Load the Excel file
df = pd.read_excel(main_path+"/"+"examples/geometry/cross_sections_schelde_quantiles.xlsx", engine="openpyxl")


def get_surface_points_from_quantile(q_value):
    """
    Extracts a list of [x, y] points for a given quantile value from the Excel data.
    :param q_value: The quantile value to filter the data.
    :return: List of [x, y] coordinate pairs.
    """
    row = df[df['fid'] == q_value]
    if row.empty:
        raise ValueError(f"No data found for fid {q_value}")
    row = row.iloc[0]
    points = [[row[f'x{i}'], row[f'y{i}']] for i in range(1, 8)]
    return points


def add_riverpoint_at_groundlevel(points):
    """
    Adds a new point on the river slope on groundlevel of landside.
    :param points: List of [x, y] coordinate pairs.
    :return: New list of points with the interpolated point inserted between points 3 and 4.
    """
    p3 = points[2]
    p4 = points[3]
    y_target = points[5][1]
    x3, y3 = p3
    x4, y4 = p4
    if y4 == y3:
        raise ValueError("Cannot interpolate with horizontal line segment between points 3 and 4.")
    # Linear interpolation to find x at y = y_target
    x_interp = x3 + (y_target - y3) * (x4 - x3) / (y4 - y3)
    interpolated_point = [x_interp, y_target]
    # Insert the new point between points 3 and 4
    return points[:3] + [interpolated_point] + points[3:]


def make_landside_horizontal(points):
    """
    Makes landside horizontal by setting level of two last points equal
    :param points: List of [x, y] coordinate pairs.
    :return: New list of points with y-level points 8 = y-level points 7
    """
    p7 = points[6]
    p8 = points[7]
    y7 = p7[1]
    x8 = p8[0]
    y8 = y7
    return points[:7] + [[x8, y8]]


# Get & modify points
surface_pts = get_surface_points_from_quantile(0.5)
print(surface_pts)
surface_pts = add_riverpoint_at_groundlevel(surface_pts)
surface_pts = make_landside_horizontal(surface_pts)
print(surface_pts)

# Add surface points of dike to geometry & connect with lines
geometry.addPoints(surface_pts)
surface_lns = [[i, i+1] for i in range(1, len(geometry.points))]
geometry.addLines(surface_lns)


def calc_cover_layer_points(points, start_id=4, end_id=7, thickness=0.25):
    """
    Generate a offset cover layer line between start_id and end_id, trimmed to line between the start and end points.
    :param points: List of [x, y] coordinate pairs.
    :param start_id: 1-based ID of the first point of the top section.
    :param end_id: 1-based ID of the last point of the top section.
    :param thickness: Offset thickness (positive inward).
    :return: List of [x, y] points of the trimmed offset line.
    """
    # Extract top section
    top_section = points[start_id - 1:end_id]
    line = LineString(top_section)
    # Offset inward (left of direction)
    offset_line = line.parallel_offset(-thickness, side='left', join_style=2)
    # Create trim line between start and end of original top section
    p_start = top_section[0]
    p_end = top_section[-1]
    trim_line = LineString([p_start, p_end])
    # Find intersection points of offset & trim line
    intersection = offset_line.intersection(trim_line)
    if intersection.is_empty:
        raise ValueError("No intersection found between offset and trim line.")
    if isinstance(intersection, MultiPoint):
        inter_pts = sorted(intersection.geoms, key=lambda p: p.x)
    elif intersection.geom_type == 'Point':
        inter_pts = [intersection]
    else:
        raise ValueError("Unexpected intersection geometry.")
    # Get intersection points
    intersec_line = LineString([pt.coords[0] for pt in inter_pts])
    # Construct list of points of cover layer from offset line & intersection points
    offset_pts = [list(tup) for tup in list(offset_line.coords)]
    intersec_pts = [list(tup) for tup in list(intersec_line.coords)]
    cover_pts = [intersec_pts[0]] + offset_pts[1:-1] + [intersec_pts[-1]]
    return cover_pts

# Add cover layer (inner points) using 1-based point IDs (4 to 7)
cover_inner_pts = calc_cover_layer_points(surface_pts, start_id=4, end_id=7, thickness=0.25)
geometry.addPoints(cover_inner_pts)
geometry.addLinesUI()

geometry.draw(listProperties=True)


# %%
# Write modified study under new file:
out_file = "examples/GeoStudio_files/test-dike-geom.gsz"
geofile.saveAs(main_path+"/"+out_file)
