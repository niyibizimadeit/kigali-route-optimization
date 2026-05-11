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
    total_distance_km: Sum of edge costs across all routes.
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

    Args:
        customer_indices: List of customer node indices (not including depot).
        num_vehicles: Number of vehicles to assign across.

    Returns:
        CVRPSolution with routes distributed round-robin.
        total_distance_km is float('inf') — caller computes actual distance
        from the distance matrix if needed.
    """
    t0 = time.time()
    routes = [[] for _ in range(num_vehicles)]
    for i, customer in enumerate(customer_indices):
        routes[i % num_vehicles].append(customer)
    routes = [r for r in routes if r]   # drop empty routes

    return CVRPSolution(
        routes=routes,
        total_distance_km=float("inf"),
        num_routes=len(routes),
        solve_time_s=time.time() - t0,
        algorithm="naive-round-robin",
    )


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
        (tour, cost) — tour is a list of node indices starting and ending
        at 0, cost is total tour distance.

    Raises:
        ValueError: If dist_matrix is empty or not square.
    """
    from ortools.constraint_solver import pywrapcp as cp
    from ortools.constraint_solver import routing_enums_pb2 as enums

    n = len(dist_matrix)
    if n == 0:
        raise ValueError("dist_matrix is empty")
    if dist_matrix.shape[0] != dist_matrix.shape[1]:
        raise ValueError("dist_matrix must be square")
    if n == 1:
        return [0], 0.0

    # OR-Tools works with integers — scale floats by a large factor
    SCALE = 1000
    int_matrix = (dist_matrix * SCALE).astype(int)

    # Create routing index manager and model
    manager = cp.RoutingIndexManager(n, 1, 0)   # n locations, 1 vehicle, depot=0
    routing = cp.RoutingModel(manager)

    def distance_callback(from_idx, to_idx):
        from_node = manager.IndexToNode(from_idx)
        to_node   = manager.IndexToNode(to_idx)
        return int(int_matrix[from_node][to_node])

    transit_cb_idx = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb_idx)

    # Search parameters
    search_params = cp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = enums.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = enums.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = time_limit_s
    search_params.log_search = False

    solution = routing.SolveWithParameters(search_params)

    if not solution:
        # Fall back to nearest-neighbour tour
        tour = _nearest_neighbour_tour(dist_matrix)
        cost = sum(dist_matrix[tour[i]][tour[i+1]] for i in range(len(tour)-1))
        return tour, float(cost)

    # Extract tour
    tour = []
    idx = routing.Start(0)
    while not routing.IsEnd(idx):
        tour.append(manager.IndexToNode(idx))
        idx = solution.Value(routing.NextVar(idx))
    tour.append(0)   # return to depot

    cost = sum(dist_matrix[tour[i]][tour[i+1]] for i in range(len(tour)-1))
    return tour, float(cost)


