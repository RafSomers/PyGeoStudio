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
from shapely.geometry import LineString, Polygon

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


def calc_cover_layer_points(points, thickness, low_wl):
    """
    Generate an offset cover layer line between start_id and end_id, trimmed to line between the start and end points.
    :param points: List of [x, y] coordinate pairs.
    :param thickness: Offset thickness (positive inward).
    :return: List of [x, y] points of the trimmed offset line.
    """
    # Check points[2] to points[5] for low_wl and groundlevel match
    start_index_cover = None
    for i in range(2, 6):
        if np.isclose(points[i][1], low_wl):
            start_index_cover = i
            break
    # Construct shapely.geometry.LineString object to do offset on outside of cover layer and trim on low water lvl
    if start_index_cover is not None:
        cover_out_ls = LineString(points[start_index_cover:9])
        trim_lowwl_ls = LineString([points[start_index_cover], [0, low_wl]])
    else:
        raise ValueError("Cannot create offset linestring! Low water is not in points 3 to 5!")
    # Construct extra shapely.geometry.LineString objects to do trimming
    trim_groundlvl_ls = LineString([[0, points[8][1]], points[8]])
    # Create offset
    offset_ls = cover_out_ls.parallel_offset(thickness, side='right', join_style=2)
    # Trim offset on low_wl & groundlvl
    intersection_lowwl = offset_ls.intersection(trim_lowwl_ls)
    intersection_groundlvl = offset_ls.intersection(trim_groundlvl_ls)
    # Create cover inside points
    offset_new_first_pt = [list(tup) for tup in list(intersection_lowwl.coords)]
    offset_new_last_pt = [list(tup) for tup in list(intersection_groundlvl.coords)]
    offset_pts = [list(tup) for tup in list(offset_ls.coords)]
    offset_pts = [p for p in offset_pts if p[1] > low_wl]
    cover_inside_pts = np.vstack((offset_new_first_pt[0], offset_pts[1:-1], offset_new_last_pt[0]))
    return cover_inside_pts

def calc_slurry_layer_points(points, outward_thickness, low_wl):
    """
    Get points on outside of slurry layer.
    Slurry layer is on outside of dike between left border of model & low water level.
    :param points: List of [x, y] coordinate pairs of surface line.
    :param outward_thickness: Offset thickness (positive inward).
    :param low_wl: Low water level.
    :return: List of [x, y] points of inside of cover layer.
    """
    # Check points[2] to points[5] for low_wl and groundlevel match
    start_index_slurry = None
    for i in range(2, 6):
        if np.isclose(points[i][1], low_wl):
            start_index_slurry = i
            break
    # Construct shapely.geometry.LineString object to do offset on outside of slurry layer and trim on low water lvl
    if start_index_slurry is not None:
        slurry_out_ls = LineString(points[0:start_index_slurry+1])
        trim_lowwl_ls = LineString([points[start_index_slurry], [points[0][0], low_wl]])
    else:
        raise ValueError("Cannot create offset linestring! Low water is not in points 3 to 5!")
    # Create offset
    offset_ls = slurry_out_ls.parallel_offset(outward_thickness, side='left', join_style=2)
    # Trim offset on low_wl
    intersection_lowwl = offset_ls.intersection(trim_lowwl_ls)
    # Create slurry outside points (start from offset's first point; no left-border trim)
    offset_pts = [list(tup) for tup in list(offset_ls.coords)]
    offset_new_last_pt = [list(tup) for tup in list(intersection_lowwl.coords)]
    offset_pts = [p for p in offset_pts if p[1] < low_wl]
    slurry_outside_pts = np.vstack((offset_pts, offset_new_last_pt[0]))
    return slurry_outside_pts

def calc_bottom_border_points(points):
    """
    Create a bottom border line 3x the slope height below the slope toe.
    Slope height is measured between point 1 (toe) and point 8 (ground level).
    :param points: List of [x, y] coordinate pairs.
    :return: List of [x, y] points for the bottom border (left → right).
    """
    # Compute slope height (toe -> ground level)
    toe_y = points[1][1]
    crest_y = points[8][1]
    slope_h = crest_y - toe_y
    # Bottom border y = toe_y - 3 * slope height
    bottom_y = toe_y - 3 * slope_h
    # Build bottom border between left boundary (point 0) and right boundary (last point)
    left_x = points[0][0]
    right_x = points[-1][0]
    bottom_border_pts = np.vstack(([left_x, bottom_y], [right_x, bottom_y]))
    return bottom_border_pts

def calc_subground_layers_points(points, t_top, t_mid, cover_line_pts=None):
    """
    Make three subground layer lines.
    Top & middle intersect the COVER line (if it intersects at that Y); otherwise they intersect the SLOPE.
    Bottom runs from right boundary to LEFT border at the bottom border elevation.
    :param points: List of [x, y] surface points.
    :param t_top: Top-layer thickness (downward from ground level).
    :param t_mid: Middle-layer thickness (downward from ground level, after top).
    :param cover_line_pts: Nx2 array of the cover-layer polyline points (from calc_cover_layer_points).
    :return: Nx2 array of [x, y] points for all three layer lines (top, middle, bottom).
    """
    # Geometry references
    toe_x, toe_y = points[1][0], points[1][1]
    grd_x, grd_y = points[8][0], points[8][1]
    left_x = points[0][0]
    right_x = points[-1][0]

    # Bottom border (3x slope height below toe)
    slope_h = grd_y - toe_y
    bottom_y = toe_y - 3 * slope_h

    # Target elevations (clamped so we never go below bottom_y)
    y_top = max(grd_y - t_top, bottom_y)
    y_mid = max(grd_y - (t_top + t_mid), bottom_y)
    y_bot = bottom_y

    # x on SLOPE (points 1 to 8) at a given y (with clamping)
    def _x_on_slope(y):
        if y <= toe_y:
            return toe_x
        if y >= grd_y:
            return grd_x
        for i in range(1, 8):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            if np.isclose(y, y0): return x0
            if np.isclose(y, y1): return x1
            if (y0 - y) * (y1 - y) < 0:
                t = (y - y0) / (y1 - y0)
                return x0 + t * (x1 - x0)
        return grd_x

    # Prepare COVER line if provided
    cover_ls = None
    cover_ymin = cover_ymax = None
    if cover_line_pts is not None and len(cover_line_pts) >= 2:
        cover_ls = LineString(cover_line_pts)
        cover_ymin = min(p[1] for p in cover_line_pts)
        cover_ymax = max(p[1] for p in cover_line_pts)

    # x on COVER at y if it intersects; otherwise fall back to SLOPE
    def _x_on_cover_or_slope(y):
        if cover_ls is not None and cover_ymin <= y <= cover_ymax:
            h = LineString([[left_x, y], [right_x, y]])
            inter = cover_ls.intersection(h)
            if not inter.is_empty:
                if hasattr(inter, "coords"):
                    return list(inter.coords)[0][0]
                else:
                    return list(inter.geoms[0].coords)[0][0]
        return _x_on_slope(y)

    # Build 2-point lines for each layer
    # Top & Middle: right boundary -> COVER (or SLOPE) intersection
    top_pts = np.vstack(([right_x, y_top], [_x_on_cover_or_slope(y_top), y_top]))
    mid_pts = np.vstack(([right_x, y_mid], [_x_on_cover_or_slope(y_mid), y_mid]))
    # Bottom: right boundary -> LEFT border at bottom_y
    bot_pts = np.vstack(([right_x, y_bot], [left_x, y_bot]))

    # Return all in one array (top, middle, bottom)
    return np.vstack((top_pts, mid_pts, bot_pts))

