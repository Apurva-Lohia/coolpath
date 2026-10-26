# CoolPath — Darlington pilot

A real, map-first walking app completing the original CoolPath project's A* routing intent. Static HTML/CSS/JavaScript; no paid API, secret, database server or fake endpoint. The app is integrated into the existing CoolPath folder. Original Python ingestion scripts, Docker configuration, plan, source data and cache are preserved locally.

## Run

Node 20+ for build/tests; Python 3 for the local server:

```sh
npm ci --ignore-scripts
npm run build
npm start
```

Open http://localhost:8765. There are no runtime or build npm dependencies. `npm ci` validates the empty dependency lockfile; the build runs checks and copies only whitelisted public assets into `build/`. Leaflet 1.9.4 is vendored; OpenStreetMap supplies online map tiles. All route calculations and the bounded graph run in-browser. If tile loading fails, the local paths remain available. Internet is required for the initial hosted page and optional basemap; this is not an offline-navigation product.

## What works

- Search six preset destinations and named streets, choose two points on the map, swap start/end, opt into geolocation.
- Real A* shortest-path comparison versus canopy-penalized routing, responsive mobile bottom sheet, route geometry, estimated distance/time and named-path steps.
- Client-side route calculation; selected location is not saved. External OSM tile requests use normal browser caching and attribution.
- 6,315 nodes and 7,206 segments in the largest connected component of the supplied April 2026 OSM walking snapshot.

## Algorithm

Each edge costs `length * (1 + preference * (1 - canopy_fraction))`. Preferences range from 0 to 4. The heuristic is straight-line haversine distance, reduced by the minimum ratio of edge length to endpoint distance so it stays admissible even with rounded edge lengths. This is **A* with canopy-weighted edge costs**, not an inflated-heuristic Weighted A* search. A binary heap manages the open set. Tests compare the result to independent Dijkstra and zero-heuristic search.

`dist/routing.mjs` exposes `buildGraph`, `nearestNode`, `route`, and `haversine`. The routing module also accepts explicitly directed edges. This dataset uses bidirectional walking edges; motor vehicle oneway flags are not treated as walking restrictions.

## Honest limitations

This is a bounded planning pilot, not an all-Sydney navigation service. The original FastAPI/Streamlit/PostGIS deployment plan is replaced here by a browser-only delivery layer to make the pilot usable without infrastructure; the canopy-aware A* intent and real source data are retained. There is no server API implemented or claimed.

“Canopy estimate” is **length-weighted area overlap of modeled tree crowns with a 10 m wide path corridor**, not a measured fraction of a pedestrian's walk in shade. Crown circles come from the City of Sydney street/park tree inventory. Trees on campus/private property may be absent, zero overlap is not proof of no shade, and tree age is unknown. There is no weather, heat measurement, solar geometry, building shade or live shadow model. The file called `darlington_canopy_2022.tif` is a PNG without georeferencing and is excluded.

Default Redfern Station to Eastern Avenue: approximately 1,102 m shortest / 12.3% corridor canopy vs 1,108 m tree-aware / 13.5% at preference 2. The improvement is modest, not a promise of meaningful cooling. Time assumes 80 m/min (4.8 km/h), without waits. Routes snap to network nodes within 100 m, not exact doorstep/edge access. Selected presets are mapped path locations, not guaranteed building entrances. Mapped access/sidewalks may be incomplete. Steps remain in the network: **not wheelchair or step-free routing**. Always check signs, crossings and local access. Not live turn-by-turn navigation.

## Data, provenance and licenses

See `data/METHODOLOGY.md`, `data/input-sha256.json`, `data/build-report.json` and `data/tree-license-evidence.json`. Rebuild with `python3 scripts/build_graph.py` after placing the original user-supplied source snapshots in `data/raw/` as described by the script. Raw inputs are intentionally excluded from the repository and deployed app. Original scripts containing local database credentials remain unchanged locally and are excluded from Git and deployment, together with the raw tree inventory, cache, raster and original plan.

