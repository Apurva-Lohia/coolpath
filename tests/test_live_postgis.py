"""Opt-in real database checks. Disabled unless a valid local connection is configured."""
import os
import pytest
from sqlalchemy import text
from backend.config import engine
from backend.repository import read_roads, load_weighted_roads, ping
from backend.routing import road_graph, solve

@pytest.mark.skipif(os.environ.get("COOLPATH_LIVE_TEST")!="1",reason="Live PostGIS access not configured; synthetic tests are separate.")
def test_live_postgis_read_only_exact_overlap_and_routing():
    db=engine()
    ping(db)
    original=read_roads(db)
    weighted=load_weighted_roads(db)
    assert len(original)==len(weighted)
    assert weighted.shade_pct.between(0,100).all()
    graph=road_graph(weighted)
    u,v=next((u,v) for u,v in graph.edges() if u!=v)
    assert solve(graph,u,v,2)["distance"]>0
    after=read_roads(db)
    assert len(after)==len(original)
    assert list(after.geometry.to_wkb())==list(original.geometry.to_wkb())
