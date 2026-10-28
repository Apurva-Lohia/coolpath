# CoolPath — local FastAPI/PostGIS walking pilot

The original CoolPath folder contains the existing map UI, FastAPI backend, OSMnx topology, NetworkX A*, and GeoPandas/Shapely canopy processing. The existing database is `sydney_spatial_db` in Docker container `coolpath_db`, exposed at `127.0.0.1:5433`, with PostGIS 3.3.4. The separate PostgreSQL 17 installation is not used.

## Launch

With the existing Docker container running, open PowerShell and run:

```powershell
& "G:\My Drive\Downloads on Laptop\GeoAI projects\CoolPath\scripts\start-local.ps1"
```

Enter the database password privately at the masked prompt. The launcher defaults to database `sydney_spatial_db` and user `apurva`, checks schema read-only, then serves http://127.0.0.1:8765/. Keep the terminal open; Ctrl+C stops it. Passwords are held only in process memory/environment, not printed or written to files. Previous environment values are restored on exit.

If private PostgreSQL connection variables are already configured, `npm start` launches the same backend. No credentials are embedded in the edited ingestion/processing scripts. Do not send passwords in chat.

## Original data and topology

The original `darlington_streets` table contains 1,284 records. Original ingestion omitted OSM edge identifiers. `ingest_map.recover_topology` reconstructs the original walking graph offline from the retained place boundary and Overpass cache, following the pinned OSMnx 2.1.1 construction sequence. All 1,284 stored street geometries and lengths uniquely match the 434-node cached graph.

Recovered `u/v/key` are added only to the derived `weighted_streets` table. Routing retains distinct OSM node identities and original directed edges, including the bidirectional walking edges produced by OSMnx. It does not connect nearby or merely crossing streets.

`tree.py` applies the original calculation through `backend/canopy.py`:

1. Project roads and tree points to EPSG:7856.
2. Buffer every tree by `TreeCanopyNS.fillna(4) / 2` metres.
3. Buffer roads by 5 metres.
4. Union all tree crowns, then calculate exact Shapely intersection area divided by road-buffer area × 100.
5. Return geometries to EPSG:4326.

No tree filtering, radius cap, sampling, or changed corridor width is used. Canopy coverage is a static proxy, not live shade or a cooling guarantee.

Both original scripts now refuse to replace existing tables. `tree.py` creates `weighted_streets` only when absent; it does not change `darlington_streets`. Do not rerun ingestion or processing to overwrite existing results.

## Backend and map

FastAPI reads persisted `weighted_streets` in a read-only transaction. OSMnx `graph_from_gdfs` restores its graph and NetworkX A* minimizes:

`length × (1 + preference × (1 − shade_pct / 100))`

Zero preference gives shortest distance. The heuristic is conservatively scaled to remain admissible. The graph is cached in memory; restart FastAPI after an authorized data change. Every API operation checks database availability. There is no bundled-JSON routing fallback.

The existing map calls `/api/network`, `/api/snap`, and `/api/routes`. Route responses include GeoJSON and the map's existing metrics. FastAPI serves only interface assets; historical browser-routing files are not active routes.

Coverage is limited to the original Darlington graph. Presets outside that graph may be rejected by the retained 100 m snap limit. Routes are not safety-validated, accessibility-certified, or live turn-by-turn navigation.

## Checks

```powershell
Set-Location "G:\My Drive\Downloads on Laptop\GeoAI projects\CoolPath"
.\.venv\Scripts\python.exe -m pytest tests/test_backend.py tests/test_live_postgis.py -q
npm run build
```

The opt-in SQLAlchemy/PostGIS test requires private connection configuration and `COOLPATH_LIVE_TEST=1`; a skipped test is not a live-database pass. Browser fixture tests explicitly use synthetic geometry. Eleven retained Node routing tests exercise historical browser code, while static tests check the current UI's FastAPI contract.

Current run verification is recorded in the task result, distinguishing live database processing from private-password-dependent production backend/browser checks.

## Preserved inputs and scope

Original `plan.md`, `test.py`, `docker-compose.yml`, tree inventory, canopy image, and caches are preserved. `ingest_map.py` and `tree.py` are edited in place as requested. No separate project, new dependencies, database migration, Docker repair, Git push, or deployment is involved. Historical static artifacts remain unused by backend routing.

Data attribution: OpenStreetMap contributors (ODbL 1.0), City of Sydney tree inventory (CC BY 4.0), and Leaflet (BSD 2-Clause).

## Verified restoration results

- Created only `public.weighted_streets`: 1,284 rows, original `u/v/key`, mean canopy overlap 10.0047208665%, range 0–73.3796992324%. Exact calculation took about 299 seconds on this run.
- Confirmed `darlington_streets` rows, attributes and geometry were unchanged before/after creation. Verified original plan, tree inventory, canopy image, test.py, Docker Compose and all three cache hashes unchanged.
- Passed 200 A*/Dijkstra comparisons on the real 434-node/1,284-edge network, nine backend tests, 16 Node checks, build and Python/PowerShell syntax checks.
- Passed Chrome desktop/mobile tests with synthetic data, then with real persisted PostGIS data loaded via existing container-local authentication into a test FastAPI service. Valid Gate 3/Abercrombie routes, preference changes and swaps work. Temporary test servers were stopped.
- Production Windows backend SQLAlchemy authentication and its complete live browser connection still require a private launcher login; they are not claimed as verified. No password was retrieved or persisted.
- Coverage decision remains: Redfern preset is 203.34 m and Eastern Avenue 161.86 m from the original graph, beyond the existing 100 m snap limit. Gate 3 (5.15 m) and Abercrombie Street (57.30 m) work within existing coverage. No network expansion, preset relocation or snap-limit change has been made.
