# CoolPath data and methodology

## Provenance and licensing

- **Walking network:** OpenStreetMap contributors, cached Overpass response dated **8 April 2026, 02:36:24 UTC**, supplied in the existing CoolPath project. ODbL 1.0: https://www.openstreetmap.org/copyright . This derived walking graph is made available under ODbL 1.0; source snapshot checksums are in `input-sha256.json`.
- **Tree inventory:** City of Sydney, Trees, existing user snapshot downloaded 8 April 2026; individual observation dates are unknown. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/ . Primary dataset: https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::trees/about . License verified against the City of Sydney ArcGIS item API on 25 October 2026; evidence in `tree-license-evidence.json`.
- City inventory describes **park and street trees only**. Missing campus/private trees are not evidence that an area is unshaded.

## What was preserved and changed

The original `ingest_map.py` downloaded an OSM walking network and stored edges in PostGIS. Original `tree.py` used the `TreeCanopyNS` diameter to construct circular tree canopies, then intersected these with 5 m buffers around roads. Its EPSG:7856 code is GDA2020 / MGA zone 56 (the original comment incorrectly calls it NSW Lambert).

This version uses the actual cached walking response (not the separate drive-network cache), preserves OSM node IDs and connections, and runs routing entirely in the browser. It does not require PostGIS or copy the original hardcoded local database credential. Original Drive files remain unchanged.

The file named `darlington_canopy_2022.tif` is in fact a PNG (PNG magic header), not a georeferenced TIFF. It is **not used** for spatial computations. No coordinates were guessed for that image.

## Graph construction

Only existing consecutive OSM way nodes are connected; no nearest-neighbor connections or invented crossings are added. Access-restricted ways and nodes, indoor paths, motorway/trunk classes, and major roads explicitly tagged without sidewalks are removed. The largest connected component is retained: 6,315 nodes and 7,206 undirected segments. Forty-one smaller components, totaling 263 nodes, are excluded. There are no `oneway:foot` tags in this supplied walking snapshot; motor-vehicle oneway tags do not constrain pedestrian traversal.

Steps remain in the graph. This is **not wheelchair-accessible routing**. Conditions, access hours, barriers and construction must be checked on the ground. The graph may contain street centerlines rather than sidewalk geometry, as in the original OSM walk ingestion; it is not a crossing-safety model.

## Estimated canopy overlap

Coordinates are projected into a local equirectangular metric plane around latitude -33.891 for canopy analysis. Edge lengths use full-precision spherical haversine distance with Earth radius 6,371,000 m. At this small study extent, the local plane is adequate for an approximate canopy proxy; it is not a survey-grade projection.

Each valid tree has a circle of radius `TreeCanopyNS / 2`. Non-tree records, nonpositive diameters and implausible diameters above 80 m are excluded. The original missing-diameter fallback of 4 m is supported; **zero of the retained 10,845 trees needed this fallback**.

For each actual network segment, a rectangular corridor extending 5 m to each side is sampled on a grid with at most 1 m longitudinal spacing and 1 m transverse spacing. The fraction covered by the union of tree circles is stored as `shade` in [0,1]. This is a deterministic midpoint estimate, not an exact geometric intersection. Unlike the original GIS buffer, rectangular segments do not include round end caps. Overlapping circles are counted only once. Tree-radius uncertainty and inventory completeness dominate precision; percentages should be rounded in the UI.

2,562 graph segments have nonzero overlap; total-length-weighted network average is approximately 14.3%.

**Do not interpret this value as the percentage of a walk guaranteed to be shaded.** It is nearby mapped canopy overlap, not live temperature, UV exposure, sunlight, current weather, time-of-day shadows, or building shade. Zero means no recorded overlap, not no actual shade. Route preference balances distance with this proxy, and may select the same route if alternatives are not beneficial.

## Reproduction

Place the supplied cached walking response at `data/raw/osm1.json` and the supplied original tree inventory at `data/raw/trees.geojson`, then run from the project root:

```sh
python scripts/build_graph.py > data/build-report.json
```

Python standard library only. Outputs: `data/graph.json`, `data/trees.json` (optional map circles), and a report on stdout. Original inputs are not needed by the browser and should not be copied into the deployed static directory. Keep these input files locally if reproducible rebuilding is needed.

## Verification

The routing test suite checks every preset pair, shortest-vs-canopy routing, and A* agreement with zero-heuristic search. The default Redfern Station / Lawson Street to USyd / Eastern Avenue route is approximately 1,102 m shortest, and 1,108 m with penalty 2; nearby mapped canopy proxy rises from about 12.3% to 13.5%. These are computational checks against the supplied snapshot, **not a field survey**.
