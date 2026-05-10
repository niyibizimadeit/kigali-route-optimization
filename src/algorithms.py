"""
algorithms.py — Custom algorithm implementations.

All shortest-path and TSP algorithms here are implemented from scratch.
OR-Tools wrappers live in solvers.py.
NetworkX is used only as a reference for correctness verification in notebooks.
"""

import heapq
import math
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Shortest path
# ---------------------------------------------------------------------------


def dijkstra(
    G,
    source: int,
    target: int,
    weight: str = "composite_weight",
) -> tuple[Optional[list[int]], float]:
    """
    Dijkstra's algorithm on a NetworkX MultiDiGraph.

    Args:
        G: NetworkX MultiDiGraph with the specified weight attribute on edges.
        source: Source node ID.
        target: Target node ID.
        weight: Edge attribute to use as cost.

    Returns:
        (path, cost) — path is a list of node IDs from source to target,
        cost is the total path cost.
        Returns (None, float('inf')) if no path exists.
    """
    if source == target:
        return [source], 0.0

    # dist[node] = best known cost from source to node
    dist = {source: 0.0}
    # prev[node] = predecessor on best path
    prev = {}
    # Min-heap: (cost, node)
    heap = [(0.0, source)]

    while heap:
        cost_u, u = heapq.heappop(heap)

        if u == target:
            # Reconstruct path
            path = []
            node = target
            while node in prev:
                path.append(node)
                node = prev[node]
            path.append(source)
            path.reverse()
            return path, cost_u

        # Skip if we already found a better path to u
        if cost_u > dist.get(u, math.inf):
            continue

        for u_, v, data in G.edges(u, data=True):
            # MultiDiGraph may have multiple edges; take minimum weight
            edge_weight = data.get(weight, math.inf)
            if not isinstance(edge_weight, (int, float)):
                edge_weight = math.inf

            new_cost = cost_u + edge_weight
            if new_cost < dist.get(v, math.inf):
                dist[v] = new_cost
                prev[v] = u
                heapq.heappush(heap, (new_cost, v))

    return None, math.inf


def astar(
    G,
    source: int,
    target: int,
    weight: str = "composite_weight",
) -> tuple[Optional[list[int]], float]:
    """
    A* search on a NetworkX MultiDiGraph with a haversine heuristic.

    The heuristic estimates minimum travel time using great-circle distance
    and the fastest road speed (primary = 50 km/h). It is admissible:
    it never overestimates the true composite_weight path cost.

    Args:
        G: NetworkX MultiDiGraph. Nodes must have 'y' (lat) and 'x' (lon).
        source: Source node ID.
        target: Target node ID.
        weight: Edge attribute to use as cost.

    Returns:
        (path, cost) — same signature as dijkstra().
    """
    if source == target:
        return [source], 0.0

    target_lat = float(G.nodes[target]["y"])
    target_lon = float(G.nodes[target]["x"])

    # g[node] = actual cost from source to node
    g = {source: 0.0}
    prev = {}
    # f = g + h
    h_source = _haversine_minutes(
        float(G.nodes[source]["y"]), float(G.nodes[source]["x"]),
        target_lat, target_lon,
    )
    heap = [(h_source, 0.0, source)]   # (f, g, node)

    while heap:
        f_u, g_u, u = heapq.heappop(heap)

        if u == target:
            path = []
            node = target
            while node in prev:
                path.append(node)
                node = prev[node]
            path.append(source)
            path.reverse()
            return path, g_u

        if g_u > g.get(u, math.inf):
            continue

        for u_, v, data in G.edges(u, data=True):
            edge_weight = data.get(weight, math.inf)
            if not isinstance(edge_weight, (int, float)):
                edge_weight = math.inf

            new_g = g_u + edge_weight
            if new_g < g.get(v, math.inf):
                g[v] = new_g
                prev[v] = u
                h_v = _haversine_minutes(
                    float(G.nodes[v]["y"]), float(G.nodes[v]["x"]),
                    target_lat, target_lon,
                )
                heapq.heappush(heap, (new_g + h_v, new_g, v))

    return None, math.inf


