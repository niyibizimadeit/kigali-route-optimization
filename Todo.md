# kigali-route-optimization — Todo

Phases are sequential. Do not start a phase until all validation checkpoints in the previous phase pass. Phases 1–9 build the research repo. Phase 10 is the GiraXpress handoff. Phases 11–15 complete the thesis measurement work.

---

## Phase 1 — Environment and Project Scaffold

**Goal:** A working Miniforge environment on M1, all dependencies installed and verified, and all source files created as proper stubs with correct structure.

**Scope:**

Update `environment.yml` to include all required packages with pinned versions:
- `python=3.11`
- `osmnx`
- `networkx`
- `geopandas`
- `shapely`
- `folium`
- `ortools`
- `scipy`
- `numpy`
- `matplotlib`
- `seaborn`
- `jupyterlab`
- `ipykernel`

All packages from `conda-forge` channel (required for ARM-native builds on M1).

Create the following files in `src/`:
- `graph.py` — stub with module docstring, import block, and empty function signatures for `load_raw_graph()`, `enrich_graph()`, `load_enriched_graph()`, and the edge cost constants block
- `algorithms.py` — stub with module docstring and empty function signatures for `dijkstra()`, `astar()`, `held_karp()`, `two_opt()`, `clarke_wright()`
- `solvers.py` — stub with module docstring and empty function signatures for `solve_tsp()`, `solve_cvrp()`, `solve_cvrptw()`
- `viz.py` — stub with module docstring and empty function signatures for `plot_graph()`, `plot_routes()`, `plot_cvrp_routes()`, `plot_benchmark()`
- `rl_bridge.py` — stub with module docstring, reward constants matching GiraXpress (`CLICK_REWARD = 1`, `CART_REWARD = 5`, `PURCHASE_REWARD = 20`, `DELIVERY_SUCCESS_REWARD = 3`, `DELIVERY_FAILURE_REWARD = -10`), and empty function signatures for `simulate_delivery_outcomes()` and `compute_linucb_regret()`

Create `giraxpress_integration/` directory with:
- `README.md` — one paragraph describing the handoff contract (this file ships into GiraXpress Phase 14)
- `export_solver.py` — stub
- `reward_signal_analysis.py` — stub

Create `notebooks/` stubs — seven `.ipynb` files with a title cell and a single markdown cell describing the notebook's purpose. No code yet.

**Validation:**
```bash
conda env create -f environment.yml
conda activate rwanda-logistics
python -c "import osmnx; print('osmnx:', osmnx.__version__)"
python -c "import networkx; print('networkx:', networkx.__version__)"
python -c "from ortools.constraint_solver import routing_enums_pb2; print('ortools: ok')"
python -c "import geopandas; print('geopandas:', geopandas.__version__)"
python -c "import folium; print('folium:', folium.__version__)"
python -c "from src.graph import load_raw_graph; print('src/graph.py: ok')"
python -c "from src.algorithms import dijkstra; print('src/algorithms.py: ok')"
python -c "from src.solvers import solve_cvrptw; print('src/solvers.py: ok')"
```

All nine lines must print without error before moving on.

---

## Phase 2 — OSM Data Pipeline (notebook 01)

**Goal:** Pull the Kigali road network from OpenStreetMap, inspect it, and export the raw graph to `data/kigali_raw.graphml`. This is the foundation for everything that follows.

**Scope:**

Implement `src/graph.py` — `load_raw_graph()` function:
- Use `osmnx.graph_from_place("Kigali, Rwanda", network_type="drive")` to pull the road network
- Project to UTM (metric coordinates) using `osmnx.project_graph()`
- Save to `data/kigali_raw.graphml` using `osmnx.save_graphml()`
- Return the graph object

