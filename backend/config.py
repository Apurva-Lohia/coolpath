"""Local PostgreSQL configuration; secrets are never written or logged."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]

def database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    if not os.environ.get("PGDATABASE") or not os.environ.get("PGUSER"):
        raise RuntimeError("Configure DATABASE_URL or PGDATABASE/PGUSER locally.")
    return URL.create("postgresql+psycopg2", username=os.environ["PGUSER"],
        password=os.environ.get("PGPASSWORD"), host=os.environ.get("PGHOST", "127.0.0.1"),
        port=int(os.environ.get("PGPORT", "5433")), database=os.environ["PGDATABASE"])

def engine():
    return create_engine(database_url(), pool_pre_ping=True,
        connect_args={"connect_timeout": 5}, hide_parameters=True)
