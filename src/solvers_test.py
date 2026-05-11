"""
solvers_test.py — Phase 9 hardening validation.

Tests all solvers on a small synthetic instance where the correct answer
is known. Run from the repo root:
    python src/solvers_test.py

Must print 'all checks passed' without error.
"""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check(name: str, condition: bool) -> None:
    if not condition:
        print(f"FAILED: {name}")
        sys.exit(1)
    print(f"  ok: {name}")


def make_toy_graph():
    """
    5-node directed graph: depot (0) + 4 customers (1-4).
    All edges present with known composite_weight values.

    Layout (distances in minutes):
        depot(0) ↔ 1 : 2.0
        depot(0) ↔ 2 : 3.0
        depot(0) ↔ 3 : 4.0
        depot(0) ↔ 4 : 5.0
        1 ↔ 2 : 1.5
        1 ↔ 3 : 2.5
        1 ↔ 4 : 3.5
        2 ↔ 3 : 1.0
        2 ↔ 4 : 2.0
        3 ↔ 4 : 1.5
    """
    import networkx as nx

    G = nx.MultiDiGraph()
    coords = {
        0: (-1.9441, 30.0619),
        1: (-1.9500, 30.0700),
        2: (-1.9550, 30.0750),
        3: (-1.9600, 30.0800),
        4: (-1.9650, 30.0850),
    }
    for node, (lat, lon) in coords.items():
        G.add_node(node, y=lat, x=lon)

    edges = [
        (0,1,2.0),(1,0,2.0),(0,2,3.0),(2,0,3.0),
        (0,3,4.0),(3,0,4.0),(0,4,5.0),(4,0,5.0),
        (1,2,1.5),(2,1,1.5),(1,3,2.5),(3,1,2.5),
        (1,4,3.5),(4,1,3.5),(2,3,1.0),(3,2,1.0),
        (2,4,2.0),(4,2,2.0),(3,4,1.5),(4,3,1.5),
    ]
    for u, v, w in edges:
        G.add_edge(u, v, key=0, composite_weight=w, length=w*1000, highway="primary")

    return G


