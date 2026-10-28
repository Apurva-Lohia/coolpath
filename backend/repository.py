"""Read-only PostGIS access to original streets and persisted canopy weights."""
import geopandas as gpd
from sqlalchemy import text

def ping(engine):
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SELECT PostGIS_Version()")).scalar_one()

def _read(engine, table):
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            roads = gpd.read_postgis("SELECT * FROM public." + table, connection, geom_col="geometry")
    if roads.empty:
        raise ValueError(table + " is empty.")
    return roads

def read_roads(engine):
    return _read(engine, "darlington_streets")

def load_weighted_roads(engine):
    roads = _read(engine, "weighted_streets")
    if not {"u", "v", "key", "shade_pct"}.issubset(roads.columns):
        raise ValueError("weighted_streets lacks original topology or canopy overlap.")
    return roads
