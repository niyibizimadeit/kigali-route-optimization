"""
export_solver.py — Packages the validated CVRPTW solver for GiraXpress.

Exposes two callables that GiraXpress consumes:
    get_solver()                  → configured solve_cvrptw with Kigali graph bound
    get_distance_matrix_builder() → build_distance_matrix with enriched graph bound

Run directly to print the validation manifest:
    python giraxpress_integration/export_solver.py

The manifest output must be saved and used to verify the GiraXpress integration.
See giraxpress_integration/README.md for verification steps.

IMPORTANT: Edge cost constants are imported from src/graph.py — never hardcoded here.
"""

import sys
import os
import json
import time
import random
from functools import partial
from typing import Callable

# Resolve repo root from this file's location and make it the working directory
# so all relative paths (data/, results/) resolve correctly regardless of
# where the script is invoked from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, REPO_ROOT)

import numpy as np


def get_solver() -> Callable:
    """
    Return a configured solve_cvrptw callable with the Kigali graph pre-loaded.

    The returned callable has the same signature as src.solvers.solve_cvrptw
    but with `graph` already bound. GiraXpress calls it as:

        solver = get_solver()
        solution = solver(
            depot_node=...,
            customer_nodes=[...],
            demands=[...],
            vehicle_capacity=20,
            num_vehicles=5,
            time_windows=[...],
        )

    Returns:
        Callable that accepts all solve_cvrptw args except `graph`.

    Raises:
        FileNotFoundError: If kigali_enriched.graphml does not exist.
    """
    from src.graph import load_enriched_graph
    from src.solvers import solve_cvrptw

    _data_path = os.path.join(REPO_ROOT, 'data', 'kigali_enriched.graphml')
    G = load_enriched_graph(path=_data_path)
    # Cast composite_weight to float after graphml reload
    for u, v, k, d in G.edges(keys=True, data=True):
        if "composite_weight" in d:
            G[u][v][k]["composite_weight"] = float(d["composite_weight"])

    def bound_solver(
        depot_node,
        customer_nodes,
        demands,
        vehicle_capacity,
        num_vehicles,
        time_windows,
        time_limit_s=30,
        dist_matrix=None,
    ):
        return solve_cvrptw(
            graph=G,
            depot_node=depot_node,
            customer_nodes=customer_nodes,
            demands=demands,
            vehicle_capacity=vehicle_capacity,
            num_vehicles=num_vehicles,
            time_windows=time_windows,
            time_limit_s=time_limit_s,
            dist_matrix=dist_matrix,
        )

    return bound_solver


def get_distance_matrix_builder() -> Callable:
    """
    Return a configured build_distance_matrix callable with the Kigali graph pre-loaded.

    GiraXpress calls it as:
        builder = get_distance_matrix_builder()
        matrix = builder(node_ids=[...])

    Returns:
        Callable that accepts node_ids and returns an N×N numpy array.
    """
    from src.graph import load_enriched_graph, build_distance_matrix

    _data_path = os.path.join(REPO_ROOT, 'data', 'kigali_enriched.graphml')
    G = load_enriched_graph(path=_data_path)
    for u, v, k, d in G.edges(keys=True, data=True):
        if "composite_weight" in d:
            G[u][v][k]["composite_weight"] = float(d["composite_weight"])

    def bound_builder(node_ids, weight="composite_weight"):
        return build_distance_matrix(G, node_ids, weight=weight)

    return bound_builder


