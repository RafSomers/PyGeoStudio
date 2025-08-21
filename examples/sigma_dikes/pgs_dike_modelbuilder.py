"""
Set of functions to build (dike) models in GeoStudio with (local forked) PyGeoStudio
====================================================================================
Use with 'import pgs_modelbuilder as pgs_mb'
USes:
    - Quantile Excel: cross_sections_schelde_quantiles.xlsx


"""

import pandas as pd
import numpy as np
from shapely.geometry import LineString, MultiPoint
from shapely.ops import substring


def get_surface_points_from_quantile_excel(excel_filepath, q_value, notes=None):
    """
    Extracts a list of [x, y] points for a given quantile value from the Excel data.
    :param q_value: The quantile value to filter the data.
    :param notes: List of point notes with descriptions of points
    :return: List of [x, y] coordinate pairs.
    """
    if notes == None:
        notes = [
            "Left model boundary",  # point-1
            "Bottom river slope",  # point-2
            "Midpoint river slope",  # point-3
            "Top (crest) river slope",  # point-4
            "Top (crest) land slope",  # point-5
            "Bottom land slope",  # point-6
            "Rigjt model boundary"  # point-7
        ]
    df = pd.read_excel(excel_filepath, engine="openpyxl")
    row = df[df['fid'] == q_value]
    if row.empty:
        raise ValueError(f"No data found for fid {q_value}")
    row = row.iloc[0]
    point_data = [[i, f"Point-{i + 1}", row[f'x{i+1}'], row[f'y{i+1}'], notes[i]]for i in range(0, 7)]
    point_table = pd.DataFrame(point_data, columns=["Index", "ID label", "X-co", "Y-co", "Note"])
    points = point_table[["X-co", "Y-co"]].to_numpy()
    return point_table, points, notes


def make_landside_horizontal(points):
    """
    Makes landside horizontal by setting level of two last points equal
    :param points: List of [x, y] coordinate pairs.
    :return: New list of points with y-level of last points = y-level second to last point
    """
    pmin2 = points[-2]
    pmin1 = points[-1]
    ymin2 = pmin2[1]
    xmin1 = pmin1[0]
    ymin1 = ymin2
    return np.vstack((points[:-1], [[xmin1, ymin1]]))


def add_extra_points_on_river_slope(points, low_wl, high_wl):
    """
    Adds new points on the river slope at low water level, high water level and ground level.
    :param points:  List of [x, y] coordinate pairs.
    :param low_wl: low water level
    :param high_wl: high water level
    :return: New list of points with the interpolated points inserted
    """
    # Helper function for linear interpolation
    def interpolate_x(y_target):
        print("new y (target):", y_target)
        if y2 < y_target <= y3:
            new_x = x2 + (y_target - y2) * (x3 - x2) / (y3 - y2)
        elif y3 < y_target <= y4:
            new_x = x3 + (y_target - y3) * (x4 - x3) / (y4 - y3)
        else:
            raise ValueError("Cannot interpolate! Point not on slope!")
        print("new  x : ", new_x)
        return new_x
    p2 = points[1]  # bottom of river slope
    p3 = points[2]  # midpoint of river slope
    p4 = points[3]  # top of river slope
    ground_lvl = points[5][1]  # bottom of land slope = ground level
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    y_targets = sorted([low_wl, high_wl, y3, ground_lvl])  # Add y3 to place at correct position, when sorted
    interpolated_points = np.array([[interpolate_x(y), y] for y in y_targets])
    new_points = np.vstack((points[:2], interpolated_points, points[3:]))   # Insert between p2 en p4
    return new_points


def calc_cover_layer_points(points, start_id=4, end_id=7, thickness=0.25):
    """
    Generate a offset cover layer line between start_id and end_id, trimmed to line between the start and end points.
    :param points: List of [x, y] coordinate pairs.
    :param start_id: 1-based ID of the first point of the top section.
    :param end_id: 1-based ID of the last point of the top section.
    :param thickness: Offset thickness (positive inward).
    :return: List of [x, y] p²oints of the trimmed offset line.
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