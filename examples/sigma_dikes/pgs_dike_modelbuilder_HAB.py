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
    p2 = points[1]  # bottom of river slope
    p3 = points[2]  # midpoint of river slope
    p4 = points[3]  # top of river slope
    ground_lvl = points[5][1]  # bottom of land slope = ground level

    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    # Helper function for linear interpolation over multiple slope segments
    def interpolate_x(y_target):
        print("new y (target):", y_target)
        if y2 <= y_target <= y3:
            new_x = x2 + (y_target - y2) * (x3 - x2) / (y3 - y2)
        elif y3 <= y_target <= y4:
            new_x = x3 + (y_target - y3) * (x4 - x3) / (y4 - y3)
        else:
            # If outside p2–p4 range, just project on nearest endpoint
            if y_target < min(y2, y4):
                return x2
            elif y_target > max(y2, y4):
                return x4
        print("new  x : ", new_x)
        return new_x

    # Prepare y targets within slope range
    y_targets = sorted([low_wl, high_wl, y3, ground_lvl])
    interpolated_points = np.array([[interpolate_x(y), y] for y in y_targets])

    # Insert new points between p2 and p4
    new_points = np.vstack((points[:2], interpolated_points, points[3:]))
    return new_points





def calc_cover_layer_points(points, low_wl=None, high_wl=None, start_id=4, end_id=7, thickness=0.25,
                            return_parts=False, geometry=None, name_part1='COVER_P1', name_part2='COVER_P2'):
    """
    Create cover layer polyline(s).
    - If low_wl and high_wl are given, returns two parts:
        part1: along the river slope between low_wl and high_wl (offset by thickness)
        part2: from high_wl point up over the top section (Point-4..Point-7) (offset by thickness)
      Return format:
        * if low/high provided: {"part1": [[x,y],...], "part2": [[x,y],...]}
        * if low/high not provided: a single polyline along start_id..end_id offset by thickness (backward compatible).
    Optionally writes polylines to the model geometry if 'geometry' is provided.
    """
    from shapely.geometry import LineString, Point
    from shapely.ops import substring

    def _as_ls(g):
        if g.is_empty:
            return None
        if g.geom_type == "LineString":
            return g
        if g.geom_type == "MultiLineString":
            parts = list(g.geoms)
            parts.sort(key=lambda ls: ls.length, reverse=True)
            return parts[0]
        return None

    def _offset_trim(base_ls, a_pt, b_pt, dist):
        for side in ("left", "right"):
            off = _as_ls(base_ls.parallel_offset(dist, side=side, join_style=2))
            if off is None:
                continue
            s = off.project(Point(a_pt))
            e = off.project(Point(b_pt))
            if s == e:
                continue
            s2, e2 = (s, e) if s < e else (e, s)
            seg = substring(off, s2, e2)
            if not seg.is_empty and len(seg.coords) >= 2:
                return [[float(x), float(y)] for (x, y) in seg.coords]
        return [list(map(float, a_pt)), list(map(float, b_pt))]

    def _interp_x_on_segment(pA, pB, y_target):
        (x1, y1), (x2, y2) = pA, pB
        if y2 == y1:
            return (x1 + x2) / 2.0
        return x1 + (y_target - y1) * (x2 - x1) / (y2 - y1)

    pts = [tuple(map(float, p)) for p in points]
    """
    if end_id <= start_id or end_id > len(pts):
        raise ValueError("Invalid start/end ids for cover layer segment.")
"""
    cover_out_ls = LineString([pts[2], pts[3], pts[4], pts[5], pts[6], pts[7], pts[8]])
    slope_ls = LineString([pts[2], pts[3], pts[4], pts[5], pts[6]])   # river slope P2->P3->P4
    top_ls = LineString([pts[6], pts[7]])     # usually P4..P7
