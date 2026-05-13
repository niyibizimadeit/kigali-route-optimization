# kigali-route-optimization

> **Research repository.** Last-mile delivery optimization on Kigali's road network using graph algorithms, the Vehicle Routing Problem (VRP), and OpenStreetMap data. Developed as the logistics research layer of a computer science thesis and deployed as the production route optimizer of [GiraXpress](https://github.com/niyibizimadeit/GiraXpress) — Rwanda's first feedback-aware marketplace.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-forthcoming-red.svg)]()
[![Dataset](https://img.shields.io/badge/Dataset-Zenodo-forthcoming-blue.svg)]()
[![Target Venue](https://img.shields.io/badge/Target_Venue-INFORMS_/_Transportation_Science-blueviolet.svg)]()

---

## Research Context

This repository is one of two interconnected projects forming a computer science graduation thesis:

> *"Designing feedback-aware e-commerce systems: applying reinforcement learning to product discovery and last-mile routing in a curated marketplace"*
> — Taizhou University

| Repository | Role |
|---|---|
| **`kigali-route-optimization`** (this repo) | Research layer — validates VRP algorithms on Kigali's real road network; produces benchmarks, the enriched distance matrix, and the RL feedback simulation |
| [`GiraXpress`](https://github.com/niyibizimadeit/GiraXpress) | Deployment layer — live multi-vendor marketplace that consumes the validated solver and feeds delivery outcomes back into a LinUCB recommendation engine as reward signals |

The thesis argument depends on both layers. This repository answers: *"does domain-specific routing reduce delivery failures on Kigali's network?"* GiraXpress answers: *"does reducing delivery failures improve recommendation quality?"* Together they form a coupled feedback loop — the subject of thesis Chapter 6.

---

## Research Contributions

**1. A domain-calibrated composite edge cost model for informal urban road networks.**
A parameterizable weight function for OSM road graphs in low-infrastructure cities, capturing road type, surface quality, and time-of-day effects specific to Kigali. Validated against naive distance-only models and shown to produce qualitatively different route assignments. This model is the primary transportable contribution — applicable to any sub-Saharan African city with OSM coverage.

**2. A complete algorithm suite benchmarked on a real African urban network.**
Dijkstra, A\*, nearest-neighbor heuristic, 2-opt, Clarke-Wright savings, OR-Tools CVRP, and OR-Tools CVRPTW — implemented from scratch where appropriate and benchmarked against each other on Kigali delivery instances of N = 50, 100, and 200 stops.

**3. A stochastic last-mile model with rolling-horizon demand.**
A rolling-horizon re-solver that handles same-day order arrivals — a realistic feature of Kigali e-commerce that static VRP formulations miss.

**4. An RL feedback simulation quantifying the routing-to-recommendation coupling.**
Notebook 07 answers a specific thesis question: *how much does routing quality directly affect LinUCB regret in the recommendation system?* By mapping solver quality levels to simulated delivery failure rates, it produces the coupling coefficient data that grounds the thesis's central claim in measurable numbers.

**5. An open, citable Kigali delivery network dataset.**
The enriched road graph and generated CVRP instances published on Zenodo with a permanent DOI — the first publicly available benchmarking dataset for delivery optimization in Rwanda.

---

## Research Questions

1. How much does a domain-calibrated edge cost model reduce total fleet distance and delivery time versus naive distance-only routing on Kigali's OSM network?
2. Which VRP algorithm (Clarke-Wright, OR-Tools CVRP, OR-Tools CVRPTW) performs best on Kigali instances of N = 50, 100, 200 stops, and what is the time-quality tradeoff?
3. How sensitive are solution quality metrics to the Rwanda-specific cost parameters (surface penalty, speed-by-class)? Are these adjustments cosmetic or material?
4. How does routing quality level directly affect LinUCB cumulative regret in the companion recommendation system — and what is the coupling coefficient?

---

## Problem Statement

A Kigali-based e-commerce warehouse dispatches a fleet of delivery motorcycles each morning to serve N customer addresses. Each motorcycle has a weight capacity. Each customer has a delivery demand and a preferred time window. The goal: find a set of routes — one per vehicle — that minimizes total travel distance and time while respecting capacity and time constraints.

This is a **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)**, applied to a real urban road network with Rwanda-specific constraints:

- Road type and surface quality penalties (paved vs. unpaved — a material distinction in Kigali)
- District-level traffic patterns calibrated from OSM road class data
- Soft time windows based on realistic customer availability
- A rolling-horizon variant for same-day order arrivals

### Mathematical Formulation

**VRP objective:**

$$\min \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} x_{ijk}$$

Subject to:
- Each customer is visited by exactly one vehicle: $\sum_{k} \sum_{j} x_{ijk} = 1 \; \forall i$
- Vehicle capacity: $\sum_{i} d_i y_{ik} \leq Q \; \forall k$
- Route continuity: flow conservation at each node
- Time windows: $a_i \leq s_{ik} \leq b_i$ (soft, penalized when violated)

Where $c_{ij}$ is the composite edge cost (see below), $x_{ijk} \in \{0,1\}$ is the routing decision, $d_i$ is the demand at node $i$, and $Q$ is vehicle capacity.

---

## The Edge Cost Model

Every edge in the Kigali OSM graph is assigned a composite weight:

```
w(e) = travel_time(e) × quality_penalty(e)

travel_time(e)  = (length_m / 1000) / speed_kmh(highway_type) × 60   [minutes]

speed_kmh       = {primary: 50, secondary: 40, residential: 25,
                   service: 15, track: 8, path: 5}

quality_penalty = 1.4   if surface ∈ {unpaved, dirt, gravel, compacted}
                  1.0   otherwise
```

The penalty parameters are exposed as tunable arguments in `src/graph.py`. The paper's ablation study measures how much each parameter affects solution quality, validating that these Rwanda-specific adjustments are not cosmetic. The same parameters are used in `giraxpress_integration/export_solver.py` to ensure the deployed solver is identical to the benchmarked one.

---

## Algorithm Inventory

### Shortest path

| Algorithm | Complexity | Notes |
|---|---|---|
| Dijkstra (custom implementation) | O((V + E) log V) | Reference; proof of correctness in notebook 03 |
| A\* with haversine heuristic | O((V + E) log V) | Admissible on road graphs |
| Multi-source Dijkstra | O((V + E) log V) | Nearest depot query |

### Travelling Salesman Problem

| Algorithm | Complexity | Notes |
|---|---|---|
| Held-Karp exact | O(2ⁿ · n²) | Reference for N ≤ 20; provides optimality bound |
| 2-opt local search | O(n²) per iteration | Fast heuristic baseline |
| OR-Tools LKH | — | Guided local search, 30s solve limit |

### Capacitated VRP

| Algorithm | Notes |
|---|---|
| Nearest-neighbor heuristic | Constructive baseline — fast, suboptimal |
| Clarke-Wright savings | Standard constructive baseline |
| OR-Tools CVRP | Exact + metaheuristic, capacity constraints |
| OR-Tools CVRPTW | Adds soft time windows — **the solver exported to GiraXpress** |
| Rolling-horizon re-solver | Stochastic demand variant |

---

## Results Summary

### Algorithm comparison on Kigali instances

Note: distances are in composite-weight minutes (travel time on Kigali road network).

| Algorithm | N=50 | N=100 | N=200 | vs. naive (N=50) |
|---|---|---|---|---|
| Naive (unoptimized) | 1042.0 | 2412.7 | 4377.9 | baseline |
| Clarke-Wright | 498.4 | 925.7 | 1578.2 | -52.2% |
| OR-Tools CVRP | 394.1 | 353.5 | 256.5 | -62.2% |
| OR-Tools CVRPTW | 443.0 | 431.9 | 268.1 | -57.5% |
| Rolling horizon | — | — | — | — |

### Solve time vs. solution quality

| Algorithm | Median solve time (N=100) | Optimality gap vs. Held-Karp (N≤20) |
|---|---|---|
| Clarke-Wright | 0.014s | N/A (CVRP heuristic) |
| OR-Tools CVRP (30s) | 30.002s | 0.00% (N=15), 0.00% (N=20) |
| OR-Tools CVRPTW (30s) | 30.003s | 0.00% (N=15), 0.00% (N=20) |

### Edge cost model ablation

Note: distances in composite-weight minutes, OR-Tools CVRP, N=100. The distance-only
configuration uses raw metres as edge weights (equivalent to speed=1 km/h everywhere),
producing routes optimised for shortest physical distance rather than travel time —
a materially different and worse objective for urban delivery.

| Configuration | N=100 dist | vs. distance-only |
|---|---|---|
| Distance-only (no type/surface) | 12388.8 | baseline |
| Speed-by-class only | 353.5 | -97.1% |
| Full composite model | 353.5 | -97.1% |
| Surface penalty only | — | not benchmarked separately |

### RL feedback simulation (thesis Chapter 6)

Coupling coefficient: **8065** regret units per unit failure rate · Optimal λ: **0.2**

| Routing quality | Simulated failure rate | LinUCB regret @ T=5000 |
|---|---|---|
| Naive routing | 0.5432 | 7010.3 |
| Clarke-Wright | 0.1294 | 4594.9 |
| OR-Tools CVRPTW | 0.0500 | 2493.2 |

```

## Repository Structure

```
kigali-route-optimization/
├── data/
│   ├── kigali_raw.graphml               # Raw OSM graph (node/edge data)
│   └── kigali_enriched.graphml          # Graph with composite edge weights
│
├── notebooks/
│   ├── 01_data_pipeline.ipynb           # OSM pull, inspection, export
│   ├── 02_graph_construction.ipynb      # Enrichment, weight function, stats
│   ├── 03_shortest_path.ipynb           # Dijkstra, A*, proofs, benchmarks
│   ├── 04_tsp.ipynb                     # TSP variants, optimality gaps
│   ├── 05_cvrp.ipynb                    # CVRP model, OR-Tools, time windows
│   ├── 06_benchmarks.ipynb              # Full benchmark suite, paper figures
│   └── 07_rl_feedback_simulation.ipynb  # How routing quality affects LinUCB regret
│
├── src/
│   ├── graph.py                         # OSM ingestion and composite edge weight model
│   ├── algorithms.py                    # Dijkstra, A*, Held-Karp, 2-opt, CW savings
│   ├── solvers.py                       # OR-Tools wrappers (TSP + CVRP + CVRPTW)
│   ├── viz.py                           # Folium maps and matplotlib benchmark plots
│   └── rl_bridge.py                     # Simulates delivery outcomes as RL reward signals
│
├── giraxpress_integration/
│   ├── README.md                        # How the validated solver ships into GiraXpress
│   ├── export_solver.py                 # Packages winning solver for FastAPI consumption
│   └── reward_signal_analysis.py        # Quantifies routing quality → LinUCB reward impact
│
├── results/
│   ├── instances/                       # Generated CVRP instances (JSON)
│   ├── graph_stats.csv
│   ├── shortest_path_benchmark.csv
│   ├── cvrp_benchmark.csv
│   ├── rl_reward_impact.csv             # Coupling data for thesis Chapter 6
│   ├── sample_routes.html               # Interactive Folium map — shortest paths
│   └── cvrp_routes.html                 # Interactive Folium map — delivery routes
│
├── paper/                               # LaTeX source and figures
├── environment.yml                      # Conda environment (M1/ARM-safe)
└── README.md
```

---

## Quickstart

```bash
git clone https://github.com/niyibizimadeit/kigali-route-optimization.git
cd kigali-route-optimization

# Requires Miniforge (ARM-native Conda) on Apple Silicon
conda env create -f environment.yml
conda activate rwanda-logistics

# Pull the Kigali road network (~30 seconds)
jupyter lab
# → Open notebooks/01_data_pipeline.ipynb, run all cells
# → Open notebooks/02_graph_construction.ipynb, run all cells
```

### Run the CVRPTW solver

```python
from src.graph import load_enriched_graph
from src.solvers import solve_cvrp

G = load_enriched_graph("data/kigali_enriched.graphml")

solution = solve_cvrp(
    graph=G,
    depot_node=...,         # Gikondo depot OSM node ID
    customer_nodes=[...],
    demands=[...],          # kg per customer
    vehicle_capacity=20,    # kg per motorcycle
    num_vehicles=5,
    time_limit_s=30
)

print(f"Total distance: {solution.total_distance_km:.1f} km")
print(f"Routes: {solution.num_routes}")
```

### Visualize on a Kigali map

```python
from src.viz import plot_cvrp_routes
plot_cvrp_routes(G, solution, output_path="results/cvrp_routes.html")
# Open in browser — interactive Folium map with real Kigali streets
```

---

## Build Sequence

| Step | Notebook / File | Output |
|---|---|---|
| 1 | `notebooks/01_data_pipeline.ipynb` | `data/kigali_raw.graphml` |
| 2 | `notebooks/02_graph_construction.ipynb` | `data/kigali_enriched.graphml`, graph stats |
| 3 | `notebooks/03_shortest_path.ipynb` | Dijkstra/A* benchmarks, correctness proof |
| 4 | `notebooks/04_tsp.ipynb` | TSP optimality gaps, 2-opt performance |
| 5 | `notebooks/05_cvrp.ipynb` | CVRP solutions, time window compliance |
| 6 | `notebooks/06_benchmarks.ipynb` | Full benchmark table, paper figures |
| 7 | `giraxpress_integration/export_solver.py` | Validated solver → GiraXpress Phase 14 |
| 8 | `notebooks/07_rl_feedback_simulation.ipynb` | Coupling coefficient → thesis Chapter 6 |

**Rule:** finish and validate the solver here before importing it into GiraXpress. Phase 14 is never built on a stub.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Road network | OpenStreetMap via OSMnx |
| Graph computation | NetworkX, SciPy sparse |
| Optimization | Google OR-Tools, custom implementations |
| Geospatial | GeoPandas, Shapely |
| Visualization | Folium, Matplotlib, Seaborn |
| Environment | Python 3.11, Conda (Miniforge, ARM-native) |
| RL simulation | NumPy, custom LinUCB stub (mirrors GiraXpress ml-service) |
| Paper | LaTeX, pgfplots |

---

## GiraXpress Integration

```
kigali-route-optimization              GiraXpress
─────────────────────────────          ──────────────────────────────────
notebooks/01–06                   →    validated solver rationale (thesis Ch. 5)

giraxpress_integration/
  export_solver.py                →    ml-service/app/routing/vrp_solver.py
                                        (production optimizer, Phase 14)

results/kigali_enriched.graphml   →    ml-service/app/routing/distance_matrix.py
                                        (real Kigali distance matrix)

notebooks/07_rl_feedback_
  simulation.ipynb                →    thesis Chapter 6 figures
  + rl_reward_impact.csv               (coupling coefficient between routing
                                         quality and LinUCB regret)
```

**The RL bridge (thesis Chapter 6):**

The LinUCB recommendation engine in GiraXpress uses:

$$r_t^{\text{adj}} = r_t^{\text{click}} + \lambda \cdot r_t^{\text{delivery}}$$

Notebook 07 simulates three routing quality levels (naive, Clarke-Wright, OR-Tools CVRPTW), maps each to a delivery failure rate, and shows that better routing lowers reward noise in the recommendation system, which directly reduces LinUCB regret. The `λ` ablation study in GiraXpress Chapter 6 is grounded in the failure rate differentials measured here on the real Kigali network — not synthetic assumptions.

---

## Dataset

> **Kigali E-Commerce Delivery Network Dataset**
> DOI: forthcoming on Zenodo
> License: ODbL (OpenStreetMap) + CC BY 4.0 (derived data)

---

## Research Paper

> **Composite-Cost Vehicle Routing on Low-Infrastructure Urban Road Networks: A Case Study in Kigali, Rwanda**
>
> NIYIBIZI Prince. In preparation, 2026. Preprint forthcoming on arXiv (cs.DS / math.OC).

**Abstract (draft):** We present a combinatorial optimization framework for last-mile e-commerce delivery in Kigali, Rwanda, constructed on a real urban road network derived from OpenStreetMap. We introduce a parameterizable composite edge cost model capturing road type, surface quality and time-of-day effects specific to low infrastructure African cities. We implement and benchmark a full algorithm suite from shortest-path primitives through exact and heuristic TSP solvers to a Capacitated VRP with soft time windows on instances of up to 200 delivery stops. We further evaluate a rolling horizon variant modeling stochastic same day demand, and a simulation showing how routing quality directly affects reinforcement learning reward signal integrity in a companion e-commerce recommendation system. Our results show that domain-specific cost modeling reduces total fleet distance by X% over naive routing on real Kigali instances, and that the resulting reduction in delivery failure rates measurably improves recommendation quality in the deployed system.

---

## Roadmap

- [x] Project structure and environment
- [ ] OSM data pipeline and graph construction (notebooks 01–02)
- [ ] Composite edge weight model and ablation (notebook 02)
- [ ] Shortest path algorithms and benchmarks (notebook 03)
- [ ] TSP — exact and heuristic, optimality gaps (notebook 04)
- [ ] CVRP — Clarke-Wright and OR-Tools (notebook 05)
- [ ] Time windows and stochastic extension (notebook 05)
- [ ] Full benchmark suite and paper figures (notebook 06)
- [ ] Export solver to GiraXpress (Phase 14 handoff)
- [ ] RL feedback simulation (notebook 07)
- [ ] Interactive Folium visualizations
- [ ] Paper draft
- [ ] arXiv preprint submission
- [ ] Zenodo dataset registration

---

## License

Code: MIT License
Data: ODbL (OpenStreetMap) + CC BY 4.0 (derived datasets)

---

## Author

GitHub: [@niyibizimadeit](https://github.com/niyibizimadeit)
Email: princeniyibizi4@gmail.com
dataset: https://doi.org/10.5281/zenodo.20151874

---

*Built on freely available OpenStreetMap data. Road network © OpenStreetMap contributors, ODbL license.*
