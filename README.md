# Kigali Route Optimization

> **Logistics and last-mile delivery optimization on Kigali's road network using graph algorithms, the Vehicle Routing Problem (VRP), and OpenStreetMap data.**

Built for real-world e-commerce deployment in Rwanda and as the logistics research layer of a computer science thesis at Taizhou University.

---

## Context

This repository is one of two interconnected projects that together form the thesis:

> *"Designing feedback-aware e-commerce systems: applying reinforcement learning to product discovery and last-mile routing in a curated marketplace"*
> — Taizhou University

| Repository | Role |
|---|---|
| **`kigali-route-optimization`** (this repo) | Research layer — validates the VRP solver on Kigali's real road network, produces the benchmarks and the enriched distance matrix |
| [`GiraXpress`](https://github.com/niyibizimadeit/GiraXpress) | Deployment layer — a live multi-vendor e-commerce marketplace that consumes the validated solver and feeds delivery outcomes back into a LinUCB recommendation engine as RL reward signals |

The thesis argument depends on both layers. This repo answers: *"does domain-specific routing actually reduce delivery failures on Kigali's network?"* GiraXpress answers: *"does reducing delivery failures improve recommendation quality?"* Together they form a complete feedback loop.

---

## Overview

This project applies classical and modern combinatorial optimization to the problem of last-mile delivery in Kigali, Rwanda. Using freely available OpenStreetMap (OSM) data, it constructs a realistic weighted road graph, models a Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) with Rwanda-specific constraints, and benchmarks multiple solvers — from hand-implemented algorithms to Google's OR-Tools.

The project is structured to serve two simultaneous goals:

- **Research** — a paper-ready experimental framework with rigorous benchmarking, published as an open dataset and arXiv preprint
- **Deployment** — the validated winning solver is exported directly into GiraXpress's `ml-service/app/routing/vrp_solver.py` as the production optimizer

---

## Problem Statement

A Kigali-based e-commerce warehouse must dispatch a fleet of delivery motorcycles each morning to serve N customer addresses across the city. Each motorcycle has a weight capacity. Each customer has a delivery demand and a preferred time window. The goal is to find a set of routes — one per vehicle — that minimizes total travel distance and time while respecting capacity and time constraints.

This is a **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)**, applied to a real urban road network with domain-specific cost modeling:

- Road type and surface quality penalties (paved vs. unpaved)
- Kigali's district-level traffic patterns
- Soft time windows based on realistic customer availability
- A rolling-horizon variant for same-day order arrivals

---

## Key Contributions

1. **Domain-calibrated edge cost model** — a parameterizable composite weight function for OSM road graphs in low-infrastructure urban environments, validated on Kigali's network
2. **Full algorithm suite** — Dijkstra, A\*, TSP (Held-Karp exact + 2-opt + OR-Tools), CVRP (Clarke-Wright + OR-Tools with time windows), implemented from scratch and benchmarked
3. **Stochastic last-mile model** — static vs. rolling-horizon comparison under realistic demand uncertainty
4. **RL feedback simulation** — `notebook 07` measures how routing quality level directly affects LinUCB regret curves in GiraXpress, producing the coupling coefficient data for thesis Chapter 6
5. **Open dataset** — enriched Kigali road graph and generated delivery instances, published with a DOI on Zenodo

---

## Results Summary

> *Results will be updated as experiments complete.*

| Algorithm | N=50 | N=100 | N=200 | vs. baseline |
|---|---|---|---|---|
| Clarke-Wright (baseline) | — | — | — | — |
| OR-Tools CVRP | — | — | — | — |
| OR-Tools + time windows | — | — | — | — |
| Rolling horizon | — | — | — | — |

**Key finding (placeholder):** OR-Tools with Rwanda-specific constraints reduces total fleet distance by X% versus the Clarke-Wright baseline on Kigali instances, with a median solve time of Y seconds for N=100.

---

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
│   ├── 03_shortest_path.ipynb           # Dijkstra, A*, benchmarks
│   ├── 04_tsp.ipynb                     # TSP variants, optimality gaps
│   ├── 05_cvrp.ipynb                    # CVRP model, OR-Tools, time windows
│   ├── 06_benchmarks.ipynb              # Full benchmark suite, paper figures
│   └── 07_rl_feedback_simulation.ipynb  # How routing quality affects LinUCB
│                                        # regret curves in GiraXpress (thesis Ch. 6)
│
├── src/
│   ├── graph.py                         # OSM ingestion and edge weight model
│   ├── algorithms.py                    # Dijkstra, A*, Held-Karp, 2-opt, CW savings
│   ├── solvers.py                       # OR-Tools wrappers (TSP + CVRP)
│   ├── viz.py                           # Folium maps and matplotlib benchmark plots
│   └── rl_bridge.py                     # Simulates delivery outcomes as RL reward
│                                        # signals; feeds notebook 07
│
├── giraxpress_integration/
│   ├── README.md                        # How the validated solver ships into GiraXpress
│   ├── export_solver.py                 # Packages winning solver for FastAPI consumption
│   └── reward_signal_analysis.py        # Quantifies routing quality → LinUCB reward impact
│
├── results/
│   ├── instances/                       # Generated CVRP instances (JSON)
│   ├── graph_stats.csv                  # Network statistics
│   ├── shortest_path_benchmark.csv
│   ├── cvrp_benchmark.csv
│   ├── rl_reward_impact.csv             # Coupling coefficient data for thesis Chapter 6
│   ├── sample_routes.html               # Interactive Folium map — shortest paths
│   └── cvrp_routes.html                 # Interactive Folium map — delivery routes
│
├── paper/                               # LaTeX source and figures
├── environment.yml                      # Conda environment (M1/ARM-safe)
├── README.md
└── .gitignore
```

---

## Quickstart

### 1. Clone and set up the environment

```bash
git clone https://github.com/niyibizimadeit/kigali-route-optimization.git
cd kigali-route-optimization

