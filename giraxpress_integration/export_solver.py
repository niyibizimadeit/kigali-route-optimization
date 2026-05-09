"""
export_solver.py — Packages the validated CVRPTW solver for GiraXpress.

This script is the handoff point between kigali-route-optimization and
GiraXpress Phase 14. It exposes two callables that GiraXpress consumes:

    get_solver()               → configured solve_cvrptw with Kigali graph bound
    get_distance_matrix_builder() → build_distance_matrix with enriched graph bound

Run directly to print the validation manifest:
    python giraxpress_integration/export_solver.py

The manifest output must be saved and used to verify the GiraXpress integration.
See giraxpress_integration/README.md for verification steps.

IMPORTANT: The edge cost constants in this file must match src/graph.py exactly.
Do not hardcode values here — import from src.graph.
"""

import sys
import time
from typing import Callable

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
                           Run notebook 02 first.
    """
    pass


def get_distance_matrix_builder() -> Callable:
    """
    Return a configured build_distance_matrix callable with the Kigali graph pre-loaded.

    GiraXpress calls it as:
        builder = get_distance_matrix_builder()
        matrix = builder(node_ids=[...])

    Returns:
        Callable that accepts node_ids and returns an N×N numpy array.
    """
    pass


def _run_test_instance() -> dict:
    """
    Run a fixed 10-node test instance and return results as a dict.

    The test instance uses hardcoded Kigali node IDs near Gikondo.
    This is the canonical verification instance — the same one used in
    the GiraXpress integration check.

    Returns:
        Dict with keys: algorithm, n_stops, total_distance_km, solve_time_s,
        time_window_violations, graph_nodes, graph_edges, edge_cost_params.
    """
    pass


def print_manifest() -> None:
    """
    Print the validation manifest to stdout.

    Output format:
        === kigali-route-optimization solver manifest ===
        algorithm:              OR-Tools CVRPTW
        graph_nodes:            XXXXX
        graph_edges:            XXXXX
        edge_cost_model:        composite (speed-by-class + surface penalty)
        QUALITY_PENALTY_UNPAVED: 1.4
        test_instance_stops:    10
        test_instance_dist_km:  X.XXX
        test_instance_time_s:   X.XXX
        ================================================
    """
    pass


if __name__ == "__main__":
    print_manifest()