def main():
    print("Running Phase 9 hardening checks...\n")

    import numpy as np
    from src.graph import build_distance_matrix
    from src.algorithms import held_karp, two_opt, clarke_wright
    from src.solvers import (
        CVRPSolution, naive_assignment,
        solve_tsp_ortools, solve_cvrp, solve_cvrptw,
    )

    G = make_toy_graph()

    # Build the exact distance matrix for nodes 0-4
    node_ids = [0, 1, 2, 3, 4]
    mat = build_distance_matrix(G, node_ids, weight="composite_weight")
    check("distance matrix shape (5,5)", mat.shape == (5, 5))
    check("distance matrix diagonal zeros", all(mat[i][i] == 0.0 for i in range(5)))
    check("mat[0][1] == 2.0", abs(mat[0][1] - 2.0) < 1e-6)
    check("mat[2][3] == 1.0", abs(mat[2][3] - 1.0) < 1e-6)

    # ------------------------------------------------------------------
    # naive_assignment
    # ------------------------------------------------------------------
    sol_naive = naive_assignment([1, 2, 3, 4], num_vehicles=2)
    check("naive produces 2 routes", sol_naive.num_routes == 2)
    check("naive routes cover all 4 customers",
          sorted(sol_naive.routes[0] + sol_naive.routes[1]) == [1, 2, 3, 4])
    check("naive algorithm label", sol_naive.algorithm == "naive-round-robin")

    # ------------------------------------------------------------------
    # held_karp on 5-node TSP (nodes 0-4)
    # ------------------------------------------------------------------
    tour_hk, cost_hk = held_karp(mat)
    check("held_karp returns a tour starting at 0", tour_hk[0] == 0)
    check("held_karp returns a tour ending at 0",   tour_hk[-1] == 0)
    check("held_karp tour visits all 5 nodes", sorted(set(tour_hk)) == [0,1,2,3,4])
    check("held_karp cost is positive", cost_hk > 0)

    # ------------------------------------------------------------------
    # two_opt never worsens a tour
    # ------------------------------------------------------------------
    import random
    random.seed(7)
    initial = list(range(5))
    random.shuffle(initial)
    initial_cost = sum(mat[initial[i]][initial[(i+1)%5]] for i in range(5))
    improved, improved_cost = two_opt(initial, mat)
    check("two_opt never worsens tour", improved_cost <= initial_cost + 1e-9)
    check("two_opt tour has correct length", len(improved) == 5)

    # ------------------------------------------------------------------
    # OR-Tools TSP — should match or beat Held-Karp
    # ------------------------------------------------------------------
    tour_ort, cost_ort = solve_tsp_ortools(mat, time_limit_s=10)
    check("ortools tsp cost <= held_karp cost", cost_ort <= cost_hk + 1e-3)
    check("ortools tsp tour starts at 0", tour_ort[0] == 0)
    check("ortools tsp tour ends at 0",   tour_ort[-1] == 0)

    # ------------------------------------------------------------------
    # clarke_wright — 4 customers, capacity=5kg, demands=[2,2,2,2]
    # ------------------------------------------------------------------
    demands_cw = [0, 2.0, 2.0, 2.0, 2.0]   # index 0 = depot
    sol_cw = clarke_wright(mat, demands_cw, vehicle_capacity=5.0, depot_idx=0)
    check("clarke_wright returns CVRPSolution", isinstance(sol_cw, CVRPSolution))
    check("clarke_wright cost > 0", sol_cw.total_distance_km > 0)
    check("clarke_wright algorithm label", sol_cw.algorithm == "clarke-wright")
    # Each route must not exceed capacity
    for route in sol_cw.routes:
        load = sum(demands_cw[i] for i in route)
        check(f"clarke_wright route load {load:.1f} <= 5.0", load <= 5.0 + 1e-6)

    # ------------------------------------------------------------------
    # solve_cvrp — 4 customers, 2 vehicles, capacity=5kg
    # ------------------------------------------------------------------
    sol_cvrp = solve_cvrp(
        graph=G,
        depot_node=0,
        customer_nodes=[1, 2, 3, 4],
        demands=[2.0, 2.0, 2.0, 2.0],
        vehicle_capacity=5.0,
        num_vehicles=2,
        time_limit_s=10,
    )
    check("solve_cvrp returns CVRPSolution", isinstance(sol_cvrp, CVRPSolution))
    check("solve_cvrp cost > 0", sol_cvrp.total_distance_km > 0)
    check("solve_cvrp cost <= naive cost",
          sol_cvrp.total_distance_km <= sum(
              mat[0][c] + mat[c][0] for c in [1,2,3,4]
          ) + 1e-3)
    all_visited = sorted(n for route in sol_cvrp.routes for n in route)
    check("solve_cvrp visits all 4 customers", all_visited == [1, 2, 3, 4])

    # ------------------------------------------------------------------
    # solve_cvrptw — same instance, relative time windows
    # ------------------------------------------------------------------
    time_windows = [(5, 30), (5, 30), (5, 30), (5, 30)]
    sol_cvrptw = solve_cvrptw(
        graph=G,
        depot_node=0,
        customer_nodes=[1, 2, 3, 4],
        demands=[2.0, 2.0, 2.0, 2.0],
        vehicle_capacity=5.0,
        num_vehicles=2,
        time_windows=time_windows,
        time_limit_s=10,
    )
    check("solve_cvrptw returns CVRPSolution", isinstance(sol_cvrptw, CVRPSolution))
    check("solve_cvrptw cost > 0", sol_cvrptw.total_distance_km > 0)
    check("solve_cvrptw has estimated_arrival_times",
          len(sol_cvrptw.estimated_arrival_times) > 0)
    check("solve_cvrptw time_window_violations >= 0",
          sol_cvrptw.time_window_violations >= 0)
    all_visited_tw = sorted(n for route in sol_cvrptw.routes for n in route)
    check("solve_cvrptw visits all 4 customers", all_visited_tw == [1, 2, 3, 4])

    # ------------------------------------------------------------------
    # ValueError guards
    # ------------------------------------------------------------------
    try:
        solve_cvrp(G, 0, [], [2.0], 5.0, 2)
        check("solve_cvrp raises ValueError on empty customers", False)
    except ValueError:
        check("solve_cvrp raises ValueError on empty customers", True)

    try:
        solve_cvrp(G, 0, [1], [2.0], 0.0, 2)
        check("solve_cvrp raises ValueError on zero capacity", False)
    except ValueError:
        check("solve_cvrp raises ValueError on zero capacity", True)

    try:
        solve_cvrptw(G, 0, [1,2], [2.0,2.0], 5.0, 2, [(0,10)])  # mismatched tw length
        check("solve_cvrptw raises ValueError on mismatched time_windows", False)
    except ValueError:
        check("solve_cvrptw raises ValueError on mismatched time_windows", True)

    print("\nall checks passed")


if __name__ == "__main__":
    main()