# Requires Miniforge (ARM-native Conda) on Apple Silicon
conda env create -f environment.yml
conda activate rwanda-logistics
```

### 2. Pull the Kigali road network

```bash
jupyter lab
# Open notebooks/01_data_pipeline.ipynb and run all cells
# This downloads the Kigali OSM graph (~30 seconds) and saves it to data/
```

### 3. Run the CVRP solver

```python
from src.graph import load_enriched_graph
from src.solvers import solve_cvrp

G = load_enriched_graph("data/kigali_enriched.graphml")

solution = solve_cvrp(
    graph=G,
    depot_node=...,        # Gikondo depot OSM node ID
    customer_nodes=[...],  # List of delivery node IDs
    demands=[...],         # kg per customer
    vehicle_capacity=20,   # kg per motorcycle
    num_vehicles=5,
    time_limit_s=30
)

print(f"Total distance: {solution.total_distance_km:.1f} km")
print(f"Routes: {solution.num_routes}")
```

### 4. Visualize routes

```python
from src.viz import plot_cvrp_routes
plot_cvrp_routes(G, solution, output_path="results/cvrp_routes.html")
# Open results/cvrp_routes.html in your browser
```

### 5. Run the RL feedback simulation

```python
# notebooks/07_rl_feedback_simulation.ipynb
#
# Answers the question: how much does routing quality affect LinUCB regret?
#
# Step 1 — Generate N delivery instances on the enriched Kigali graph
# Step 2 — Solve with naive routing vs Clarke-Wright vs OR-Tools CVRPTW
# Step 3 — Map solver quality → simulated delivery failure rates
# Step 4 — Feed failure rates into LinUCB reward function:
#           r_adj = r_click + λ · r_delivery
# Step 5 — Compare regret curves across routing quality levels
# Step 6 — Output: rl_reward_impact.csv → thesis Chapter 6, Figure X
```

---

## Technical Stack

| Layer | Tools |
|---|---|
| Road network | OpenStreetMap via OSMnx |
| Graph computation | NetworkX, SciPy sparse |
| Optimization | Google OR-Tools, custom implementations |
| Geospatial | GeoPandas, Shapely |
| Visualization | Folium, Matplotlib, Seaborn |
| Environment | Python 3.11, Conda (ARM-native via Miniforge) |
| RL simulation | NumPy, custom LinUCB stub (mirrors GiraXpress ml-service) |
| Paper | LaTeX, pgfplots |

---

## Algorithm Inventory

### Shortest path

| Algorithm | Complexity | Notes |
|---|---|---|
| Dijkstra (custom) | O((V + E) log V) | Reference implementation |
| A\* with haversine heuristic | O((V + E) log V) | Admissible on road graphs |
| Multi-source Dijkstra | O((V + E) log V) | Nearest depot query |

### Travelling Salesman Problem

| Algorithm | Complexity | Notes |
|---|---|---|
| Held-Karp exact | O(2ⁿ · n²) | Reference for N ≤ 20 |
| 2-opt local search | O(n²) per iteration | Fast heuristic baseline |
| OR-Tools LKH | — | Guided local search, 30s limit |

### Capacitated VRP

| Algorithm | Notes |
|---|---|
| Clarke-Wright savings | Fast constructive baseline |
| OR-Tools CVRP | Exact + metaheuristic, capacity constraints |
| OR-Tools CVRPTW | Adds soft time windows — **this is the solver exported to GiraXpress** |
| Rolling horizon re-solver | Stochastic demand variant |

---

## The Edge Cost Model

Every edge in the Kigali graph is assigned a composite weight:

```
w(e) = travel_time(e) × quality_penalty(e)

travel_time(e)  = (length_m / 1000) / speed_kmh × 60   [minutes]

speed_kmh       = f(highway_type)
                  # primary=50, secondary=40, residential=25, track=8, ...