def _haversine_minutes(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance converted to minimum travel minutes.

    Assumes fastest road speed (primary = 50 km/h) so the heuristic
    is admissible — never overestimates true composite_weight cost.

    Args:
        lat1, lon1: Coordinates of point 1 in decimal degrees.
        lat2, lon2: Coordinates of point 2 in decimal degrees.

    Returns:
        Estimated minimum travel time in minutes.
    """
    R = 6371.0  # Earth radius km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    dist_km = 2 * R * math.asin(math.sqrt(a))
    fastest_speed_kmh = 50.0   # primary road
    return (dist_km / fastest_speed_kmh) * 60.0


# ---------------------------------------------------------------------------
# TSP
# ---------------------------------------------------------------------------


def held_karp(dist_matrix: np.ndarray) -> tuple[list[int], float]:
    """
    Held-Karp exact TSP solver using dynamic programming.

    Practical upper limit: N ≤ 20 (O(2^n * n^2) time and space).
    Always starts and ends at index 0.

    Args:
        dist_matrix: Square numpy array of pairwise distances. Shape (N, N).

    Returns:
        (tour, cost) — tour is a list of node indices starting and ending
        at 0, cost is total tour distance.
    """
    n = len(dist_matrix)
    if n == 1:
        return [0], 0.0
    if n == 2:
        return [0, 1, 0], dist_matrix[0][1] + dist_matrix[1][0]

    # dp[S][i] = min cost to reach node i having visited exactly the nodes in S
    # S is a bitmask; node 0 is always the start
    INF = float("inf")
    full = (1 << n) - 1

    dp = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]

    dp[1][0] = 0.0  # start at node 0, visited = {0}

    for S in range(1, 1 << n):
        if not (S & 1):   # must include node 0
            continue
        for u in range(n):
            if not (S & (1 << u)):
                continue
            if dp[S][u] == INF:
                continue
            for v in range(n):
                if S & (1 << v):
                    continue
                new_S = S | (1 << v)
                new_cost = dp[S][u] + dist_matrix[u][v]
                if new_cost < dp[new_S][v]:
                    dp[new_S][v] = new_cost
                    parent[new_S][v] = u

    # Find best last node before returning to 0
    best_cost = INF
    last = -1
    for u in range(1, n):
        cost = dp[full][u] + dist_matrix[u][0]
        if cost < best_cost:
            best_cost = cost
            last = u

    # Reconstruct tour
    tour = []
    S = full
    u = last
    while u != -1:
        tour.append(u)
        prev_u = parent[S][u]
        S = S ^ (1 << u)
        u = prev_u
    tour.reverse()
    tour.append(0)  # return to depot

    return tour, best_cost


def two_opt(
    tour: list[int],
    dist_matrix: np.ndarray,
    max_iterations: int = 1000,
) -> tuple[list[int], float]:
    """
    2-opt local search to improve a TSP tour.

    Iteratively reverses segments between two edges if the swap reduces
    total tour cost. Stops when no improving swap is found or
    max_iterations is reached.

    Args:
        tour: Initial tour as a list of node indices (not repeated start/end).
        dist_matrix: Square numpy array of pairwise distances.
        max_iterations: Maximum number of improvement passes.

    Returns:
        (improved_tour, improved_cost). Never returns a worse tour.
    """
    def tour_cost(t):
        return sum(dist_matrix[t[i]][t[(i + 1) % len(t)]] for i in range(len(t)))

    best = list(tour)
    best_cost = tour_cost(best)
    n = len(best)

    for _ in range(max_iterations):
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # Cost of current edges: i-1→i and j→j+1
                a, b = best[i - 1], best[i]
                c, d = best[j], best[(j + 1) % n]
                current = dist_matrix[a][b] + dist_matrix[c][d]
                # Cost if we swap: i-1→j and i→j+1
                swapped = dist_matrix[a][c] + dist_matrix[b][d]
                if swapped < current - 1e-10:
                    best[i:j + 1] = best[i:j + 1][::-1]
                    best_cost = best_cost - current + swapped
                    improved = True
        if not improved:
            break

    return best, tour_cost(best)


# ---------------------------------------------------------------------------
# CVRP heuristic
# ---------------------------------------------------------------------------


def clarke_wright(
    dist_matrix: np.ndarray,
    demands: list[float],
    vehicle_capacity: float,
    depot_idx: int = 0,
) -> "CVRPSolution":
    """
    Clarke-Wright savings algorithm for the Capacitated VRP.

    Starts with one vehicle per customer (star routes from depot), then
    iteratively merges routes that produce the highest savings while
    respecting vehicle capacity.

    Args:
        dist_matrix: Square numpy array. Index 0 is the depot.
        demands: Demand per node. demands[0] (depot) should be 0.
        vehicle_capacity: Maximum load per vehicle.
        depot_idx: Index of the depot. Default 0.

    Returns:
        CVRPSolution.
    """
    from src.solvers import CVRPSolution
    import time

    t0 = time.time()
    n = len(dist_matrix)
    customers = [i for i in range(n) if i != depot_idx]

    # Initial routes: one vehicle per customer
    routes = [[c] for c in customers]
    route_demand = [demands[c] for c in customers]

    # Compute savings: s(i,j) = d(depot,i) + d(depot,j) - d(i,j)
    savings = []
    for i in customers:
        for j in customers:
            if i >= j:
                continue
            s = (dist_matrix[depot_idx][i]
                 + dist_matrix[depot_idx][j]
                 - dist_matrix[i][j])
            savings.append((s, i, j))
    savings.sort(reverse=True)

    # Merge routes greedily
    def find_route(node):
        for idx, r in enumerate(routes):
            if node in r:
                return idx
        return -1

    for s, i, j in savings:
        ri = find_route(i)
        rj = find_route(j)
        if ri == -1 or rj == -1 or ri == rj:
            continue
        # i must be at the end of its route, j at the start (or vice versa)
        route_i = routes[ri]
        route_j = routes[rj]
        can_merge = False
        merged = None

        if route_i[-1] == i and route_j[0] == j:
            merged = route_i + route_j
            can_merge = True
        elif route_j[-1] == i and route_i[0] == j:
            merged = route_j + route_i
            can_merge = True
        elif route_i[0] == i and route_j[-1] == j:
            merged = route_j + route_i
            can_merge = True
        elif route_i[-1] == j and route_j[0] == i:
            merged = route_j + route_i
            can_merge = True

        if not can_merge:
            continue

        new_demand = route_demand[ri] + route_demand[rj]
        if new_demand > vehicle_capacity:
            continue

        # Perform merge — remove rj, update ri
        routes[ri] = merged
        route_demand[ri] = new_demand
        routes.pop(rj)
        route_demand.pop(rj)

    # Compute total distance
    total = 0.0
    for route in routes:
        total += dist_matrix[depot_idx][route[0]]
        for k in range(len(route) - 1):
            total += dist_matrix[route[k]][route[k + 1]]
        total += dist_matrix[route[-1]][depot_idx]

    return CVRPSolution(
        routes=routes,
        total_distance_km=total,
        num_routes=len(routes),
        solve_time_s=time.time() - t0,
        algorithm="clarke-wright",
    )