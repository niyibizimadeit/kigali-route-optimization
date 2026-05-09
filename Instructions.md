# kigali-route-optimization — Instructions

This file defines how this repository is structured, how work flows through it, what each file owns, and how everything connects to GiraXpress. Read this before writing any code.

---

## What This Repo Is

This is the research and logistics layer of the GiraXpress thesis. It has two jobs:

**Job 1 — Validate a production-grade VRP solver for Kigali's road network.**
The OR-Tools CVRPTW solver built here is the exact solver that ships into GiraXpress Phase 14. It is never built as a stub in GiraXpress. It must be validated here first.

**Job 2 — Produce thesis measurement data.**
Benchmarks, regret curves, coupling coefficients, and paper figures all come from this repo. GiraXpress consumes the solver output; this repo produces the evidence that justifies the solver choice.

The thesis argument depends on both. This repo answers: *does domain-specific routing reduce delivery failures on Kigali's network?* GiraXpress answers: *does reducing delivery failures improve recommendation quality?*

---

## Integration Boundary with GiraXpress

The sequential dependency is:

```
This repo                                  GiraXpress
─────────────────────────────────────────────────────────────────
notebooks/01 → data/kigali_raw.graphml
notebooks/02 → data/kigali_enriched.graphml
notebooks/05 → validated CVRPTW solver
                                      ↓
              giraxpress_integration/export_solver.py
                                      ↓
                         ml-service/app/routing/vrp_solver.py     ← Phase 14
                         ml-service/app/routing/distance_matrix.py ← Phase 14
                                      ↓
notebooks/07 → rl_reward_impact.csv
                                      ↓
                         thesis Chapter 6 figures                  ← Phase 15
```

**Rule:** GiraXpress Phase 14 does not begin until notebooks 01, 02, and 05 are complete and validated here. No stubs. No approximations.

---

## Environment Setup (M1 MacBook Pro)

This project requires Miniforge — the ARM-native Conda distribution. Do not use Anaconda or standard Homebrew Python. OR-Tools and OSMnx both have native ARM builds, but only through Miniforge channels.

### One-time Miniforge install

```bash
# Download Miniforge for Apple Silicon
curl -L https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh -o Miniforge3.sh
bash Miniforge3.sh
# Accept license, accept init, restart terminal
```

### Create the project environment

```bash
conda env create -f environment.yml
conda activate rwanda-logistics
```

### Verify the environment

```bash
python -c "import osmnx; print('osmnx:', osmnx.__version__)"
python -c "import networkx; print('networkx:', networkx.__version__)"
python -c "from ortools.constraint_solver import routing_enums_pb2; print('ortools: ok')"
python -c "import geopandas; print('geopandas:', geopandas.__version__)"
python -c "import folium; print('folium:', folium.__version__)"
```

All five must print without error. If OR-Tools fails, the most common cause is using the wrong Conda channel — make sure `environment.yml` specifies `conda-forge`.

### Start Jupyter

```bash
jupyter lab
```

---

## Repository Conventions

### Data files
- `data/kigali_raw.graphml` — raw OSM graph, never edited by hand, always regenerated from notebook 01
- `data/kigali_enriched.graphml` — composite-weight graph, always regenerated from notebook 02
- Never commit large `.graphml` files if they exceed GitHub's 100MB limit — use Git LFS or exclude and document regeneration steps

### Source files (`src/`)
Each file has one job. Never merge responsibilities between files.

| File | Owns |
|------|------|
| `graph.py` | OSM ingestion, composite edge weight model, graph loading/saving |
| `algorithms.py` | Dijkstra, A*, Held-Karp, 2-opt, Clarke-Wright — all custom implementations |
| `solvers.py` | OR-Tools wrappers only — TSP, CVRP, CVRPTW |
| `viz.py` | All visualization — Folium maps, Matplotlib benchmark plots |
| `rl_bridge.py` | Simulates delivery outcomes as RL reward signals — mirrors GiraXpress LinUCB |

