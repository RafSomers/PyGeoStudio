"""
Set of functions to build (dike) models in GeoStudio with (local forked) PyGeoStudio
====================================================================================
Haarith's version
====================================================================================
Use with 'import pgs_modelbuilder as pgs_mb'
USes:
    - Quantile Excel: cross_sections_schelde_quantiles.xlsx
"""

import pandas as pd
import numpy as np
from shapely.geometry import LineString, MultiPoint
from shapely.ops import substring


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

