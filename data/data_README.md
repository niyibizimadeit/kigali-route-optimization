# data/

Road network data files for Kigali, Rwanda.

---

## Files

| File | Size | Contents |
|------|------|----------|
| `kigali_raw.graphml` | ~10 MB | Raw OSM drive network, WGS84 coordinates, standard OSM edge attributes |
| `kigali_enriched.graphml` | ~28 MB | Same graph with `composite_weight` added to every edge |

---

## Graph statistics

| Attribute | Value |
|-----------|-------|
| Nodes | 19,022 |
| Edges | 50,411 |
| CRS | WGS84 (EPSG:4326) |
| OSM data date | 2025 |
| Coverage | Greater Kigali, Rwanda |
| Network type | Drive (motorised vehicles only) |

---

## Edge attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `length` | float | Edge length in metres (computed by OSMnx) |
| `highway` | str | OSM highway tag (primary, secondary, residential, etc.) |
| `surface` | str | OSM surface tag where available (unpaved, dirt, gravel, etc.) |
| `composite_weight` | float | Travel time in minutes, with surface quality penalty applied |

`composite_weight` is only present in `kigali_enriched.graphml`.

---

## Composite weight formula

```
w(e) = travel_time(e) × quality_penalty(e)

travel_time(e) = (length_m / 1000) / speed_kmh(highway_type) × 60   [minutes]

speed_kmh = {primary:50, secondary:40, residential:25, service:15, track:8, path:5, default:20}

quality_penalty = 1.4  if surface ∈ {unpaved, dirt, gravel, compacted, ground, mud, sand, grass}
                  1.0  otherwise
```

---

## How to regenerate

```bash
conda activate rwanda-logistics
jupyter lab
# Run notebooks/01_data_pipeline.ipynb     → kigali_raw.graphml
# Run notebooks/02_graph_construction.ipynb → kigali_enriched.graphml
```

Both notebooks use `os.chdir(os.path.abspath('..'))` to ensure files save here
(repo root `data/`) regardless of where Jupyter is launched from.