quality_penalty = 1.4 if surface ∈ {unpaved, dirt, gravel} else 1.0
```

The penalty parameters — speed by road class and surface multipliers — are exposed as tunable arguments. The ablation study in the paper measures how much each parameter affects solution quality, proving these Rwanda-specific adjustments are not cosmetic. The same parameters are used in `giraxpress_integration/export_solver.py` to ensure the deployed solver is identical to the benchmarked one.

---

## GiraXpress Integration

This repository is the research foundation for the logistics layer of [GiraXpress](https://github.com/niyibizimadeit/GiraXpress) — Rwanda's first feedback-aware e-commerce marketplace.

**The deployment chain:**

```
kigali-route-optimization          GiraXpress
─────────────────────────          ──────────────────────────────────
notebooks 01–06                →   validated solver rationale
                                   (thesis Chapter 5)

giraxpress_integration/
  export_solver.py             →   ml-service/app/routing/vrp_solver.py
                                   (production optimizer, Phase 14)

results/kigali_enriched.graphml →  ml-service/app/routing/distance_matrix.py
                                   (real Kigali distance matrix, not a stub)

notebooks/07_rl_feedback_
  simulation.ipynb             →   thesis Chapter 6 figures
  + rl_reward_impact.csv           (coupling coefficient between routing
                                    quality and LinUCB regret)
```

**What the RL bridge proves (thesis Chapter 6):**

The LinUCB recommendation engine in GiraXpress uses delivery outcome as a reward signal:

```
r_adj = r_click + λ · r_delivery
```

Notebook 07 runs a simulation across three routing quality levels — naive, Clarke-Wright, and OR-Tools CVRPTW — and shows that better routing directly lowers the delivery failure rate, which lowers reward noise, which reduces LinUCB regret. The `λ` ablation study in GiraXpress Chapter 6 is grounded in the real failure rate differentials measured here on the Kigali network — not synthetic assumptions.

---

## Dataset

The enriched Kigali road graph and all generated CVRP instances are published as a citable open dataset:

> **Kigali E-Commerce Delivery Network Dataset**
> [DOI: 10.5281/zenodo.XXXXXXX] *(to be registered)*
> License: ODbL (OpenStreetMap data) + CC BY 4.0 (derived data)

---

## Paper

> **Composite-Cost Vehicle Routing on Low-Infrastructure Urban Road Networks: A Case Study on Kigali, Rwanda**
>
> *Under preparation. Preprint forthcoming on arXiv (cs.DS / math.OC).*

**Abstract (draft):** We present a combinatorial optimization framework for last-mile e-commerce delivery in Kigali, Rwanda, constructed on a real urban road network derived from OpenStreetMap. We introduce a parameterizable composite edge cost model that captures road type, surface quality, and time-of-day effects specific to low-infrastructure African cities. Building on this model, we implement and benchmark a full algorithm suite — from shortest-path primitives through exact and heuristic TSP solvers to a capacitated VRP with soft time windows — and compare performance against both classical baselines and Google OR-Tools on instances of up to 200 delivery stops. We further evaluate a rolling-horizon variant that models stochastic same-day order arrivals, and a simulation of how routing quality level affects the integrity of reinforcement learning reward signals in a companion e-commerce recommendation system. Our results show that domain-specific cost modeling reduces total fleet distance by X% over naïve routing on real Kigali instances, and that the resulting reduction in delivery failure rates measurably improves recommendation quality in the deployed system.

---

## Execution Order

This repo and GiraXpress are developed in parallel with a deliberate handoff point:

| Week | This repo | GiraXpress |
|---|---|---|
| 9 | Notebooks 01–05, enriched graph, validated solver | — |
| 10 | Notebook 06 (full benchmarks), `export_solver.py` | Phase 14: import solver, wire FastAPI endpoint |
| 11 | Notebook 07 (RL feedback simulation) | Phase 15: feedback loop closure |
| 12 | Paper draft, Zenodo registration | Thesis simulation study |

**Rule:** finish and validate the solver here first, then drop it into GiraXpress. Phase 14 is never built on a stub.

---

## Roadmap

- [x] Project structure and environment
- [ ] OSM data pipeline and graph construction
- [ ] Composite edge weight model
- [ ] Shortest path algorithms and benchmarks
- [ ] TSP — exact and heuristic
- [ ] CVRP — Clarke-Wright and OR-Tools
- [ ] Time windows and stochastic extension
- [ ] Full benchmark suite
- [ ] RL feedback simulation (notebook 07)
- [ ] `giraxpress_integration/` — export solver and reward signal analysis
- [ ] Interactive Folium visualizations
- [ ] Paper draft
- [ ] arXiv preprint
- [ ] Zenodo dataset registration

---

## License

Code: MIT License
Data: ODbL (OpenStreetMap) + CC BY 4.0

---

## Author

GitHub: [@niyibizimadeit](https://github.com/niyibizimadeit)
Email: princeniyibizi4@gmail.com

---

*Built on freely available OpenStreetMap data. Road network © OpenStreetMap contributors, ODbL license.*
