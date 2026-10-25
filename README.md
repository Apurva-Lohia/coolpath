# CoolPath — Darlington pilot

A real, map-first walking app completing the original CoolPath project's A* routing intent. Static HTML/CSS/JavaScript; no paid API, secret, database server or fake endpoint. The original Drive files remain unchanged.

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

See `data/METHODOLOGY.md`, `data/input-sha256.json`, `data/build-report.json` and `data/tree-license-evidence.json`. Rebuild with `python3 scripts/build_graph.py` after placing the original user-supplied source snapshots in `data/raw/` as described by the script. Raw inputs are intentionally excluded from the repository and deployed app. Original scripts containing local database credentials are not shipped.

- Map/network: © OpenStreetMap contributors, ODbL 1.0, https://www.openstreetmap.org/copyright . The derived graph is distributed at `dist/data/graph.json` under ODbL 1.0.
- Tree inventory: City of Sydney, CC BY 4.0, https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::trees/about . CoolPath transforms canopy widths into estimated circular canopy/corridor overlaps; no endorsement implied.
- Leaflet 1.9.4: BSD 2-Clause, `dist/vendor/LICENSE`.

## Hosting and release boundary

The source repository must remain **private in the owner’s personal GitHub account**, not a University of Sydney organization/server. The repository visibility is separate from the Vercel website’s visibility. A public Vercel pilot is authorized; its downloaded client code and public geodata are necessarily visible to website visitors. No private input snapshots or secrets are deployed. The previous owner-private preview is unchanged. Public-scale use needs tile-provider capacity review, fresh geodata, field validation of crossings/access, and accessibility testing. No paid service is enabled.

## Verification status (25 October 2026)

- PASS: 16 Node tests (11 routing and 5 static checks), including 200 randomized A*/Dijkstra comparisons, all 36 preset origin/destination pairs, real-data zero-heuristic comparison, invalid graph inputs and disconnected graphs.
- PASS: local asset references, unique HTML IDs, declared basic accessibility semantics, matching deployed/tested graph; these are static checks, not an accessibility audit.
- PASS: JavaScript syntax checks, Python compile, input checksums, graph geometry/length/shade validation, source secret-pattern scan.
- PASS: owner-private hosted deployment and private login gate verified by supported cloud browser.
- NOT RUN: app desktop/mobile runtime rendering, hosted asset/tile loading and browser interaction suite. Shell Chromium could not launch under this execution environment's socket restrictions; its authorized wrapper attempt was blocked by a protected read-only path. The supported cloud browser could not reach local preview and was not signed into ChatGPT for the private hosted app. No visibility or authentication workaround was used. Responsive CSS and flows received static review, not a visual pass.
- `tests/ui-qa.cjs` is a prepared browser harness, not a passed result. In an authorized local environment, install Playwright separately and run with `BASE_URL=http://localhost:8765 node tests/ui-qa.cjs`. Optional `PLAYWRIGHT_MODULE` and `CHROMIUM_PATH` select installed tools. Screenshots are local QA output only.

Browser/mobile and field-access validation remain outstanding before this can be described as production-ready navigation. Hosting the pilot does not establish safety or accuracy in the field.

## Deploy to Vercel

1. Create a **private repository in your personal GitHub account** and push this clean source tree to `main`. Do not use a university organization or enterprise GitHub server.
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