def _nearest_neighbour_tour(dist_matrix: np.ndarray) -> list[int]:
    """Greedy nearest-neighbour construction — fallback if OR-Tools finds no solution."""
    n = len(dist_matrix)
    visited = [False] * n
    tour = [0]
    visited[0] = True
    for _ in range(n - 1):
        last = tour[-1]
        best = min(
            (j for j in range(n) if not visited[j]),
            key=lambda j: dist_matrix[last][j]
        )
        tour.append(best)
        visited[best] = True
    tour.append(0)
    return tour


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
        ValueError: If inputs are invalid.
    """
    if not customer_nodes:
        raise ValueError("customer_nodes cannot be empty")
    if vehicle_capacity <= 0:
        raise ValueError("vehicle_capacity must be positive")
    if num_vehicles <= 0:
        raise ValueError("num_vehicles must be positive")

    from ortools.constraint_solver import pywrapcp as cp
    from ortools.constraint_solver import routing_enums_pb2 as enums
    from src.graph import build_distance_matrix

    t0 = time.time()

    all_nodes = [depot_node] + customer_nodes
    matrix = build_distance_matrix(graph, all_nodes, weight="composite_weight")
    # Replace inf with a large finite penalty so OR-Tools can handle it
    max_finite = matrix[matrix != np.inf].max() * 10 if (matrix != np.inf).any() else 1e6
    matrix = np.where(matrix == np.inf, max_finite, matrix)

    SCALE = 1000
    int_matrix = (matrix * SCALE).astype(int)
    int_demands = [0] + [int(d * SCALE) for d in demands]
    int_capacity = int(vehicle_capacity * SCALE)

    n = len(all_nodes)
    manager = cp.RoutingIndexManager(n, num_vehicles, 0)
    routing = cp.RoutingModel(manager)

    def distance_callback(from_idx, to_idx):
        return int(int_matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)])

    transit_cb = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_idx):
        return int_demands[manager.IndexToNode(from_idx)]

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb, 0, [int_capacity] * num_vehicles, True, "Capacity"
    )

    search_params = cp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = enums.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = enums.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = time_limit_s
    search_params.log_search = False

    solution = routing.SolveWithParameters(search_params)

    routes = []
    total_dist = 0.0

    if solution:
        for v in range(num_vehicles):
            route = []
            idx = routing.Start(v)
            while not routing.IsEnd(idx):
                node = manager.IndexToNode(idx)
                if node != 0:
                    route.append(node)
                idx = solution.Value(routing.NextVar(idx))
            if route:
                routes.append(route)
        # Compute actual distance
        for route in routes:
            total_dist += matrix[0][route[0]]
            for i in range(len(route) - 1):
                total_dist += matrix[route[i]][route[i+1]]
            total_dist += matrix[route[-1]][0]
    else:
        # Fallback: naive assignment
        fallback = naive_assignment(list(range(1, n)), num_vehicles)
        routes = fallback.routes

    return CVRPSolution(
        routes=routes,
        total_distance_km=total_dist,
        num_routes=len(routes),
        solve_time_s=time.time() - t0,
        algorithm="ortools-cvrp",
    )


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

    This is the production solver exported to GiraXpress Phase 14.

    Time windows are soft: violations are penalized in the objective but do
    not make the problem infeasible. Correct for Kigali delivery windows,
    which are approximate.

    Args:
        graph: Enriched NetworkX graph.
        depot_node: OSM node ID of the depot.
        customer_nodes: List of OSM node IDs.
        demands: Demand per customer (kg).
        vehicle_capacity: Maximum load per vehicle in kg.
        num_vehicles: Number of available vehicles.
        time_windows: List of (earliest_min, latest_min) per customer.
        time_limit_s: Maximum solver wall time.

    Returns:
        CVRPSolution with time_window_violations and estimated_arrival_times.

    Raises:
        ValueError: If inputs are invalid.
    """
    if not customer_nodes:
        raise ValueError("customer_nodes cannot be empty")
    if vehicle_capacity <= 0:
        raise ValueError("vehicle_capacity must be positive")
    if num_vehicles <= 0:
        raise ValueError("num_vehicles must be positive")
    if len(time_windows) != len(customer_nodes):
        raise ValueError("time_windows must have same length as customer_nodes")

    from ortools.constraint_solver import pywrapcp as cp
    from ortools.constraint_solver import routing_enums_pb2 as enums
    from src.graph import build_distance_matrix

    t0 = time.time()

    all_nodes = [depot_node] + customer_nodes
    matrix = build_distance_matrix(graph, all_nodes, weight="composite_weight")
    max_finite = matrix[matrix != np.inf].max() * 10 if (matrix != np.inf).any() else 1e6
    matrix = np.where(matrix == np.inf, max_finite, matrix)

    SCALE = 100   # finer scale for time windows (minutes)
    int_matrix   = (matrix * SCALE).astype(int)
    int_demands  = [0] + [int(d * SCALE) for d in demands]
    int_capacity = int(vehicle_capacity * SCALE)

    # Time windows: index 0 = depot (open all day), 1..n = customers
    depot_tw = (0, int(24 * 60 * SCALE))
    int_windows = [depot_tw] + [
        (int(tw[0] * SCALE), int(tw[1] * SCALE)) for tw in time_windows
    ]

    n = len(all_nodes)
    manager = cp.RoutingIndexManager(n, num_vehicles, 0)
    routing = cp.RoutingModel(manager)

    def distance_callback(from_idx, to_idx):
        return int(int_matrix[manager.IndexToNode(from_idx)][manager.IndexToNode(to_idx)])

    transit_cb = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_cb)

    def demand_callback(from_idx):
        return int_demands[manager.IndexToNode(from_idx)]

    demand_cb = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_cb, 0, [int_capacity] * num_vehicles, True, "Capacity"
    )

    # Time dimension for soft windows
    routing.AddDimension(transit_cb, int(60 * SCALE), int(24 * 60 * SCALE), True, "Time")
    time_dim = routing.GetDimensionOrDie("Time")

    tw_violation_count = 0
    PENALTY = int(max_finite * SCALE * 10)

    for i in range(1, n):   # skip depot
        idx = manager.NodeToIndex(i)
        early, late = int_windows[i]
        time_dim.SetCumulVarSoftLowerBound(idx, early, PENALTY)
        time_dim.SetCumulVarSoftUpperBound(idx, late,  PENALTY)

    search_params = cp.DefaultRoutingSearchParameters()
    search_params.first_solution_strategy = enums.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_params.local_search_metaheuristic = enums.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_params.time_limit.seconds = time_limit_s
    search_params.log_search = False

    solution = routing.SolveWithParameters(search_params)

    routes = []
    total_dist = 0.0
    arrival_times: dict[int, float] = {}

    if solution:
        for v in range(num_vehicles):
            route = []
            idx = routing.Start(v)
            while not routing.IsEnd(idx):
                node = manager.IndexToNode(idx)
                if node != 0:
                    route.append(node)
                    arr = solution.Min(time_dim.CumulVar(idx)) / SCALE
                    arrival_times[node] = arr
                    early, late = int_windows[node]
                    if arr * SCALE < early or arr * SCALE > late:
                        tw_violation_count += 1
                idx = solution.Value(routing.NextVar(idx))
            if route:
                routes.append(route)

        for route in routes:
            total_dist += matrix[0][route[0]]
            for i in range(len(route) - 1):
                total_dist += matrix[route[i]][route[i+1]]
            total_dist += matrix[route[-1]][0]
    else:
        fallback = naive_assignment(list(range(1, n)), num_vehicles)
        routes = fallback.routes

    return CVRPSolution(
        routes=routes,
        total_distance_km=total_dist,
        num_routes=len(routes),
        solve_time_s=time.time() - t0,
        algorithm="ortools-cvrptw",
        time_window_violations=tw_violation_count,
        estimated_arrival_times=arrival_times,
    )


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

    Re-solves every re_solve_interval_min minutes incorporating new orders.

    Args:
        graph: Enriched NetworkX graph.
        depot_node: OSM node ID of the depot.
        initial_orders: List of dicts with keys 'node' (OSM ID) and 'demand' (kg).
        new_order_stream: List of (arrival_time_min, osm_node_id, demand_kg).
                          Must be sorted by arrival_time_min ascending.
        vehicle_capacity: Maximum load per vehicle in kg.
        num_vehicles: Number of available vehicles.
        re_solve_interval_min: How often to re-solve (minutes).

    Returns:
        List of CVRPSolution objects, one per solve interval.
    """
    solutions = []
    current_orders = list(initial_orders)
    stream_idx = 0
    current_time = 0.0
    max_time = max(
        (t for t, _, _ in new_order_stream), default=0
    ) + re_solve_interval_min

    while current_time <= max_time:
        # Absorb any new orders that arrived by current_time
        while stream_idx < len(new_order_stream):
            arr_time, node, demand = new_order_stream[stream_idx]
            if arr_time <= current_time:
                current_orders.append({"node": node, "demand": demand})
                stream_idx += 1
            else:
                break

        if current_orders:
            customer_nodes = [o["node"] for o in current_orders]
            demands = [o["demand"] for o in current_orders]
            # Default time windows: 8am–8pm for all customers
            time_windows = [(8 * 60, 20 * 60)] * len(customer_nodes)

            sol = solve_cvrptw(
                graph=graph,
                depot_node=depot_node,
                customer_nodes=customer_nodes,
                demands=demands,
                vehicle_capacity=vehicle_capacity,
                num_vehicles=num_vehicles,
                time_windows=time_windows,
                time_limit_s=10,   # tighter limit for rolling re-solves
            )
            solutions.append(sol)

        current_time += re_solve_interval_min

    return solutions