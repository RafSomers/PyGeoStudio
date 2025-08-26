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


def calc_soillayers_bottom_levels (profile_points, scenario, low_wl):
    """
    Return soil subground layer bottom levels (Y-values) per scenario; clay thickness is always 0.5m
    Scenrios:
    s0: Sand dike – All sand ground layers            -> no clay levels
    s1: Sand dike – Clay layer at landside ground     -> top clay at GL-0.5
    s2: Sand dike – Clay layer 1 m below low water    -> top clay at (LWL-1.0), next at -0.5 below
    s3: Sand dike – All clay layers                   -> two 0.5 m clay bands from GL downward
     Returns (y_top_level, y_mid_level) where any missing level is None.
    """
    # refs
    toe_y = profile_points[1][1]
    crest_y = profile_points[3][1]
    bottom_y = toe_y - 3.0 * (crest_y - toe_y)
    def clamp(y):
        return max(min(y, crest_y), bottom_y)
    key = str(scenario).strip().lower()
    if key.startswith("s"):
        key = key[1:]
    if key == '0':
        H = crest_y - bottom_y
        bottom_layer1 = clamp((crest_y-H/3.0))
        bottom_layer2 = clamp(crest_y - 2.0*H/3)
        bottom_layer3 = bottom_y
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '1':
        bottom_layer1 = clamp(crest_y - 0.5)
        rem = bottom_layer1 - bottom_y
        bottom_layer2 = clamp(crest_y - rem / 2.0)
        bottom_layer3 = bottom_y
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '2':
        bottom_layer1 = clamp(float(low_wl)-1.0)
        bottom_layer2 = clamp(bottom_layer1-0.5)
        bottom_layer3 = bottom_y
        return bottom_layer1, bottom_layer2, bottom_layer3
    if key == '3':
        bottom_layer1 = clamp(crest_y-0.5)
        bottom_layer2 = clamp (bottom_layer1 - 0.5)
        bottom_layer3 = bottom_y
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
                    list_of_extra_points.append(sorted_mpts[0])
            else:
                raise ValueError(f"Unsupported geometry type: {geom.geom_type}")

        return np.array(list_of_extra_points)

    # Apply to your geometries
    geoms = [intersection_lowwl, intersection_highwl, intersection_groundlvl, intersection_bot_l1, intersection_bot_l2]
    locs = ['low', 'low', 'low', 'low', 'low']
    extra_points_on_slope = get_extra_points(geoms, locs)
    gl_land_pts = get_extra_points([intersection_groundlvl], ['high'])

    # Construct cover_inside_points output
    offset_pts_low2crest = [p for p in offset_pts if p[1] > low_wl][:-4]  # above low_wl & not including crest
    unsorted_pts = np.vstack((offset_pts_low2crest, extra_points_on_slope))
    sorted_pts = np.vstack(sorted(unsorted_pts, key=lambda x: x[1]))  # Sort by y-coordinate
    cover_inside_pts = np.vstack((sorted_pts, offset_pts[-3:-1], gl_land_pt))
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
    pass


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