- Map/network: © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright . The derived graph is distributed at `dist/data/graph.json` under ODbL 1.0.
- Tree inventory: City of Sydney, CC BY 4.0, https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::trees/about . CoolPath transforms canopy widths into estimated circular canopy/corridor overlaps; no endorsement implied.
- Leaflet 1.9.4: BSD 2-Clause, `dist/vendor/LICENSE`.

## Hosting and release boundary

The existing personal GitHub repository is https://github.com/Apurva-Lohia/coolpath. This update preserves its history. Local integration and a normal repository update are authorized; no Vercel deployment is performed as part of this step. Repository visibility and website visibility are separate. Original local inputs and credential-bearing scripts are excluded from version control and deployment.

## Verification status (26 October 2026, existing Windows folder)

- PASS: `npm ci --ignore-scripts --no-audit --no-fund`, `npm run build`, JavaScript syntax checks, and all 16 Node tests (11 routing and 5 static checks).
- PASS: 200 randomized A*/Dijkstra comparisons, all 36 preset origin/destination pairs, real-data zero-heuristic comparison, malformed input and disconnected-network checks.
- PASS: Python syntax parsing for all three original Python scripts and `scripts/build_graph.py`, without executing ingestion or accessing the database.
- PASS: real Chrome desktop (1440 x 1000) and mobile viewport (390 x 844) checks against the app served from this folder. Initial routes and basemap rendered, route selection, preference slider, swap, invalid/same endpoints, map-pick cancellation and About dialog worked; no JavaScript page errors occurred.
- PASS: mobile viewport had no horizontal overflow; attribution remained visible. Blocking OSM tiles displayed the warning while both local route cards remained available. Desktop and mobile screenshots received visual review.
- NOT RUN: physical phone testing, actual geolocation, complete map-pick flow, accessibility audit, geodata regeneration, database ingestion, field validation, or Vercel deployment. Viewport emulation is not a physical-device test.
- Optional browser harness: `tests/ui-qa.cjs`. `PLAYWRIGHT_MODULE` and `CHROMIUM_PATH` can select installed tools. Screenshots stay local and are gitignored.

Canopy overlap is a static proxy, not live shade or a cooling guarantee. This pilot is not safety-validated navigation.

## Deploy to Vercel

1. Use the existing personal repository `Apurva-Lohia/coolpath`; preserve its history. Deployment is a separate action requiring authorization.
2. In your intended Vercel account, import that repository. Verify the personal GitHub owner and repository before accepting the integration. A private GitHub repository does not require making source public to host the web app.
3. Use the repository root, framework **Other**, build command `npm run build`, output directory `build`, and install command `npm ci --ignore-scripts --no-audit --no-fund`. These are committed in `vercel.json`; do not override them with a framework preset.
4. No environment variables, API keys, database, paid add-ons or custom domain are required. Use Vercel’s assigned domain. Check plan eligibility and stop before accepting fees or broadening account grants.
5. Deploy, wait for a successful deployment, then inspect the returned domain and verify the initial map, graph asset, both routes, swaps, errors, mobile layout and attribution in a browser. Do not infer a successful deployment from a project creation response.

Builds run all 16 tests before producing assets. Test locally with `python3 -m http.server 8765 --directory build`. No catch-all route rewrite is used: missing assets should return 404 rather than HTML disguised as JSON. Referrer policy preserves the origin referrer required by the OpenStreetMap tile service.

Configuration references: [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json), [Git deployment](https://vercel.com/docs/git).

### Repository layout

```text
dist/                 Editable browser app and bundled public data
data/                 Processed graph, methodology and license evidence
scripts/build.mjs     Deterministic static build, no network access
scripts/build_graph.py  Optional geodata regeneration (original inputs required)
tests/                Routing, static checks, optional browser harness
vercel.json           Vercel static build configuration
build/                Generated deployment output (gitignored)
```

Regenerating the graph is separate from building the website. Place the original walking-network Overpass snapshot at `data/raw/osm1.json` and original tree inventory at `data/raw/trees.geojson`, run `python3 scripts/build_graph.py`, review the result, then copy `data/graph.json` to `dist/data/graph.json`. Raw files are deliberately excluded from Git and deployment; ordinary website builds use the checked-in derived graph and need no original private files.
