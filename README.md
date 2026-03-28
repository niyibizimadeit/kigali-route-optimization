# Kigali Route Optimization

> **Logistics and last-mile delivery optimization on Kigali's road network using graph algorithms, the Vehicle Routing Problem (VRP), and OpenStreetMap data.**

Built for real-world e-commerce deployment in Rwanda and as a research contribution to combinatorial optimization on low-infrastructure African urban road networks.

---

## Overview

This project applies classical and modern combinatorial optimization to the problem of last-mile delivery in Kigali, Rwanda. Using freely available OpenStreetMap (OSM) data, it constructs a realistic weighted road graph, models a capacitated vehicle routing problem (CVRP) with Rwanda-specific constraints, and benchmarks multiple solvers — from hand-implemented algorithms to Google's OR-Tools.

The project is structured to serve three simultaneous goals:

- **Research** — a paper-ready experimental framework with rigorous benchmarking
- **Deployment** — a runnable solver that could be handed to a Kigali e-commerce operator today
- **Portfolio** — clean, documented, reproducible code with a citable dataset

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
4. **Open dataset** — enriched Kigali road graph and generated delivery instances, published with a DOI on Zenodo

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
│   ├── kigali_raw.graphml          # Raw OSM graph (node/edge data)
│   └── kigali_enriched.graphml     # Graph with composite edge weights
│
├── notebooks/
│   ├── 01_data_pipeline.ipynb      # OSM pull, inspection, export
│   ├── 02_graph_construction.ipynb # Enrichment, weight function, stats
│   ├── 03_shortest_path.ipynb      # Dijkstra, A*, benchmarks
│   ├── 04_tsp.ipynb                # TSP variants, optimality gaps
│   ├── 05_cvrp.ipynb               # CVRP model, OR-Tools, time windows
│   └── 06_benchmarks.ipynb         # Full benchmark suite, paper figures
│
├── src/
│   ├── graph.py                    # OSM ingestion and edge weight model
│   ├── algorithms.py               # Dijkstra, A*, Held-Karp, 2-opt, CW savings
│   ├── solvers.py                  # OR-Tools wrappers (TSP + CVRP)
│   └── viz.py                      # Folium maps and matplotlib benchmark plots
│
├── results/
│   ├── instances/                  # Generated CVRP instances (JSON)
│   ├── graph_stats.csv             # Network statistics
│   ├── shortest_path_benchmark.csv
│   ├── cvrp_benchmark.csv
│   ├── sample_routes.html          # Interactive Folium map — shortest paths
│   └── cvrp_routes.html            # Interactive Folium map — delivery routes
│
├── paper/                          # LaTeX source and figures
├── environment.yml                 # Conda environment (M1/ARM-safe)
├── README.md
└── .gitignore
```

---

## Quickstart

### 1. Clone and set up the environment

```bash
git clone https://github.com/YOUR_USERNAME/kigali-route-optimization.git
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
| OR-Tools CVRPTW | Adds soft time windows |
| Rolling horizon re-solver | Stochastic demand variant |

---

## The Edge Cost Model

Every edge in the Kigali graph is assigned a composite weight:

```
w(e) = travel_time(e) × quality_penalty(e)

travel_time(e) = (length_m / 1000) / speed_kmh × 60   [minutes]

speed_kmh      = f(highway_type)   # primary=50, secondary=40, track=8, ...
quality_penalty = 1.4 if surface ∈ {unpaved, dirt, gravel} else 1.0
```

The penalty parameters (speed by road class, surface multipliers) are exposed as tunable arguments. The ablation study in the paper measures how much each parameter affects solution quality — proving these Rwanda-specific adjustments are not cosmetic.

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

**Abstract (draft):** We present a combinatorial optimization framework for last-mile e-commerce delivery in Kigali, Rwanda, constructed on a real urban road network derived from OpenStreetMap. We introduce a parameterizable composite edge cost model that captures road type, surface quality, and time-of-day effects specific to low-infrastructure African cities. Building on this model, we implement and benchmark a full algorithm suite — from shortest-path primitives through exact and heuristic TSP solvers to a capacitated VRP with soft time windows — and compare performance against both classical baselines and Google OR-Tools on instances of up to 200 delivery stops. We further evaluate a rolling-horizon variant that models stochastic same-day order arrivals. Our results show that domain-specific cost modeling reduces total fleet distance by X% over naïve routing on real Kigali instances, and that the rolling-horizon approach recovers Y% of the distance optimality lost to demand uncertainty.

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


GitHub: [@your_username](https://github.com/niyibizimadeit)
Email: princeniyibizi4@gmail.com

---

*Built on freely available OpenStreetMap data. Road network © OpenStreetMap contributors, ODbL license.*