"""
    if low_wl is not None and high_wl is not None:
        low_wl = float(low_wl)
        high_wl = float(high_wl)
        y2, y3, y4 = pts[1][1], pts[2][1], pts[3][1]
        lo = min(y2, y4); hi = max(y2, y4)
        low_wl_c = min(max(low_wl, lo), hi)
        high_wl_c = min(max(high_wl, lo), hi)

        if min(y2, y3) <= low_wl_c <= max(y2, y3):
            x_low = _interp_x_on_segment(pts[1], pts[2], low_wl_c)
        else:
            x_low = _interp_x_on_segment(pts[2], pts[3], low_wl_c)
        if min(y2, y3) <= high_wl_c <= max(y2, y3):
            x_high = _interp_x_on_segment(pts[1], pts[2], high_wl_c)
        else:
            x_high = _interp_x_on_segment(pts[2], pts[3], high_wl_c)

        p_low = (x_low, low_wl_c)
        p_high = (x_high, high_wl_c)

        s = slope_ls.project(Point(p_low)); e = slope_ls.project(Point(p_high))
        s2, e2 = (s, e) if s < e else (e, s)
        slope_sub = substring(slope_ls, s2, e2)
        

        part1 = _offset_trim(slope_sub, p_low, p_high, thickness)

        base2_coords = [p_high] + list(top_ls.coords)
        base2 = LineString(base2_coords)
        part2 = _offset_trim(base2, p_high, top_ls.coords[-1], thickness)

        res = {"part1": part1, "part2": part2}

        if geometry is not None:
            poly_methods = (
                'create_polyline', 'add_polyline', 'create_line', 'add_line',
                'CreatePolyline', 'AddPolyline', 'createPolyline', 'addPolyline',
                'CreateLine', 'AddLine', 'createLine', 'addLine'
            )
            for nm, pts_out in ((name_part1, part1), (name_part2, part2)):
                wrote = False
                for m in poly_methods:
                    if not hasattr(geometry, m):
                        continue
                    fn = getattr(geometry, m)
                    # Try common signatures in order
                    for call in (
                            lambda: fn(name=nm, points=pts_out),
                            lambda: fn(nm, pts_out),
                            lambda: fn(points=pts_out),
                            lambda: fn(pts_out),
                    ):
                        try:
                            call()
                            wrote = True
                            break
                        except Exception:
                            pass
                    if wrote:
                        break

        return res if return_parts or (low_wl is not None and high_wl is not None) else part2

    # Backward-compat: single offset along the top section
    part = _offset_trim(top_ls, top_ls.coords[0], top_ls.coords[-1], thickness)
    if geometry is not None:
        poly_methods = (
            'create_polyline', 'add_polyline', 'create_line', 'add_line',
            'CreatePolyline', 'AddPolyline', 'createPolyline', 'addPolyline',
            'CreateLine', 'AddLine', 'createLine', 'addLine'
        )
        for m in poly_methods:
            if not hasattr(geometry, m):
                continue
            fn = getattr(geometry, m)
            for call in (
                    lambda: fn(name=name_part2, points=part),
                    lambda: fn(name_part2, part),
                    lambda: fn(points=part),
                    lambda: fn(part),
            ):
                try:
                    call()
                    raise StopIteration
                except Exception:
                    pass
        try:
            pass
        except StopIteration:
            pass

    return part
"""
def build_cover_region(points, low_wl, high_wl, start_id=4, end_id=7, thickness=0.5, geometry=None):
    """
    Make a simple closed polygon for the cover:
    - use the same polyline you already compute (part1 + part2) as the TOP edge
    - make a BOTTOM edge by lowering Y by 'thickness'
    - close the loop (bottom reversed)
    """
    parts = calc_cover_layer_points(
        points, low_wl=low_wl, high_wl=high_wl,
        start_id=start_id, end_id=end_id, thickness=thickness,
        return_parts=True, geometry=geometry
    )
    top = (parts.get("part1", []) + parts.get("part2", [])) if isinstance(parts, dict) else (parts or [])
    if not top:
        return []
    bottom = [[x, y - abs(float(thickness))] for (x, y) in reversed(top)]
    poly = top + bottom
    if geometry is not None:
        # ensure these polygon vertices exist in the model before we try to make a region
        geometry.addPoints(poly)
    return poly


def build_subground_strip_polys(layers):
    """
    Turn consecutive 2-point subground layer lines into closed 4-corner polygons:
    [left_a -> left_b -> right_b -> right_a].
    Input 'layers' is what add_subground_layers already returns: [[xL,y],[xR,y]] per layer.
    """
    strips = []
    if not isinstance(layers, list) or len(layers) < 2:
        return strips
    for a, b in zip(layers[:-1], layers[1:]):
        if isinstance(a, list) and len(a) == 2 and isinstance(b, list) and len(b) == 2:
            left_a, right_a = a
            left_b, right_b = b
            strips.append([left_a, left_b, right_b, right_a])
    return strips

def add_slurry_layer(points, thickness=1.0, start_id=1, end_id=4):
    """
    Create a slurry layer below the low water level along the river slope.
    :param points: List of [x, y] coordinate pairs.
    :param thickness: Vertical thickness of the slurry layer.
    :param start_id: 1-based ID of the first point of the slope section.
    :param end_id: 1-based ID of the last point of the slope section.
    :return: List of [x, y] points representing the slurry layer polygon.
    """
    slope_section = points[start_id - 1:end_id]
    y_values = [y for _, y in slope_section]
    low_water_level = min(y_values)
    slurry_bottom = low_water_level - thickness

    # Create slurry layer polygon: top edge at low water level, bottom edge at slurry_bottom
    top_edge = [[x, low_water_level] for x, _ in slope_section]
    bottom_edge = [[x, slurry_bottom] for x, _ in reversed(slope_section)]
    slurry_polygon = top_edge + bottom_edge

    return slurry_polygon


