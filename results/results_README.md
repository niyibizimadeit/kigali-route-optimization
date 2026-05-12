# results/

All benchmark outputs, figures, and dataset files produced by this project.
Every file here is reproducible by re-running the notebook listed below.

---

## Files

### Shortest path

| File | Produced by | Contents |
|------|-------------|----------|
| `shortest_path_benchmark.csv` | notebook 03 | Runtime benchmark for Dijkstra, A*, NetworkX across 20 pairs |
| `sample_routes.html` | notebook 03 | Interactive Folium map — 3 sample shortest paths on Kigali streets |

### TSP

| File | Produced by | Contents |
|------|-------------|----------|
| `tsp_benchmark.csv` | notebook 04 | Held-Karp, 2-opt, OR-Tools costs and optimality gaps for N=15,20,30,50 |
| `tsp_gap.png` | notebook 04 | Optimality gap vs N for 2-opt and OR-Tools |

### CVRP

| File | Produced by | Contents |
|------|-------------|----------|
| `cvrp_benchmark.csv` | notebook 05 | Naive, Clarke-Wright, OR-Tools CVRP, CVRPTW for N=50 |
| `cvrp_routes_n50.html` | notebook 05 | Interactive Folium map — N=50 delivery routes |
| `cvrp_benchmark_full.csv` | notebook 06 | Full benchmark: 4 algorithms × N=50,100,200 × 3 reps |
| `cvrp_ablation.csv` | notebook 06 | Edge cost model ablation at N=100 |
| `benchmark_distance.png/.pdf` | notebook 06 | Figure 1: distance by algorithm and N |
| `benchmark_time.png/.pdf` | notebook 06 | Figure 2: solve time by algorithm and N |

### RL feedback simulation

| File | Produced by | Contents |
|------|-------------|----------|
| `rl_reward_impact.csv` | notebook 07 | Failure rate, final regret, coupling coefficient per routing scenario |
| `regret_curves.png/.pdf` | notebook 07 | Figure 3: LinUCB cumulative regret by routing quality level |
| `lambda_ablation.png/.pdf` | notebook 07 | Figure 4: regret at T=5000 vs λ (delivery reward weight) |

### GiraXpress integration

| File | Produced by | Contents |
|------|-------------|----------|
| `kigali_distance_matrix_sample.json` | `giraxpress_integration/export_solver.py` | 20×20 sample distance matrix for integration verification |

### Instance files

| File | Produced by | Contents |
|------|-------------|----------|
| `instances/instance_n50_seed42.json` | notebook 06 | N=50 CVRP instance (nodes, demands, depot) |
| `instances/instance_n100_seed42.json` | notebook 06 | N=100 CVRP instance |
| `instances/instance_n200_seed42.json` | notebook 06 | N=200 CVRP instance |

---

## How to regenerate everything

Run notebooks in order from the repo root (with `rwanda-logistics` kernel active):

```
01_data_pipeline.ipynb        → data/kigali_raw.graphml
02_graph_construction.ipynb   → data/kigali_enriched.graphml
03_shortest_path.ipynb        → shortest_path_benchmark.csv, sample_routes.html
04_tsp.ipynb                  → tsp_benchmark.csv, tsp_gap.png
05_cvrp.ipynb                 → cvrp_benchmark.csv, cvrp_routes_n50.html
06_benchmarks.ipynb           → cvrp_benchmark_full.csv, benchmark_*.png/pdf
07_rl_feedback_simulation.ipynb → rl_reward_impact.csv, regret_curves.png, lambda_ablation.png
```

To regenerate just the paper figures from existing CSVs:
```python
from src.viz import export_all_figures
export_all_figures("results/")
```