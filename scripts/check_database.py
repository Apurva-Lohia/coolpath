"""Read-only schema inventory using private local connection configuration."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import text
from backend.config import engine

try:
    db=engine()
    with db.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            print("Connected to configured local PostgreSQL database.")
            print("PostGIS:",connection.execute(text("SELECT extversion FROM pg_extension WHERE extname='postgis'")).scalar())
            for name in ("darlington_streets","weighted_streets"):
                columns=connection.execute(text("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name=:name ORDER BY ordinal_position"),{"name":name}).all()
                print(name,":",[(c[0],c[1]) for c in columns] or "absent")
                if columns:
                    print("Rows:",connection.execute(text("SELECT count(*) FROM public."+name)).scalar())
except Exception:
    print("Database check failed. Configure valid local credentials and database privately; no changes were made.")
    raise SystemExit(1)
