# GiraXpress Integration Handoff

This folder contains the files that ship the validated Kigali CVRPTW solver into GiraXpress Phase 14. Nothing in this folder should be touched until notebooks 01, 02, and 05 in the research repo are complete and validated.

---

## What Goes Where

| File (this repo) | Destination (GiraXpress) |
|---|---|
| `giraxpress_integration/export_solver.py` | `ml-service/app/routing/vrp_solver.py` |
| `data/kigali_enriched.graphml` | `ml-service/app/routing/kigali_enriched.graphml` |
| `results/kigali_distance_matrix_sample.json` | Used for integration verification only |

## Parameters That Must Stay in Sync

The following constants are defined in both repos and must always match:

| Constant | This repo (`src/graph.py`) | GiraXpress (`ml-service/app/routing/vrp_solver.py`) |
|---|---|---|
| `QUALITY_PENALTY_UNPAVED` | 1.4 | 1.4 |
| `QUALITY_PENALTY_PAVED` | 1.0 | 1.0 |
| `SPEED_BY_HIGHWAY["primary"]` | 50 | 50 |
| `SPEED_BY_HIGHWAY["residential"]` | 25 | 25 |

If you change any of these here, update them in GiraXpress immediately and re-run the integration verification below.

## Reward Constants That Must Stay in Sync

| Constant | This repo (`src/rl_bridge.py`) | GiraXpress (`ml-service/app/constants.py`) |
|---|---|---|
| `DELIVERY_SUCCESS_REWARD` | +3.0 | +3 |
| `DELIVERY_FAILURE_REWARD` | -10.0 | -10 |
| `LAMBDA_DEFAULT` | 0.5 | 0.5 |

## Integration Verification

After copying files to GiraXpress, run this verification to confirm the deployed solver matches the benchmarked one:

```bash
# In this repo
python giraxpress_integration/export_solver.py
# Note the printed manifest: total_distance_km for the 10-node test instance

# In GiraXpress
cd ml-service
python -c "from app.routing.vrp_solver import get_solver; s = get_solver(); print(s.run_test())"
# The output distance must match the manifest above within 0.01 km
```

## When GiraXpress Phase 14 Can Begin

Phase 14 can begin once all of these are true:
- [ ] `notebooks/01_data_pipeline.ipynb` is complete — `data/kigali_raw.graphml` exists
- [ ] `notebooks/02_graph_construction.ipynb` is complete — `data/kigali_enriched.graphml` exists
- [ ] `notebooks/05_cvrp.ipynb` (parts 1 and 2) is complete — CVRPTW solver is validated
- [ ] `python giraxpress_integration/export_solver.py` prints the manifest without error
- [ ] The integration verification above passes