Complete `notebooks/01_data_pipeline.ipynb`:
- **Cell 1:** Imports and config
- **Cell 2:** Call `load_raw_graph()`, time the OSM pull, print node and edge count
- **Cell 3:** Basic graph stats — number of nodes, edges, connected components, average degree
- **Cell 4:** Plot the raw graph using `osmnx.plot_graph()` — verify it looks like Kigali
- **Cell 5:** Inspect edge attributes — what OSM tags are present (`highway`, `surface`, `length`, `maxspeed`, `lanes`)
- **Cell 6:** Count what percentage of edges have a `surface` tag — this determines how many edges the quality penalty will apply to
- **Cell 7:** Export `data/kigali_raw.graphml` and print file size
- **Cell 8:** Reload from disk and verify node/edge count matches — confirms the export/import is lossless

**Validation:**
- `data/kigali_raw.graphml` exists and is non-empty
- Reloaded graph has the same node count as the pulled graph
- Edge attribute inspection shows `highway` is present on all (or nearly all) edges
- The graph plot visually looks like Kigali's road network (you will recognize major roads)
- At least 50% of edges have a `length` attribute in meters

---

## Phase 3 — Graph Enrichment and Edge Cost Model (notebook 02)

**Goal:** Apply the composite edge cost model to every edge in the raw graph, producing the enriched graph that all solvers will use. This is the primary research contribution of the repo.

**Scope:**

Implement `src/graph.py` — `enrich_graph()` function:
- Define edge cost constants as named module-level variables (not magic numbers):
  ```python
  SPEED_BY_HIGHWAY = {
      "primary": 50, "secondary": 40, "residential": 25,
      "service": 15, "track": 8, "path": 5, "default": 20
  }
  UNPAVED_SURFACES = {"unpaved", "dirt", "gravel", "compacted", "ground", "mud"}
  QUALITY_PENALTY_UNPAVED = 1.4
  QUALITY_PENALTY_PAVED = 1.0
  ```
- For each edge, compute:
  - `speed_kmh` from `highway` tag using `SPEED_BY_HIGHWAY` (fall back to `default`)
  - `travel_time_min` = `(length_m / 1000) / speed_kmh × 60`
  - `quality_penalty` = 1.4 if `surface` in `UNPAVED_SURFACES`, else 1.0
  - `composite_weight` = `travel_time_min × quality_penalty`
- Add `composite_weight` as a new edge attribute on every edge
- Save to `data/kigali_enriched.graphml`
- Return the enriched graph

Implement `src/graph.py` — `load_enriched_graph()` function:
- Load from `data/kigali_enriched.graphml` and return the graph

Complete `notebooks/02_graph_construction.ipynb`:
- **Cell 1:** Imports, load raw graph
- **Cell 2:** Call `enrich_graph()`, verify `composite_weight` attribute exists on all edges
- **Cell 3:** Distribution plot — histogram of `composite_weight` values across all edges. Look for a bimodal shape (paved vs. unpaved)
- **Cell 4:** Spot-check — find the 10 highest-weight edges and print their `highway` and `surface` tags. These should be tracks or unpaved paths.
- **Cell 5:** Spot-check — find the 10 lowest-weight edges. These should be primary roads.
- **Cell 6 (ablation setup):** Build three alternative versions of the graph: distance-only (no type/surface), speed-by-class only (no surface penalty), full composite model. Print mean edge weight for each.
- **Cell 7:** For a fixed sample of 5 source-destination pairs, compute shortest paths under each of the three weight configurations. Print path lengths and note qualitative differences.
- **Cell 8:** Export enriched graph, reload, verify `composite_weight` survives round-trip to disk.

**Validation:**
- Every edge in the enriched graph has a `composite_weight` attribute — zero edges missing
- `composite_weight` is always positive
- Mean composite weight for unpaved edges is 1.4× the mean for paved edges (within tolerance)
- `data/kigali_enriched.graphml` loads without error via `load_enriched_graph()`
- The three ablation configurations produce different path assignments on the sample pairs

---

## Phase 4 — src/graph.py Hardening

