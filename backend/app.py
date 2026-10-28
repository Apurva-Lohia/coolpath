"""FastAPI serves the existing map and real PostgreSQL-backed NetworkX routing."""
from threading import Lock
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .config import ROOT, engine
from .repository import ping, load_weighted_roads
from .routing import road_graph, nearest, solve, network_display
from .places import PLACES

class PointInput(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)

class RouteInput(BaseModel):
    start: PointInput
    end: PointInput
    preference: float = Field(default=2, ge=0, le=4, allow_inf_nan=False)

class RoutingService:
    def __init__(self):
        self.db = None
        self.graph = None
        self.display = None
        self.lock = Lock()

    def ready(self):
        with self.lock:
            if self.db is None:
                self.db = engine()
            # Never silently serve an offline/static routing fallback.
            ping(self.db)
            if self.graph is None:
                self.graph = road_graph(load_weighted_roads(self.db))
                self.display = network_display(self.graph, PLACES)
        return self

def create_app(service=None):
    app = FastAPI(title="CoolPath", version="2.0.0")
    app.state.service = service or RoutingService()

    def ready():
        try:
            return app.state.service.ready()
        except Exception:
            # Database exceptions can embed connection parameters: do not expose/log them.
            raise HTTPException(503, "PostGIS routing is unavailable. Check the local database connection, weighted_streets table and original topology. No browser routing fallback is used.") from None

    @app.get("/api/health")
    def health():
        current = ready()
        return {"status":"ok","routing":"NetworkX A*","storage":"PostgreSQL/PostGIS",
                "nodes":current.graph.number_of_nodes(),"edges":current.graph.number_of_edges()}

    @app.get("/api/network")
    def network():
        return ready().display

    @app.post("/api/snap")
    def snap(point: PointInput):
        current = ready()
        try:
            n,d = nearest(current.graph,point.lat,point.lon)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from None
        node = current.graph.nodes[n]
        return {"id":str(n),"lat":node["y"],"lon":node["x"],"distance":d}

    @app.post("/api/routes")
    def routes(request: RouteInput):
        current = ready()
        try:
            start,sd = nearest(current.graph,request.start.lat,request.start.lon)
            end,ed = nearest(current.graph,request.end.lat,request.end.lon)
            shortest = solve(current.graph,start,end,0)
            coolest = solve(current.graph,start,end,request.preference)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from None
        return {"routes":{"cool":coolest,"short":shortest},
                "snap":{"start_m":sd,"end_m":ed},"algorithm":"NetworkX A*"}

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(ROOT/"dist"/"index.html")

    @app.get("/app.mjs", include_in_schema=False)
    def javascript():
        return FileResponse(ROOT/"dist"/"app.mjs",media_type="text/javascript")

    @app.get("/style.css", include_in_schema=False)
    def stylesheet():
        return FileResponse(ROOT/"dist"/"style.css",media_type="text/css")

    app.mount("/vendor",StaticFiles(directory=ROOT/"dist"/"vendor"),name="vendor")
    return app

app = create_app()
