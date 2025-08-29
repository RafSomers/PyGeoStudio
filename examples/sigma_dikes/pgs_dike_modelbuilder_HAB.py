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


def get_profile_points_from_quantile_excel(excel_filepath, q_value, notes=None):
    """
    Extracts a list of [x, y] points for a given quantile value from the Excel data.
    :param q_value: The quantile value to filter the data.
    :param notes: List of point notes with descriptions of points
    :return: List of [x, y] coordinate pairs.
    """
    if notes == None:
        notes = [
            "Left model boundary",  # point-0
            "Bottom river slope",  # point-1
            "Midpoint river slope",  # point-2
            "Top (crest) river slope",  # point-3
            "Top (crest) land slope",  # point-4
            "Bottom land slope",  # point-5
            "Rigjt model boundary"  # point-6
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


def calc_soillayers_bottom_levels(profile_points, scenario, low_wl, clay_layer_t):
    """
    Return soil subground layer bottom levels (Y-values) per scenario; clay thickness is always 0.5m
    Scenrios:
    s0: Sand dike – All sand ground layers            -> no clay levels
    s1: Sand dike – Clay layer at landside ground     -> top clay at GL-0.5
    s2: Sand dike – Clay layer 1 m below low water    -> top clay at (LWL-1.0), next at -0.5 below
    s3: Sand dike – All clay layers                   -> two 0.5 m clay bands from GL downward
     Returns (y_top_level, y_mid_level) where any missing level is None.
    """
    def clamp(y):
        return max(min(y, gl_y), bottom_layer3)

    # variables

    toe_y = profile_points[1][1]
    crest_y = profile_points[3][1]
    gl_y = profile_points[6][1]
    bottom_layer3 = toe_y - 3.0 * (crest_y - toe_y)
    h_subground = gl_y - bottom_layer3

    #  defining the levels based on scenarios
    key = str(scenario).strip().lower()
    if key.startswith("s"):
        key = key[1:]
    if key == '0':          # Equally divide all 3 subground layers
        bottom_layer1 = clamp(gl_y-h_subground/3.0)
        bottom_layer2 = clamp(bottom_layer1 - h_subground/3)
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '1':  # first set clay layer, then Equally divide the remaining 2 subground layers
        bottom_layer1 = clamp(gl_y - clay_layer_t)
        rem = bottom_layer1 - bottom_layer3
        bottom_layer2 = clamp(bottom_layer1 - rem / 2.0)
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '2':
        bottom_layer1 = clamp(float(low_wl)-1.0)
        bottom_layer2 = clamp(bottom_layer1-0.5)
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '3':
        bottom_layer1 = clamp(gl_y - h_subground / 3.0)
        bottom_layer2 = clamp(bottom_layer1 - h_subground / 3)
        return bottom_layer1, bottom_layer2, bottom_layer3


def calc_cover_layer_points(profile_points, inward_thickness, low_wl, high_wl, bot_l1, bot_l2):
    """
    Generate an offset cover layer line between start_id and end_id, trimmed to line between the start and end points.
    :param profile_points: List of [x, y] coordinate pairs.
    :param inward_thickness: Offset thickness (positive inward).
    :param low_wl
    :param high_wl
    :param bot_l1
    :param bot_l2
    :return: List of [x, y] points of the trimmed offset line.
    """
    # Variables
    lw_left, lw_right = [profile_points[0][0], low_wl], [profile_points[-1][0], low_wl]
    hw_left, hw_right = [profile_points[0][0], high_wl], [profile_points[-1][0], high_wl]
    gl_left, gl_right = [profile_points[0][0], profile_points[-1][1]], profile_points[-1]
    l1_left, l1_right = [profile_points[0][0], bot_l1], [profile_points[-1][0], bot_l1]
    l2_left, l2_right = [profile_points[0][0], bot_l2], [profile_points[-1][0], bot_l2]

    # Construct shapely.geometry.LineString objects
    profile_ls = LineString(profile_points)
    trim_lowwl_ls = LineString([lw_left, lw_right])
    trim_highwl_ls = LineString([hw_left, hw_right])
    trim_groundlvl_ls = LineString([gl_left, gl_right])
    trim_bot_l1_ls = LineString([l1_left, l1_right])
    trim_bot_l2_ls = LineString([l2_left, l2_right])

    # Create offset LimeString and points list
    offset_ls = profile_ls.parallel_offset(inward_thickness, side='right', join_style=2)
    offset_pts = [list(tup) for tup in list(offset_ls.coords)]

    # Get intersectiuons
    intersection_lowwl = offset_ls.intersection(trim_lowwl_ls)
    intersection_highwl = offset_ls.intersection(trim_highwl_ls)
    intersection_groundlvl = offset_ls.intersection(trim_groundlvl_ls)
    intersection_bot_l1 = offset_ls.intersection(trim_bot_l1_ls)
    intersection_bot_l2 = offset_ls.intersection(trim_bot_l2_ls)

    # Get points from intersections
    def select_point_from_intersection(list_of_intersections, list_of_locs):
        list_of_selected_points = []
        for geom, loc in zip(list_of_intersections, list_of_locs):
            if geom.is_empty:
                continue
            elif geom.geom_type == 'Point':
                list_of_selected_points.append(list(geom.coords[0]))
            elif geom.geom_type == 'MultiPoint':
                all_mpts_tuple_list = [pt_geom.coords[0] for pt_geom in geom.geoms]
                all_mpts = [list(tup) for tup in all_mpts_tuple_list]
                sorted_mpts = sorted(all_mpts, key=lambda x: x[0])
                if loc == 'left':
                    list_of_selected_points.append(sorted_mpts[0])
                elif loc == 'right':
                    list_of_selected_points.append(sorted_mpts[1])
                else:
                    raise ValueError(f"location should be left or right")
            else:
                raise ValueError(f"Unsupported geometry type: {geom.geom_type}")

        return np.array(list_of_selected_points)

    # Apply to your geometries
    geoms = [intersection_lowwl, intersection_highwl, intersection_groundlvl, intersection_groundlvl,
             intersection_bot_l1, intersection_bot_l2]
    locs = ['left', 'left', 'left', 'right', 'left', 'left']
    extra_points_on_slope = select_point_from_intersection(geoms, locs)

    # Construct cover_inside_points output
    offset_pts_low2crest = [p for p in offset_pts if p[1] > low_wl][:-2]  # above low_wl &  including crest
    unsorted_pts = np.vstack((offset_pts_low2crest, extra_points_on_slope))
    sorted_pts = np.vstack(sorted(unsorted_pts, key=lambda x: x[0]))  # Sort by x-coordinate
    cover_inside_pts = [p for p in sorted_pts if p[1] >= low_wl]
    return cover_inside_pts


def calc_slurry_layer_points(profile_points, outward_thickness, low_wl):
    """
    Generate an offset slurry layer line between start_id and end_id, trimmed to line between the start and end points.
    :param profile_points: List of [x, y] coordinate pairs.
    :param outward_thickness: Offset thickness (positive inward).
    :param low_wl
    :param high_wl
    :param bot_l1
    :param bot_l2
    :return: List of [x, y] points of the trimmed offset line.
    """
    # Variables
    lw_left, lw_right = [profile_points[0][0], low_wl], [profile_points[-1][0], low_wl]

    # Construct shapely.geometry.LineString objects
    profile_ls_full = LineString(profile_points)
    trim_lowwl_ls = LineString([lw_left, lw_right])

    # find the low-water point on the original profile (leftmost intersection)
    _lw_inter = profile_ls_full.intersection(trim_lowwl_ls)
    if _lw_inter.is_empty:
        raise ValueError("Cannot locate low water on profile.")
    if _lw_inter.geom_type == 'Point':
        lw_pt = list(_lw_inter.coords[0])
    elif _lw_inter.geom_type == 'MultiPoint':
        pts = [list(g.coords[0]) for g in _lw_inter.geoms]
        lw_pt = sorted(pts, key=lambda x: x[0])[0]
    elif _lw_inter.geom_type == 'LineString':
        lw_pt = list(_lw_inter.coords[0])
    else:
        # fall back to first available coordinate
        lw_pt = list(list(_lw_inter.geoms)[0].coords[0])

    # source polyline for slurry: left border → river toe → low-water on slope
    profile_ls = LineString([profile_points[0], profile_points[1], lw_pt])

    # Create offset LineString and points list (to the LEFT so riverbed part is above)
    offset_ls = profile_ls.parallel_offset(outward_thickness, side='left', join_style=2)
    offset_pts = [list(tup) for tup in list(offset_ls.coords)]

    # Get intersections
    intersection_lowwl = offset_ls.intersection(trim_lowwl_ls)

    # Get points from intersections
    def get_extra_points(list_of_geoms, list_of_locs):
        list_of_extra_points = []
        for geom, loc in zip(list_of_geoms, list_of_locs):
            if geom.is_empty:
                continue
            elif geom.geom_type == 'Point':
                list_of_extra_points.append(list(geom.coords[0]))
            elif geom.geom_type == 'MultiPoint':
                all_mpts_tuple_list = [pt_geom.coords[0] for pt_geom in geom.geoms]
                all_mpts = [list(tup) for tup in all_mpts_tuple_list]
                sorted_mpts = sorted(all_mpts, key=lambda x: x[0])
                if loc in ['low', 'high']:
                    list_of_extra_points.append(sorted_mpts[0])  # river-side = leftmost
            else:
                raise ValueError(f"Unsupported geometry type: {geom.geom_type}")
        # keep shape 2D so vstack never fails
        return np.array(list_of_extra_points, dtype=float).reshape(-1, 2)

    geoms = [intersection_lowwl]
    locs  = ['low', 'low', 'low']
    extra_points_on_slope = get_extra_points(geoms, locs)

    # Construct slurry_outside_points output
    # keep only points BELOW low water (slurry sits below LWL); no crest part here
    offset_pts_left2low = np.array([p for p in offset_pts if p[1] <= low_wl], dtype=float).reshape(-1, 2)
    unsorted_pts = np.vstack((offset_pts_left2low, extra_points_on_slope))
    sorted_pts = np.vstack(sorted(unsorted_pts, key=lambda x: x[1]))  # sort by y
    slurry_outside_pts = np.vstack((sorted_pts,))
    slurry_outside_pts = slurry_outside_pts[slurry_outside_pts[:, 1] <= low_wl]
    return slurry_outside_pts


"""
# todo: test and update functions below

def calc_slurry_layer_points(points, outward_thickness, low_wl):
    
    Get points on outside of slurry layer.
    Slurry layer is on outside of dike between left border of model & low water level.
    :param points: List of [x, y] coordinate pairs of surface line.
    :param outward_thickness: Offset thickness (positive inward).
    :param low_wl: Low water level.
    :return: List of [x, y] points of inside of cover layer.
    
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
"""


def calc_bottom_border_points(profile_points, bot_l3):
    """
    Create a bottom border line 3x the slope height below the slope toe.
    Slope height is measured between point 1 (toe) and point 8 (ground level).
    :param profile_points: List of [x, y] coordinate pairs.
    :param bot_l3: bottom level of layer 3 (lowest layer)
    :return: List of [x, y] points for the bottom border (left → right).
    """
    # Build bottom border between left boundary (point 0) and right boundary (last point)
    left_x = profile_points[0][0]
    right_x = profile_points[-1][0]
    bottom_border_pts = np.vstack(([left_x, bot_l3], [right_x, bot_l3]))
    return bottom_border_pts


def calc_subground_layers_points(points, y_top_level, y_mid_level, cover_line_pts=None):
    """
    Make three subground layer lines (levels only).
    Top & middle: left point is on COVER at that Y if available; else on SLOPE.
    For any level below the slope toe, the left point is on the LEFT BORDER at that Y.
    Bottom runs from right boundary to LEFT border at the bottom border elevation.
    :param points: List of [x, y] surface points.
    :param y_top_level: Absolute Y for the top layer line.
    :param y_mid_level: Absolute Y for the middle layer line.
    :param cover_line_pts: Nx2 cover polyline points (from calc_cover_layer_points). Optional.
    :return: Nx2 array of [x, y] points for all three layer lines (top, middle, bottom).
    """
    # Geometry references
    toe_x, toe_y = points[1][0], points[1][1]
    grd_x, grd_y = points[6][0], points[6][1]
    left_x = points[0][0]
    right_x = points[-1][0]

    # Bottom border (3x slope height below toe)
    slope_h = grd_y - toe_y
    bottom_y = toe_y - 3 * slope_h

    # Clamp levels to [bottom_y, grd_y]
    def _clamp(y): return max(min(y, grd_y), bottom_y)
    y_top = _clamp(y_top_level)
    y_mid = _clamp(y_mid_level)
    y_bot = bottom_y

    # x on SLOPE (points 1..8) at a given y (with clamping)
    def _x_on_slope(y):
        if y <= toe_y: return toe_x
        if y >= grd_y: return grd_x
        for i in range(1, 8):
            x0, y0 = points[i]
            x1, y1 = points[i + 1]
            if np.isclose(y, y0): return x0
            if np.isclose(y, y1): return x1
            if (y0 - y) * (y1 - y) < 0:
                t = (y - y0) / (y1 - y0)
                return x0 + t * (x1 - x0)
        return grd_x

    # x on a polyline at Y by segment interpolation (returns None if Y not covered)
    def _x_on_polyline_at_y(poly_pts, y):
        for i in range(len(poly_pts) - 1):
            x0, y0 = poly_pts[i]
            x1, y1 = poly_pts[i + 1]
            if np.isclose(y, y0): return x0
            if np.isclose(y, y1): return x1
            if np.isclose(y0, y1) and np.isclose(y, y0):
                return min(x0, x1)
            if (y0 - y) * (y1 - y) < 0:
                t = (y - y0) / (y1 - y0)
                return x0 + t * (x1 - x0)
        return None

    # Left-side X at Y: if below toe -> LEFT BORDER; else COVER if hits, else SLOPE
    def _x_left_at_y(y):
        if y <= toe_y:
            return left_x
        if cover_line_pts is not None and len(cover_line_pts) >= 2:
            xi = _x_on_polyline_at_y(cover_line_pts, y)
            if xi is not None:
                return xi
        return _x_on_slope(y)

    # Build 2-point lines for each layer
    top_pts = np.vstack(([right_x, y_top], [_x_left_at_y(y_top), y_top]))
    mid_pts = np.vstack(([right_x, y_mid], [_x_left_at_y(y_mid), y_mid]))
    bot_pts = np.vstack(([right_x, y_bot], [left_x, y_bot]))

    # Return all in one array (top, middle, bottom)
    return np.vstack((top_pts, mid_pts, bot_pts))


def update_profile_points(profile_pts, low_wl, high_wl, g_lvl, bot_l1, bot_l2):
    """
    Adds new points on the river slope at low water level, high water level and ground level.
    :param profile_pts:  List of [x, y] coordinate pairs.
    :param low_wl: low water level
    :param high_wl: high water level
    :param g_lvl: ground level
    :param bot_l1: bottom of layer 1
    :param bot_l2: bottom of layer 2
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
    p2 = profile_pts[1]  # bottom of river slope
    p3 = profile_pts[2]  # midpoint of river slope
    p4 = profile_pts[3]  # top of river slope
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    y_targets = sorted([low_wl, high_wl, y3, g_lvl])  # Add y3 to place at correct position, when sorted
    if min(y2, y4) < bot_l1 <= max(y2, y4):
        y_targets.append(bot_l1)
    if min(y2, y4) < bot_l2 <= max(y2, y4):
        y_targets.append(bot_l2)
    y_targets = sorted(y_targets)
    interpolated_points = np.array([[interpolate_x(y), y] for y in y_targets])
    new_points = np.vstack((profile_pts[:2], interpolated_points, profile_pts[3:]))   # Insert between p2 en p4
    return new_points


def add_right_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3):
    """
    Add points on the right border at the bottoms of layers 1, 2, and 3.
    :param profile_pts: List of [x, y] coordinate pairs (full profile).
    :param bot_l1: Bottom elevation of layer 1.
    :param bot_l2: Bottom elevation of layer 2.
    :param bot_l3: Bottom elevation of layer 3.
    :return: 3x2 array of [x, y] points on the right border.
    """
    # Right border x
    right_x = profile_pts[-1][0]
    # Points on right side for each layer bottom
    layer_right_pts = np.array([[right_x, bot_l1], [right_x, bot_l2], [right_x, bot_l3]])
    return layer_right_pts


def add_left_side_layer_points(profile_pts, bot_l1, bot_l2, bot_l3):
    """
    Add points on the right border at the bottoms of layers 1, 2, and 3.
    :param profile_pts: List of [x, y] coordinate pairs (full profile).
    :param bot_l1: Bottom elevation of layer 1.
    :param bot_l2: Bottom elevation of layer 2.
    :param bot_l3: Bottom elevation of layer 3.
    :return: array of [x, y] points on the right border.
    """
    left_x = profile_pts[0][0]
    toe_y = profile_pts[1][1]
    layer_left_pts = np.array([[left_x, y] for y in (bot_l1, bot_l2) if y < toe_y] + [[left_x, bot_l3]])
    return layer_left_pts