**Goal:** `src/graph.py` is production-ready — robust error handling, clean public API, and fully consistent with what `giraxpress_integration/export_solver.py` will need to consume.

**Scope:**

Review and harden every function in `src/graph.py`:
- `load_raw_graph(output_path="data/kigali_raw.graphml")` — if the file already exists and `force_refresh=False`, load from disk instead of re-pulling OSM. Add a `force_refresh` parameter.
- `enrich_graph(G, params=None)` — accept an optional `params` dict that overrides the default constants. This is how the ablation study swaps configurations without editing source code.
- `load_enriched_graph(path="data/kigali_enriched.graphml")` — raise a clear `FileNotFoundError` with an actionable message if the file doesn't exist ("Run notebook 02 first")
- Add a `get_node_coordinates(G, node_id)` helper — returns `(lat, lon)` for a given OSM node ID. This will be used heavily by the solver and visualizer.
- Add a `build_distance_matrix(G, node_ids, weight="composite_weight")` function — takes a list of OSM node IDs and returns an N×N matrix of shortest-path costs. This is the exact function that `export_solver.py` will call.

Write a `src/graph_test.py` — not a full test suite, just a `main()` block that runs the key assertions:
```bash
python src/graph_test.py
```
Must print `all checks passed` without error.

**Validation:**
- `load_raw_graph(force_refresh=False)` loads from disk without hitting OSM on second call
- `enrich_graph(G, params={"QUALITY_PENALTY_UNPAVED": 2.0})` applies the override correctly
- `build_distance_matrix(G, node_ids)` returns an N×N numpy array with zeros on the diagonal
- `python src/graph_test.py` prints `all checks passed`

---

## Phase 5 — Shortest Path Algorithms (notebook 03)

**Goal:** Implement Dijkstra and A* from scratch in `src/algorithms.py`, verify correctness against NetworkX's reference implementation, and benchmark runtime on the Kigali graph.

**Scope:**

Implement in `src/algorithms.py`:

`dijkstra(G, source, target, weight="composite_weight")`:
- Classic priority-queue Dijkstra
- Returns `(path, cost)` tuple — path as list of node IDs, cost as float
- Must handle disconnected graphs gracefully (return `None, inf` if no path)

`astar(G, source, target, weight="composite_weight")`:
- A* with haversine heuristic (great-circle distance between nodes using their lat/lon)
- Same return signature as `dijkstra`
- The heuristic must be admissible — never overestimates true cost

Complete `notebooks/03_shortest_path.ipynb`:
- **Cell 1:** Imports, load enriched graph
- **Cell 2:** Sample 20 random source-destination pairs from the graph
- **Cell 3:** For each pair, run custom Dijkstra, custom A*, and `nx.dijkstra_path` (reference). Assert all three return the same path cost (within floating point tolerance).
- **Cell 4:** Correctness proof — for a small subgraph of 50 nodes where Held-Karp gives the true shortest path, verify Dijkstra matches it exactly
- **Cell 5:** Runtime benchmark — for N = 100, 500, 1000 random pairs, time each algorithm. Plot runtime distribution as a boxplot.
- **Cell 6:** Visualize 3 sample paths on a Folium map — call `src/viz.py`'s `plot_routes()`. Save to `results/sample_routes.html`.
- **Cell 7:** Write results to `results/shortest_path_benchmark.csv`

**Validation:**
- Custom Dijkstra matches NetworkX reference within 1e-6 on all 20 sample pairs
- Custom A* matches Dijkstra on all 20 sample pairs
- `results/shortest_path_benchmark.csv` exists with columns: `algorithm`, `n_pairs`, `mean_ms`, `median_ms`, `p95_ms`
- `results/sample_routes.html` opens in a browser and shows paths on Kigali streets

---

## Phase 6 — TSP Solvers (notebook 04)