def _run_test_instance() -> dict:
    """
    Run a fixed 10-node test instance and return results as a dict.

    Uses 10 nodes near central Kigali (Gikondo/CBD area).
    This is the canonical verification instance for GiraXpress integration check.
    """
    from src.graph import load_enriched_graph, build_distance_matrix
    from src.solvers import solve_cvrptw
    from src.graph import (
        SPEED_BY_HIGHWAY, QUALITY_PENALTY_UNPAVED, QUALITY_PENALTY_PAVED
    )
    import networkx as nx

    _data_path = os.path.join(REPO_ROOT, 'data', 'kigali_enriched.graphml')
    G = load_enriched_graph(path=_data_path)
    for u, v, k, d in G.edges(keys=True, data=True):
        if "composite_weight" in d:
            G[u][v][k]["composite_weight"] = float(d["composite_weight"])

    # Reproducible 10-node sample from the largest SCC
    scc = max(nx.strongly_connected_components(G), key=len)
    scc_nodes = sorted(scc)   # sorted for reproducibility
    random.seed(0)
    sample = random.sample(scc_nodes, 11)   # depot + 10 customers
    depot_node = sample[0]
    customer_nodes = sample[1:]

    demands = [2.0] * 10
    time_windows = [(10, 120)] * 10   # 10–120 min from departure

    mat = build_distance_matrix(G, [depot_node] + customer_nodes)
    max_finite = mat[mat != np.inf].max()
    mat_clean = np.where(mat == np.inf, max_finite * 10, mat)

    t0 = time.time()
    sol = solve_cvrptw(
        graph=G,
        depot_node=depot_node,
        customer_nodes=customer_nodes,
        demands=demands,
        vehicle_capacity=20.0,
        num_vehicles=3,
        time_windows=time_windows,
        time_limit_s=30,
        dist_matrix=mat_clean,
    )
    solve_time = time.time() - t0

    return {
        "algorithm":              "OR-Tools CVRPTW",
        "n_stops":                len(customer_nodes),
        "total_distance_km":      round(sol.total_distance_km, 4),
        "solve_time_s":           round(solve_time, 3),
        "time_window_violations": sol.time_window_violations,
        "graph_nodes":            len(G.nodes),
        "graph_edges":            len(G.edges),
        "edge_cost_model":        "composite (speed-by-class + surface penalty)",
        "QUALITY_PENALTY_UNPAVED": QUALITY_PENALTY_UNPAVED,
        "SPEED_BY_HIGHWAY_primary": SPEED_BY_HIGHWAY["primary"],
    }


def print_manifest() -> None:
    """Print the validation manifest to stdout."""
    print("Running 10-node test instance...")
    result = _run_test_instance()

    print("\n" + "=" * 52)
    print("  kigali-route-optimization solver manifest")
    print("=" * 52)
    for key, val in result.items():
        print(f"  {key:<30}: {val}")
    print("=" * 52)
    print("\nSave this output. Use it to verify the GiraXpress")
    print("integration — see giraxpress_integration/README.md.")


def produce_distance_matrix_sample() -> None:
    """
    Write a 20-node sample distance matrix to results/ as JSON.
    Used by GiraXpress integration verification.
    """
    from src.graph import load_enriched_graph, build_distance_matrix
    import networkx as nx

    _data_path = os.path.join(REPO_ROOT, 'data', 'kigali_enriched.graphml')
    G = load_enriched_graph(path=_data_path)
    for u, v, k, d in G.edges(keys=True, data=True):
        if "composite_weight" in d:
            G[u][v][k]["composite_weight"] = float(d["composite_weight"])

    scc = max(nx.strongly_connected_components(G), key=len)
    scc_nodes = sorted(scc)
    random.seed(1)
    sample_nodes = random.sample(scc_nodes, 20)

    mat = build_distance_matrix(G, sample_nodes)
    mat_serializable = [
        [None if v == float("inf") else round(v, 6) for v in row]
        for row in mat.tolist()
    ]

    output = {
        "node_ids":    sample_nodes,
        "matrix":      mat_serializable,
        "weight":      "composite_weight",
        "description": "20×20 sample distance matrix (minutes) for GiraXpress integration verification",
    }

    os.makedirs(os.path.join(REPO_ROOT, "results"), exist_ok=True)
    out_path = os.path.join(REPO_ROOT, "results", "kigali_distance_matrix_sample.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Distance matrix sample saved to {out_path}")


if __name__ == "__main__":
    print_manifest()
    produce_distance_matrix_sample()