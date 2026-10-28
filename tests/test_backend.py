"""Synthetic geometry/API tests. These do NOT claim a live PostGIS connection."""
import math
import random
import geopandas as gpd
import networkx as nx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point
from backend.canopy import canopy_overlap
from backend.routing import road_graph, solve, nearest, haversine, network_display, edge_cost
from backend.app import create_app
from backend.places import PLACES

def roads_fixture():
    a=(151.1988371,-33.8916059); b=(151.1978,-33.8916059)
    c=(151.1983,-33.8912); d=(151.19,-33.88); e=(151.1905,-33.88)
    rows=[]
    for u,v,shade in [(a,b,0),(a,c,100),(c,b,100),(d,e,20)]:
        rows.append({"geometry":LineString([u,v]),"length":haversine((u[1],u[0]),(v[1],v[0])),
                     "shade_pct":shade,"name":"Test path"})
    return gpd.GeoDataFrame(rows,crs=4326)

def test_exact_canopy_matches_original_and_does_not_double_count():
    roads=gpd.GeoDataFrame({"geometry":[LineString([(334000,6248000),(334030,6248000)])]},crs=7856)
    trees=gpd.GeoDataFrame({"TreeCanopyNS":[10.,10.,None],"geometry":[Point(334010,6248000),Point(334012,6248000),Point(334023,6248000)]},crs=7856)
    result=canopy_overlap(roads,trees)
    original_union=trees.buffer(trees.TreeCanopyNS.fillna(4)/2).union_all()
    corridor=roads.geometry.iloc[0].buffer(5)
    expected=corridor.intersection(original_union).area/corridor.area*100
    assert result.shade_pct.iloc[0]==pytest.approx(expected,abs=1e-10)
    summed=sum(corridor.intersection(t.buffer(r)).area for t,r in zip(trees.geometry,trees.TreeCanopyNS.fillna(4)/2))
    assert result.shade_pct.iloc[0] < summed/corridor.area*100
    assert result.crs.to_epsg()==4326

def test_missing_width_is_original_four_metre_diameter():
    roads=gpd.GeoDataFrame({"geometry":[LineString([(334000,6248000),(334030,6248000)])]},crs=7856)
    trees=gpd.GeoDataFrame({"TreeCanopyNS":[None],"geometry":[Point(334010,6248000)]},crs=7856)
    explicit=trees.copy(); explicit["TreeCanopyNS"]=4.
    assert canopy_overlap(roads,trees).shade_pct.iloc[0]==pytest.approx(canopy_overlap(roads,explicit).shade_pct.iloc[0])

def test_canopy_rejects_invalid_inputs():
    roads=roads_fixture()
    trees=gpd.GeoDataFrame({"TreeCanopyNS":[-2],"geometry":[Point(151.19,-33.89)]},crs=4326)
    with pytest.raises(ValueError): canopy_overlap(roads,trees)

def test_astar_shortest_and_canopy_choice_geometry_reversal():
    graph=road_graph(roads_fixture())
    short=solve(graph,0,1,0); cool=solve(graph,0,1,4)
    assert short["distance"] < cool["distance"]
    assert cool["canopyFraction"] > short["canopyFraction"]
    reverse=solve(graph,1,0,4)
    assert reverse["coordinates"]==list(reversed(cool["coordinates"]))
    assert cool["geojson"]["geometry"]["coordinates"][0]==[151.1988371,-33.8916059]

def test_disconnected_same_node_and_snap_boundary():
    graph=road_graph(roads_fixture())
    with pytest.raises(ValueError,match="connected"): solve(graph,0,3,2)
    with pytest.raises(ValueError,match="same mapped"): solve(graph,0,0,2)
    with pytest.raises(ValueError,match="outside"): nearest(graph,0,0)
    assert nearest(graph,-33.8916059,151.1988371)[0]==0

def test_astar_matches_dijkstra_randomized_parallel_edges():
    rng=random.Random(8301)
    for _ in range(40):
        points=[(151.19+rng.random()*.003,-33.89+rng.random()*.003) for _ in range(8)]
        rows=[]
        for i in range(7):
            for j in range(i+1,8):
                if j==i+1 or rng.random()<.3:
                    for parallel in range(1+(rng.random()<.25)):
                        u,v=points[i],points[j]
                        length=haversine((u[1],u[0]),(v[1],v[0]))*rng.uniform(.95,1.5)
                        rows.append({"geometry":LineString([u,v]),"length":length,"shade_pct":rng.uniform(0,100),"name":"Test"})
        graph=road_graph(gpd.GeoDataFrame(rows,crs=4326))
        for preference in [0,1,2,3,4]:
            weight=lambda u,v,edges:min(edge_cost(e,preference) for e in edges.values())
            expected=nx.dijkstra_path_length(graph,0,7,weight=weight)
            assert solve(graph,0,7,preference)["cost"]==pytest.approx(expected)

class FixtureService:
    def __init__(self):
        self.graph=road_graph(roads_fixture())
        self.display=network_display(self.graph,[dict(PLACES[0]),{**PLACES[1],"lat":-33.8916059,"lon":151.1978}])
    def ready(self): return self

def test_fastapi_routes_validation_and_no_static_fallback():
    client=TestClient(create_app(FixtureService()))
    payload={"start":{"lat":-33.8916059,"lon":151.1988371},"end":{"lat":-33.8916059,"lon":151.1978},"preference":2}
    r=client.post("/api/routes",json=payload)
    assert r.status_code==200
    assert r.json()["routes"]["cool"]["geojson"]["type"]=="Feature"
    assert client.get("/api/network").json()["source"].startswith("PostGIS")
    assert client.get("/").status_code==200
    assert client.get("/data/graph.json").status_code==404
    assert client.get("/routing.mjs").status_code==404
    assert client.post("/api/routes",json={**payload,"preference":5}).status_code==422
    assert client.post("/api/snap",json={"lat":91,"lon":0}).status_code==422

def test_database_failure_is_explicit_and_does_not_leak_credentials():
    class Broken:
        def ready(self): raise RuntimeError("private-password-value")
    client=TestClient(create_app(Broken()))
    for endpoint in ["/api/health","/api/network"]:
        response=client.get(endpoint)
        assert response.status_code==503
        assert "private-password-value" not in response.text
        assert "No browser routing fallback" in response.text

def test_original_osm_ids_keep_colocated_nodes_separate_and_edges_directed():
    a=(151.19,-33.89); b=(151.191,-33.89); c=(151.192,-33.89)
    roads=gpd.GeoDataFrame([
        {"u":101,"v":102,"key":0,"geometry":LineString([a,b]),"length":100.,"shade_pct":10.,"name":"First"},
        {"u":201,"v":202,"key":0,"geometry":LineString([b,c]),"length":100.,"shade_pct":20.,"name":"Separate"}
    ],crs=4326)
    graph=road_graph(roads)
    assert set(graph.nodes)=={101,102,201,202}
    assert graph.is_directed()
    assert solve(graph,101,102,2)["distance"]==100
    with pytest.raises(ValueError,match="connected"): solve(graph,101,202,2)
    with pytest.raises(ValueError,match="connected"): solve(graph,102,101,2)

