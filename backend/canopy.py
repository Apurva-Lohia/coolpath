"""Exact original tree.py method, without writing/replacing database tables."""
import geopandas as gpd
import numpy as np

def canopy_overlap(roads: gpd.GeoDataFrame, trees: gpd.GeoDataFrame):
    if roads.crs is None or trees.crs is None:
        raise ValueError("Road and tree CRS are required.")
    if "TreeCanopyNS" not in trees:
        raise ValueError("TreeCanopyNS is required.")
    if roads.empty or trees.empty:
        raise ValueError("Roads and tree inventory must not be empty.")
    if not roads.geometry.is_valid.all() or not trees.geometry.is_valid.all():
        raise ValueError("Invalid source geometry; inspect it before processing.")
    projected_roads = roads.to_crs(epsg=7856)
    projected_trees = trees.to_crs(epsg=7856)
    radius = projected_trees["TreeCanopyNS"].fillna(4).astype(float) / 2
    if not np.isfinite(radius).all() or (radius < 0).any():
        raise ValueError("Invalid canopy width; inspect source data.")
    crowns = projected_trees.geometry.buffer(radius)
    # Same polygon union and exact area intersections as original tree.py.
    all_shade = crowns.union_all()
    corridors = projected_roads.geometry.buffer(5)
    if (corridors.area <= 0).any():
        raise ValueError("Road corridor has zero area.")
    result = projected_roads.copy()
    result["shade_pct"] = corridors.intersection(all_shade).area / corridors.area * 100
    return result.to_crs(epsg=4326)