**Goal:** Implement Held-Karp exact TSP and 2-opt local search in `src/algorithms.py`. Benchmark against OR-Tools LKH. Establish optimality bounds for small instances.

**Scope:**

Implement in `src/algorithms.py`:

`held_karp(dist_matrix)`:
- Dynamic programming exact TSP solver
- Accepts an N×N distance matrix (numpy array)
- Returns `(tour, cost)` — tour as list of indices, cost as float
- Practical limit: N ≤ 20 (exponential complexity)

`two_opt(tour, dist_matrix, max_iterations=1000)`:
- 2-opt local search improvement
- Accepts an initial tour and distance matrix
- Returns improved `(tour, cost)`

Add to `src/solvers.py`:

`solve_tsp_ortools(dist_matrix, time_limit_s=30)`:
- OR-Tools TSP solver with guided local search
- Returns `(tour, cost)`

Complete `notebooks/04_tsp.ipynb`:
- **Cell 1:** Imports, load enriched graph, build distance matrix for 15-node sample
- **Cell 2:** Run Held-Karp on 15-node instance. This is the optimal solution.
- **Cell 3:** Run 2-opt starting from a random tour. Compute optimality gap vs Held-Karp.
- **Cell 4:** Run 2-opt starting from a nearest-neighbor construction. Compute optimality gap.
- **Cell 5:** Run OR-Tools LKH on the same 15-node instance. Compute optimality gap.
- **Cell 6:** Scale test — run all three heuristics on N = 20, 30, 50 node instances. Held-Karp only on N ≤ 20.
- **Cell 7:** Plot optimality gap vs N for each heuristic. This becomes a paper figure.
- **Cell 8:** Write results to `results/tsp_benchmark.csv`

**Validation:**
- Held-Karp returns the true optimum on instances where brute force confirms it (N ≤ 10)
- 2-opt always improves or equals the initial tour — never makes it worse
- OR-Tools result is within 5% of Held-Karp on 15-node instances
- `results/tsp_benchmark.csv` exists

---

## Phase 7 — CVRP: Clarke-Wright and OR-Tools (notebook 05, part 1)

**Goal:** Implement the Clarke-Wright savings algorithm in `src/algorithms.py` and the OR-Tools CVRP wrapper in `src/solvers.py`. Validate both on Kigali instances with N = 50 stops.

**Scope:**

Implement in `src/algorithms.py`:

`clarke_wright(dist_matrix, demands, vehicle_capacity, depot_idx=0)`:
- Classic Clarke-Wright savings construction heuristic
- Returns a `CVRPSolution` dataclass: `routes` (list of lists of node indices), `total_cost`, `num_vehicles_used`

Define in `src/solvers.py`:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class CVRPSolution:
    routes: List[List[int]]       # each route is a list of node indices
    total_distance_km: float
    num_routes: int
    solve_time_s: float
    algorithm: str