### Notebooks (`notebooks/`)
Notebooks are the research layer. They call `src/` functions — they do not implement logic themselves. If you find yourself writing a meaningful function inside a notebook cell, it belongs in `src/` first.

| Notebook | Purpose |
|----------|---------|
| `01_data_pipeline.ipynb` | Pull OSM data, inspect graph, export raw graphml |
| `02_graph_construction.ipynb` | Apply edge cost model, enrich graph, export enriched graphml |
| `03_shortest_path.ipynb` | Dijkstra/A* benchmarks and correctness proofs |
| `04_tsp.ipynb` | TSP variants, optimality gaps |
| `05_cvrp.ipynb` | CVRP and CVRPTW, time windows, rolling horizon |
| `06_benchmarks.ipynb` | Full benchmark suite, paper figures |
| `07_rl_feedback_simulation.ipynb` | How routing quality level affects LinUCB regret |

### Results files (`results/`)
All benchmark CSVs and HTML maps are written by notebooks into `results/`. Never write results by hand. Each notebook documents exactly which result files it produces.

### GiraXpress integration (`giraxpress_integration/`)
This folder is the handoff point. Files here must exactly mirror what GiraXpress consumes:
- `export_solver.py` packages the validated CVRPTW solver into the format expected by `ml-service/app/routing/vrp_solver.py`
- `reward_signal_analysis.py` quantifies routing quality → LinUCB reward impact for thesis Chapter 6
- These files must use the same edge cost parameters as `src/graph.py` — never diverge

---

## The Edge Cost Model

This is the primary transportable research contribution. Every edge in the Kigali OSM graph receives a composite weight:

```
w(e) = travel_time(e) × quality_penalty(e)

travel_time(e)  = (length_m / 1000) / speed_kmh(highway_type) × 60   [minutes]

speed_kmh = {
    primary:     50,
    secondary:   40,
    residential: 25,
    service:     15,
    track:        8,
    path:         5,
    default:     20
}

quality_penalty = 1.4  if surface ∈ {unpaved, dirt, gravel, compacted}
                  1.0  otherwise
```

These parameters are defined in `src/graph.py` as named constants, not magic numbers. They are tunable — the ablation study in notebook 06 measures sensitivity to each. The same parameter values must be used in `giraxpress_integration/export_solver.py`. If you change them here, you change them there too.

---

## The CVRPTW Model

The production solver is a Capacitated VRP with soft Time Windows (CVRPTW). The formulation:

**Objective:** minimize total fleet distance and time

$$\min \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} x_{ijk}$$

**Constraints:**
- Each customer visited by exactly one vehicle
- Vehicle capacity respected: $\sum_{i} d_i y_{ik} \leq Q \; \forall k$
- Route continuity: flow conservation at each node
- Soft time windows: $a_i \leq s_{ik} \leq b_i$ (penalized when violated, not hard-rejected)

The soft time window choice is deliberate — Kigali delivery windows are approximate. Hard windows would produce infeasible instances on the real network.

---

## The RL Bridge

`src/rl_bridge.py` simulates how delivery outcomes feed into the GiraXpress LinUCB recommendation engine. It is not a toy — it must mirror the actual reward signal construction in GiraXpress:

```
r_t_adj = r_t_click + λ × r_t_delivery

r_t_delivery = +3   on successful delivery
r_t_delivery = -10  on failed delivery
```

Notebook 07 uses this bridge to map three routing quality levels (naive, Clarke-Wright, OR-Tools CVRPTW) to simulated failure rates, then shows how each failure rate affects LinUCB cumulative regret. The coupling coefficient produced by this notebook is the quantitative core of thesis Chapter 6.

---

## Golden Rules

- Never implement logic in a notebook cell that belongs in `src/`
- Never edit `data/kigali_raw.graphml` or `data/kigali_enriched.graphml` by hand — always regenerate
- Never change edge cost parameters in one file without changing them in the other
- Never begin GiraXpress Phase 14 before notebooks 01, 02, and 05 are validated
- Every result file in `results/` must be reproducible by re-running the notebook that produced it
- The solver exported to GiraXpress must be byte-for-byte identical in behavior to the one benchmarked here