"""OSMnx graph reconstruction and NetworkX A* over PostGIS road geometries."""
import math
import geopandas as gpd
import networkx as nx
import osmnx as ox
from shapely.geometry import Point

def haversine(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    q = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(q)))

def road_graph(roads):
    if roads.crs is None:
        raise ValueError("Road CRS is required.")
    roads = roads.to_crs(4326)
    nodes, edges, identities = [], [], {}
    has_topology = {'u', 'v', 'key'}.issubset(roads.columns)
    original_nodes = {}
    def node_id(coord):
        xy = tuple(coord[:2])
        if xy not in identities:
            identities[xy] = len(identities)
            nodes.append({"osmid": identities[xy], "x": xy[0], "y": xy[1], "geometry": Point(xy)})
        return identities[xy]
    # Production uses recovered original OSM u/v/key; coordinate-only fixtures remain supported.
    for i, row in enumerate(roads.itertuples()):
        geom = row.geometry
        if geom is None or geom.is_empty or geom.geom_type != "LineString" or not geom.is_valid:
            raise ValueError("Roads must contain valid nonempty LineStrings.")
        length, shade = float(row.length), float(row.shade_pct)
        if not math.isfinite(length) or length <= 0 or not math.isfinite(shade) or not 0 <= shade <= 100:
            raise ValueError("Invalid road length or canopy overlap.")
        if has_topology:
            u, v = int(row.u), int(row.v)
            for n, xy in [(u, geom.coords[0]), (v, geom.coords[-1])]:
                xy = tuple(xy[:2])
                if n in original_nodes:
                    if not all(math.isclose(a,b,abs_tol=1e-8,rel_tol=0) for a,b in zip(original_nodes[n],xy)):
                        raise ValueError("Conflicting coordinates for an original OSM node.")
                else:
                    original_nodes[n] = xy
                    nodes.append({"osmid":n, "x":xy[0], "y":xy[1], "geometry":Point(xy)})
        else:
            u, v = node_id(geom.coords[0]), node_id(geom.coords[-1])
        name = getattr(row, "name", None)
        if isinstance(name, (list, tuple)):
            name = " / ".join(map(str, name))
        elif not isinstance(name, str):
            name = "Unnamed walking path"
        edges.append({"u":u, "v":v, "key":int(row.key) if has_topology else i, "length":length,
                      "shade":shade/100, "name":name, "geometry":geom})
    if not edges:
        raise ValueError("No routable roads.")
    ng = gpd.GeoDataFrame(nodes, crs=4326).set_index("osmid")
    eg = gpd.GeoDataFrame(edges, crs=4326).set_index(["u","v","key"])
    # Original OSMnx network_type='walk' is bidirectional; vehicle oneway is not a walking restriction.
    graph = ox.graph_from_gdfs(ng, eg, graph_attrs={"crs":ng.crs})
    if not has_topology:
        graph = nx.MultiGraph(graph)  # synthetic fixtures only; production requires original IDs
    ratios = [1.0]
    for u,v,e in graph.edges(data=True):
        straight = haversine((graph.nodes[u]["y"],graph.nodes[u]["x"]),
                             (graph.nodes[v]["y"],graph.nodes[v]["x"]))
        if straight > 0:
            ratios.append(e["length"]/straight)
    graph.graph["heuristic_scale"] = min(ratios)
    return graph

def nearest(graph, lat, lon, radius=100):
    best = min(graph.nodes, key=lambda n: haversine((lat,lon),(graph.nodes[n]["y"],graph.nodes[n]["x"])))
    node = graph.nodes[best]
    distance = haversine((lat,lon),(node["y"],node["x"]))
    if distance > radius:
        raise ValueError("That point is outside our mapped walking network. Choose a nearby path in the Darlington pilot area.")
    return best, distance

def edge_cost(edge, preference):
    return edge["length"] * (1 + preference * (1-edge["shade"]))

def solve(graph, start, end, preference):
    if not math.isfinite(preference) or not 0 <= preference <= 4:
        raise ValueError("Preference must be between 0 and 4.")
    if start == end:
        raise ValueError("These points resolve to the same mapped location. Choose a destination farther away.")
    def weight(u,v,edges):
        return min(edge_cost(e,preference) for e in edges.values())
    def heuristic(u,v):
        a,b=graph.nodes[u],graph.nodes[v]
        return graph.graph["heuristic_scale"] * haversine((a["y"],a["x"]),(b["y"],b["x"]))
    try:
        path = nx.astar_path(graph,start,end,heuristic=heuristic,weight=weight)
    except nx.NetworkXNoPath as exc:
        raise ValueError("No connected walking route was found. Choose points on the same network.") from exc
    coordinates, segments, distance, covered, cost = [], [], 0., 0., 0.
    for u,v in zip(path,path[1:]):
        e = min(graph[u][v].values(), key=lambda item:edge_cost(item,preference))
        coords = list(e["geometry"].coords)
        origin = graph.nodes[u]
        if not all(math.isclose(a,b,abs_tol=1e-8,rel_tol=0) for a,b in zip(coords[0][:2], (origin["x"],origin["y"]))):
            coords.reverse()
        coordinates.extend([[c[1],c[0]] for c in (coords if not coordinates else coords[1:])])
        segments.append({"name":e["name"],"length":e["length"],"shade":e["shade"]})
        distance += e["length"]; covered += e["length"]*e["shade"]; cost += edge_cost(e,preference)
    nodes = [{"id":str(n),"lat":graph.nodes[n]["y"],"lon":graph.nodes[n]["x"]} for n in path]
    return {"nodes":nodes,"coordinates":coordinates,"edges":segments,"distance":distance,
            "canopyFraction":covered/distance,"cost":cost,
            "geojson":{"type":"Feature","geometry":{"type":"LineString","coordinates":[[lon,lat] for lat,lon in coordinates]},
                       "properties":{"distance_m":distance,"canopy_fraction":covered/distance,"preference":preference}}}

def network_display(graph, places):
    return {"nodes":[{"id":str(n),"lat":d["y"],"lon":d["x"]} for n,d in graph.nodes(data=True)],
            "edges":[{"u":str(u),"v":str(v),"name":e["name"],"shade":e["shade"],
                      "geometry":[[y,x] for x,y,*_ in e["geometry"].coords]}
                     for u,v,e in graph.edges(data=True)],
            "places":places, "source":"PostGIS weighted_streets; original OSMnx topology; exact GeoPandas/Shapely canopy overlap"}