```

Implement in `src/solvers.py`:

`solve_cvrp(graph, depot_node, customer_nodes, demands, vehicle_capacity, num_vehicles, time_limit_s=30)`:
- Builds distance matrix from graph using `src/graph.build_distance_matrix()`
- Runs OR-Tools CVRP with capacity constraints
- Returns `CVRPSolution`

Complete `notebooks/05_cvrp.ipynb` — part 1:
- **Cell 1:** Imports, load enriched graph
- **Cell 2:** Generate a synthetic N=50 delivery instance — sample 50 random nodes from the Kigali graph as customer locations, assign random demands (1–5 kg each), set depot at a central Kigali node (Gikondo area), 5 vehicles each with 20 kg capacity
- **Cell 3:** Run Clarke-Wright. Print total distance, number of routes, solve time.
- **Cell 4:** Run OR-Tools CVRP. Print total distance, number of routes, solve time.
- **Cell 5:** Compare Clarke-Wright vs OR-Tools — distance gap, routes used, solve time. This comparison is a paper figure.
- **Cell 6:** Visualize OR-Tools solution on Folium map — each route a different color. Save to `results/cvrp_routes_n50.html`.

**Validation:**
- `CVRPSolution` dataclass is importable from `src/solvers.py`
- Clarke-Wright produces a feasible solution — no route exceeds vehicle capacity
- OR-Tools produces a feasible solution with shorter or equal total distance vs Clarke-Wright
- `results/cvrp_routes_n50.html` opens in browser and shows color-coded routes on Kigali streets

---

## Phase 8 — CVRPTW: Time Windows and Rolling Horizon (notebook 05, part 2)

**Goal:** Add soft time windows to the OR-Tools solver, making it the production-grade CVRPTW that ships to GiraXpress. Then implement the rolling-horizon stochastic extension.

**Scope:**

Update `src/solvers.py`:

Extend `CVRPSolution` dataclass:
```python
@dataclass
class CVRPSolution:
    routes: List[List[int]]
    total_distance_km: float
    num_routes: int
    solve_time_s: float
    algorithm: str
    time_window_violations: int = 0      # count of soft window violations
    estimated_arrival_times: dict = None # node_idx → estimated arrival time (minutes)