def add_subground_layers(points, layer_thickness=2.0, num_layers=3, geometry=None, name_prefix='SUBGROUND_'):
    """
    Adds points for subground layers below the lowest elevation in the cross-section.
    Each layer is horizontal and follows the x-coordinates of the model boundaries.
    Returns: list-of-layers, each layer is [[x_left,y],[x_right,y]].
    Optionally writes each as a boundary/polyline into the model.
    """
    pts = [list(map(float, p)) for p in points]
    if len(pts) < 2:
        return []

    x_left = pts[0][0]  # Left model boundary
    x_right = pts[-1][0]  # Right model boundary
    min_y = min(y for _, y in pts)

    layers = []
    dh = abs(float(layer_thickness))
    for i in range(1, int(num_layers) + 1):
        y_level = min_y - i * dh
        layer = [[x_left, y_level], [x_right, y_level]]
        layers.append(layer)

    if geometry is not None:
        for idx, layer in enumerate(layers):
            nm = f"{name_prefix}{idx+1}"
            wrote = False
            for m in ('create_layer_boundary','add_layer_boundary','add_subsurface_layer','CreateLayer'):
                if hasattr(geometry, m):
                    try:
                        getattr(geometry, m)(region=None, name=nm, points=layer)
                        wrote = True
                        break
                    except Exception:
                        continue
            if not wrote:
                for m in ('create_polyline','add_polyline','create_line','add_line','CreatePolyline'):
                    if hasattr(geometry, m):
                        try:
                            getattr(geometry, m)(name=nm, points=layer)
                            break
                        except Exception:
                            continue

    return layers

def add_slurry_layer_below_low_wl(points, low_wl, thickness=1.0, start_id=2, end_id=4,
                                  geometry=None, name_top='SLURRY_TOP', name_bottom='SLURRY_BOTTOM',
                                  name_points_prefix='SLURRY_PT'):
    """
    Create a rectangular slurry band on the river slope directly below the low water level.
    - Uses the horizontal at y=low_wl across the slope section (Point-2..Point-4).
    - Returns a polygon (list of [x,y]) tracing top edge (at low_wl) then bottom edge (low_wl - thickness).
    Optionally writes the top/bottom edges as polylines and adds points along the top edge.
    """
    pts = [list(map(float, p)) for p in points]
    if end_id <= start_id or end_id > len(pts):
        return []

    slope = pts[start_id-1:end_id]  # e.g., P2..P4
    top_edge = [[x, float(low_wl)] for x, _ in slope]
    bottom_edge = [[x, float(low_wl) - abs(float(thickness))] for x, _ in reversed(slope)]
    poly = top_edge + bottom_edge

    if geometry is not None:
        # polylines for top and bottom
        for nm, pts_out in [(name_top, top_edge), (name_bottom, list(reversed(bottom_edge)))]:  # bottom reversed for consistent direction
            for method in ('create_polyline','add_polyline','create_line','add_line','CreatePolyline'):
                if hasattr(geometry, method):
                    try:
                        getattr(geometry, method)(name=nm, points=pts_out)
                        break
                    except Exception:
                        continue
        # add discrete points along the top edge
        for i,(x,y) in enumerate(top_edge):
            pid = f"{name_points_prefix}_{i}"
            for pm in ('create_point','add_point','add_node','CreatePoint'):
                if hasattr(geometry, pm):
                    try:
                        getattr(geometry, pm)(name=pid, x=x, y=y)
                        break
                    except Exception:
                        continue

    return poly

def create_all_regions(geometry, regions_point_ids=None):
    """
    Thin wrapper around Geometry.create_all_regions(...), returning the region table for convenience.
    Usage:
        pgs_mb.create_all_regions(geometry)
        pgs_mb.create_all_regions(geometry, regions_point_ids=[[1,2,3,4], [5,6,7,8]])
    """
    if not hasattr(geometry, "create_all_regions"):
        raise AttributeError("Geometry object has no method 'create_all_regions'. Update Geometry.py first.")
    geometry.create_all_regions(regions_point_ids=regions_point_ids)
    # Return a DataFrame of regions (like geometry.point_table)
    if hasattr(geometry, "region_table"):
        return geometry.region_table
    return None

