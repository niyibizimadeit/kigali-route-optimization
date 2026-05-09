"""
solvers.py — OR-Tools wrappers for TSP, CVRP, and CVRPTW.

This module owns the CVRPSolution dataclass and all OR-Tools solver calls.
Custom algorithm implementations (Dijkstra, Clarke-Wright, etc.) live in
algorithms.py.

The solve_cvrptw() function is the production solver exported to GiraXpress.
Its return type and parameter signature must never change without also updating
giraxpress_integration/export_solver.py.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class CVRPSolution:
    """
    Unified return type for all CVRP/CVRPTW solvers.

    routes: Each route is a list of node indices from dist_matrix.
            Index 0 is always the depot. Routes do NOT repeat the depot
            at start/end — that is implicit.
    total_distance_km: Sum of edge costs across all routes (in the unit
                       of the distance matrix — composite_weight is minutes,
                       but we label this km for VRP convention; be consistent).
    num_routes: Number of vehicles used.
    solve_time_s: Wall-clock solver time in seconds.
    algorithm: Name of the algorithm that produced this solution.
    time_window_violations: Number of soft time window violations (CVRPTW only).
    estimated_arrival_times: Maps node index → estimated arrival time in minutes
                             from depot departure (CVRPTW only).
    """
    routes: list[list[int]]
    total_distance_km: float
    num_routes: int
    solve_time_s: float
    algorithm: str
    time_window_violations: int = 0
    estimated_arrival_times: dict[int, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------


def naive_assignment(
    customer_indices: list[int],
    num_vehicles: int,
) -> CVRPSolution:
    """
    Round-robin assignment of customers to vehicles with no routing optimization.

    This is the baseline that all optimized solvers are compared against.
    Used in GiraXpress Phase 14 benchmarking.

    Args:
        customer_indices: List of customer node indices (not including depot).
        num_vehicles: Number of vehicles to assign across.

    Returns:
        CVRPSolution with routes distributed round-robin. total_distance_km
        is set to float('inf') — caller must compute actual distance using
        the distance matrix if needed.
    """
    pass


# ---------------------------------------------------------------------------
# TSP
# ---------------------------------------------------------------------------


def solve_tsp_ortools(
    dist_matrix: np.ndarray,
    time_limit_s: int = 30,
) -> tuple[list[int], float]:
    """
    OR-Tools TSP solver with guided local search metaheuristic.

    Args:
        dist_matrix: Square numpy array of pairwise distances. Shape (N, N).
        time_limit_s: Maximum solver wall time.

    Returns:
        (tour, cost) where tour is a list of node indices and cost is total
        tour distance.

    Raises:
        ValueError: If dist_matrix is empty or not square.
    """
    pass


# ---------------------------------------------------------------------------
# CVRP
# ---------------------------------------------------------------------------


def solve_cvrp(
    graph,
    depot_node: int,
    customer_nodes: list[int],
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    time_limit_s: int = 30,
) -> CVRPSolution:
    """
    OR-Tools CVRP solver with capacity constraints.

    Builds the distance matrix from the graph internally using
    src.graph.build_distance_matrix(). All routing decisions are made
    on composite_weight edges.

    Args:
        graph: Enriched NetworkX graph (from load_enriched_graph).
        depot_node: OSM node ID of the depot.
        customer_nodes: List of OSM node IDs for customer delivery locations.
        demands: Demand per customer (kg). Same order as customer_nodes.
        vehicle_capacity: Maximum load per vehicle in kg.
        num_vehicles: Number of available vehicles.
        time_limit_s: Maximum solver wall time.

    Returns:
        CVRPSolution.

    Raises:
        ValueError: If customer_nodes is empty, capacity <= 0, or num_vehicles <= 0.
    """
    pass


# ---------------------------------------------------------------------------
# CVRPTW (production solver — exported to GiraXpress)
# ---------------------------------------------------------------------------


def solve_cvrptw(
    graph,
    depot_node: int,
    customer_nodes: list[int],
    demands: list[float],
    vehicle_capacity: float,
    num_vehicles: int,
    time_windows: list[tuple[float, float]],
    time_limit_s: int = 30,
) -> CVRPSolution:
    """
    OR-Tools CVRPTW solver with soft time windows.

    This is the production solver. Its output is consumed directly by
    GiraXpress ml-service/app/routing/vrp_solver.py.

    Time windows are soft: violations are penalized in the objective but do
    not make the problem infeasible. This is correct for Kigali delivery
    windows, which are approximate.

    Args:
        graph: Enriched NetworkX graph (from load_enriched_graph).
        depot_node: OSM node ID of the depot.
        customer_nodes: List of OSM node IDs for customer delivery locations.
        demands: Demand per customer (kg). Same order as customer_nodes.
        vehicle_capacity: Maximum load per vehicle in kg.
        num_vehicles: Number of available vehicles.
        time_windows: List of (earliest_min, latest_min) tuples, one per
                      customer node. Times are in minutes from depot departure.
        time_limit_s: Maximum solver wall time.

    Returns:
        CVRPSolution with time_window_violations and estimated_arrival_times
        populated.

    Raises:
        ValueError: If customer_nodes is empty, capacity <= 0, num_vehicles <= 0,
                    or len(time_windows) != len(customer_nodes).
    """
    pass


# ---------------------------------------------------------------------------
# Rolling horizon
# ---------------------------------------------------------------------------


def solve_rolling_horizon(
    graph,
    depot_node: int,
    initial_orders: list[dict],
    new_order_stream: list[tuple[float, int, float]],
    vehicle_capacity: float,
    num_vehicles: int,
    re_solve_interval_min: float = 60,
) -> list[CVRPSolution]:
    """
    Rolling-horizon re-solver for stochastic same-day order arrivals.

    Re-solves the routing problem every re_solve_interval_min minutes,
    incorporating any new orders that arrived since the last solve.

    Args:
        graph: Enriched NetworkX graph.
        depot_node: OSM node ID of the depot.
        initial_orders: List of dicts with keys 'node' (OSM ID) and 'demand' (kg).
        new_order_stream: List of (arrival_time_min, osm_node_id, demand_kg) tuples.
                          Sorted by arrival_time_min ascending.
        vehicle_capacity: Maximum load per vehicle in kg.
        num_vehicles: Number of available vehicles.
        re_solve_interval_min: How often to re-solve (minutes).

    Returns:
        List of CVRPSolution objects, one per solve interval.
    """
    pass