```

Implement `solve_cvrptw(graph, depot_node, customer_nodes, demands, vehicle_capacity, num_vehicles, time_windows, time_limit_s=30)`:
- `time_windows` is a list of `(earliest_min, latest_min)` tuples, one per customer node
- Soft time windows — violations are penalized, not forbidden (add a large penalty per minute of violation to the OR-Tools objective)
- Returns updated `CVRPSolution` with `time_window_violations` and `estimated_arrival_times` populated

Implement `solve_rolling_horizon(graph, depot_node, initial_orders, new_order_stream, vehicle_capacity, num_vehicles, re_solve_interval_min=60)`:
- Accepts an `initial_orders` list and a `new_order_stream` (list of `(arrival_time_min, node, demand)` tuples)
- Re-solves every `re_solve_interval_min` minutes, incorporating new orders
- Returns a list of `CVRPSolution` objects, one per solve interval
- This is the stochastic variant for the thesis

Complete `notebooks/05_cvrp.ipynb` — part 2:
- **Cell 7:** Add time windows to the N=50 instance — assign each customer a 2-hour window centered on a random preferred delivery time
- **Cell 8:** Run `solve_cvrptw`. Print violations count, estimated arrival times for 3 sample customers.
- **Cell 9:** Compare CVRP vs CVRPTW — does adding time windows increase total distance? By how much?
- **Cell 10:** Rolling horizon simulation — 30 orders at dispatch, 20 more arrive during the day in 3 batches. Run `solve_rolling_horizon`. Print how routes change across solve intervals.
- **Cell 11:** Write all results to `results/cvrp_benchmark.csv` with columns: `algorithm`, `n_stops`, `total_dist_km`, `n_vehicles`, `solve_time_s`, `tw_violations`

**Validation:**
- `solve_cvrptw` returns a feasible solution with `time_window_violations` ≥ 0
- `estimated_arrival_times` is populated for every customer node
- Rolling horizon produces a different route plan after each new order batch
- `results/cvrp_benchmark.csv` exists with all four algorithm rows for N=50

---

## Phase 9 — src/solvers.py and src/viz.py Hardening

**Goal:** Both modules are production-ready with clean APIs before the GiraXpress handoff. `viz.py` is fully implemented. Everything is importable and callable without notebook context.

**Scope:**

Harden `src/solvers.py`:
- All three solver functions (`solve_tsp_ortools`, `solve_cvrp`, `solve_cvrptw`) have consistent signatures and return types
- All three raise `ValueError` with a clear message if inputs are invalid (empty customer list, capacity ≤ 0, etc.)
- Add a `naive_assignment(customer_nodes, num_vehicles)` function — round-robin assignment with no routing optimization. This is the baseline that GiraXpress Phase 14 compares against.

Implement `src/viz.py` fully:

`plot_graph(G, output_path=None)`:
- Folium map of the full Kigali road network, colored by `highway` type

`plot_routes(G, paths, node_ids, output_path=None)`:
- Folium map showing a list of paths (from shortest path algorithms)

`plot_cvrp_routes(G, solution: CVRPSolution, node_coordinates, output_path=None)`:
- Folium map with each route in a distinct color, depot marked separately, customer markers numbered
- This is the exact function the GiraXpress admin map view will be modeled on

`plot_benchmark(csv_path, metric, group_by, output_path=None)`:
- Matplotlib bar chart from a benchmark CSV — used for paper figures

Write `src/solvers_test.py` — a `main()` block that runs the key solver assertions on a tiny 5-node toy instance where the correct answer is known:
```bash
python src/solvers_test.py
```

**Validation:**
- `python src/solvers_test.py` prints `all checks passed`
- `plot_cvrp_routes` produces an HTML file that opens in a browser with colored routes visible on Kigali streets
- `naive_assignment` produces routes where total distance is strictly greater than `solve_cvrptw` on any non-trivial instance

---

## Phase 10 — GiraXpress Integration Handoff

**Goal:** The validated CVRPTW solver is packaged and ready to be dropped into GiraXpress Phase 14. This phase produces the exact files that GiraXpress consumes — nothing more, nothing less.

**Scope:**

This phase produces three outputs. Nothing in GiraXpress is touched yet — these outputs are written here and then manually copied into GiraXpress when Phase 14 begins.

**Output 1 — `giraxpress_integration/export_solver.py`:**

Implement this as a standalone script that:
- Loads `data/kigali_enriched.graphml` via `src/graph.load_enriched_graph()`
- Exposes a `get_solver()` function that returns a configured `solve_cvrptw` callable with the Kigali graph already bound
- Exposes a `get_distance_matrix_builder()` function that returns the `build_distance_matrix` callable
- Prints a manifest when run directly: algorithm name, edge cost parameters, graph node count, graph edge count, solve time on a 10-node test instance

The output of this script is exactly what goes into `ml-service/app/routing/vrp_solver.py` in GiraXpress.

**Output 2 — `results/kigali_distance_matrix_sample.json`:**

A 20×20 sample distance matrix (20 Kigali nodes, composite weights) saved as JSON. This is used to verify the distance matrix in GiraXpress matches what was produced here.

**Output 3 — `giraxpress_integration/README.md`:**

A clear handoff document describing:
- Which files to copy where in GiraXpress
- What parameters must stay in sync (`QUALITY_PENALTY_UNPAVED`, `SPEED_BY_HIGHWAY`)
- How to verify the deployed solver matches the benchmarked one (run the 10-node test instance and compare output to the manifest)
- What GiraXpress Phase 14 can now begin

**Validation:**
- `python giraxpress_integration/export_solver.py` prints the manifest without error
- `results/kigali_distance_matrix_sample.json` exists and has the right shape (20×20)
- `get_solver()` returns a callable that solves a 5-node test instance correctly
- `giraxpress_integration/README.md` is clear enough that someone who hasn't read this repo can execute the GiraXpress Phase 14 integration

**→ After this phase passes, GiraXpress Phase 14 can begin.**

---

## Phase 11 — Full Benchmark Suite (notebook 06)

**Goal:** Run every algorithm against every instance size (N = 50, 100, 200) and produce the paper figures. This is the evidence base for the thesis solver choice justification.

**Scope:**

Complete `notebooks/06_benchmarks.ipynb`:
- **Cell 1:** Imports, load enriched graph
- **Cell 2:** Generate instances for N = 50, 100, 200. Each instance: random customer nodes, random demands, fixed depot, 5 vehicles, 20 kg capacity. Seed the random generator for reproducibility.
- **Cell 3:** For each (algorithm, N) combination, run the solver 5 times and record: total distance, solve time, number of routes. Algorithms: naive, Clarke-Wright, OR-Tools CVRP, OR-Tools CVRPTW.
- **Cell 4:** Distance comparison table — rows are algorithms, columns are N values. Show mean ± std. This is Table 1 in the paper.
- **Cell 5:** Solve time comparison — same structure as Cell 4. This is Table 2.
- **Cell 6:** Plot — grouped bar chart, distance by algorithm and N. Save to `results/benchmark_distance.png`.
- **Cell 7:** Plot — solve time vs N, line chart per algorithm. Save to `results/benchmark_time.png`.
- **Cell 8:** Edge cost model ablation — run OR-Tools CVRPTW with 4 configurations (distance-only, speed-by-class only, surface-penalty only, full composite) on N=100. Record total distance for each. This answers Research Question 3.
- **Cell 9:** Write everything to `results/cvrp_benchmark_full.csv`

**Validation:**
- OR-Tools CVRPTW produces shorter total distance than naive on all three instance sizes
- OR-Tools CVRPTW produces shorter or equal total distance vs Clarke-Wright on all three sizes
- `results/benchmark_distance.png` and `results/benchmark_time.png` exist and are legible
- Full composite model produces different (and shorter) routes than distance-only on N=100

---

## Phase 12 — RL Feedback Simulation (notebook 07)

**Goal:** Quantify how routing quality level directly affects LinUCB cumulative regret. Produce the coupling coefficient data for thesis Chapter 6.

**Scope:**

Implement `src/rl_bridge.py` fully:

`simulate_delivery_outcomes(solution: CVRPSolution, failure_rate: float, n_days: int = 30)`:
- For each delivery in the solution, randomly marks it as failed with probability `failure_rate`
- Returns a list of reward signal events: `[(product_id, reward, delivery_outcome), ...]`
- Uses the reward constants that match GiraXpress exactly

`compute_linucb_regret(reward_events, n_products=50, alpha=1.0, T=5000)`:
- Simulates a simplified LinUCB agent receiving the reward events
- Returns a `RegretResult` dataclass: `cumulative_regret` (array of length T), `final_regret`, `convergence_step`
- The LinUCB implementation here must mirror the one in GiraXpress `ml-service/app/bandits/linucb.py`

Complete `notebooks/07_rl_feedback_simulation.ipynb`:
- **Cell 1:** Imports
- **Cell 2:** Define three routing quality scenarios:
  - Naive routing → failure rate derived from Phase 11 naive baseline
  - Clarke-Wright → failure rate derived from Phase 11 Clarke-Wright results
  - OR-Tools CVRPTW → failure rate derived from Phase 11 CVRPTW results
  - Document how failure rates are estimated from distance and time window compliance data
- **Cell 3:** For each scenario, run `simulate_delivery_outcomes` over 30 simulated days
- **Cell 4:** For each scenario, run `compute_linucb_regret` with T=5000 interaction steps
- **Cell 5:** Plot regret curves — three lines on one chart (one per routing quality scenario). Save to `results/regret_curves.png`. This is Figure X in the thesis.
- **Cell 6:** Compute coupling coefficient — the slope of the regression line between failure rate and final LinUCB regret across the three scenarios
- **Cell 7:** Run λ ablation — for the OR-Tools CVRPTW scenario, vary λ (the delivery reward weight) from 0 to 1 in steps of 0.1. Plot final regret vs λ. Identify the optimal λ. Save to `results/lambda_ablation.png`.
- **Cell 8:** Write `results/rl_reward_impact.csv` with columns: `routing_algorithm`, `failure_rate`, `final_regret_T5000`, `convergence_step`, `optimal_lambda`

**Validation:**
- OR-Tools CVRPTW scenario produces lower cumulative regret than naive at T=5000
- Coupling coefficient is computable and non-zero
- `results/regret_curves.png` shows three visually distinct curves
- `results/rl_reward_impact.csv` exists with three rows (one per routing quality level)

---

## Phase 13 — Visualization Polish

**Goal:** All Folium maps and Matplotlib figures are publication-quality and reproducible.

**Scope:**

Review and polish all visualizations produced by previous phases:

Folium maps — for each of `results/sample_routes.html`, `results/cvrp_routes_n50.html`:
- Verify the map tiles load (uses OpenStreetMap tiles — no API key needed)
- Depot marker is visually distinct (star or house icon)
- Customer markers are numbered in stop order
- Each vehicle route is a distinct color with a legend
- Route lines follow actual road geometry (not straight lines) — use the `folium.PolyLine` with actual path node coordinates from the graph

Matplotlib figures — for each PNG in `results/`:
- 300 DPI minimum
- Axis labels with units
- Legend with algorithm names
- No plot titles (captions go in the paper, not the figure)
- Saved in both PNG (for the thesis Word/PDF) and PDF (for LaTeX)

Add to `src/viz.py`:
`export_all_figures(results_dir="results/")` — regenerates all PNG and PDF figures from their source CSVs. Running this function should be the only step needed to regenerate figures after a benchmark re-run.

**Validation:**
- All HTML maps open in Safari on M1 and show routes on actual Kigali streets
- All PNGs are ≥ 300 DPI
- `export_all_figures()` runs without error and produces the same files as the individual notebook cells

---

## Phase 14 — Dataset and Results Packaging

**Goal:** All results are organized, documented, and ready for Zenodo upload. The repo is in a state where a reader can reproduce every result from scratch.

**Scope:**

Write `results/README.md` — documents every file in `results/`:
- What it contains
- Which notebook produced it
- How to regenerate it

Write `data/README.md` — documents the two graphml files:
- How to regenerate `kigali_raw.graphml` (run notebook 01)
- How to regenerate `kigali_enriched.graphml` (run notebook 02)
- What OSM data coverage date was used
- Node and edge counts

Generate `results/instances/` — the CVRP benchmark instances as JSON files:
- `instance_n50_seed42.json`
- `instance_n100_seed42.json`
- `instance_n200_seed42.json`
- Each file contains: node IDs, coordinates, demands, vehicle capacity, depot node

Write the top-level `README.md` results section — fill in all the placeholder `—` values in the results tables using the actual numbers from `results/cvrp_benchmark_full.csv`.

**Validation:**
- A fresh clone of the repo with no data files can regenerate everything by running notebooks 01–07 in order
- All `—` placeholders in `README.md` results tables are filled with real numbers
- `results/instances/` contains three JSON files with valid structure

---

## Phase 15 — Paper Draft Preparation

**Goal:** All figures and tables referenced in the research paper are finalized and the paper LaTeX structure is set up.

**Scope:**

Set up `paper/` directory:
- `paper/main.tex` — LaTeX document structure with standard sections (Abstract, Introduction, Related Work, Problem Statement, Edge Cost Model, Algorithm Inventory, Results, Discussion, Conclusion, References)
- `paper/figures/` — symlinks or copies of all PNGs/PDFs from `results/`
- `paper/bibliography.bib` — BibTeX entries for all key citations: OR-Tools, OSMnx, LinUCB (Li et al. 2010), Clarke-Wright (1964), the GiraXpress repo itself

Write the paper abstract (see README draft — it needs X% filled in with real numbers from Phase 11).

Write sections that can be written now without waiting for review:
- Problem Statement section (from the mathematical formulation in the README)
- Edge Cost Model section (from `src/graph.py` constants and ablation results)
- Algorithm Inventory section (from the algorithm table in the README)

**Validation:**
- `pdflatex paper/main.tex` compiles without error (figures render, no missing references)
- Abstract contains no placeholder text — all X% values are real numbers from benchmark results
- `paper/bibliography.bib` has entries for all cited works