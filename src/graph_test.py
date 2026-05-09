"""
graph_test.py — Phase 1 validation script.

Run from the repo root with:
    python src/graph_test.py

Must print 'all checks passed' without error. If any check fails,
it prints the failing check name and exits with a non-zero code.
"""

import sys
import os

# Ensure repo root is on the path so 'from src.x import y' works
# regardless of how the script is invoked.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check(name: str, condition: bool) -> None:
    if not condition:
        print(f"FAILED: {name}")
        sys.exit(1)
    print(f"  ok: {name}")


def main():
    print("Running Phase 1 validation checks...\n")

    # --- Import checks ---
    try:
        from src.graph import (
            load_raw_graph,
            enrich_graph,
            save_enriched_graph,
            load_enriched_graph,
            get_node_coordinates,
            build_distance_matrix,
            SPEED_BY_HIGHWAY,
            UNPAVED_SURFACES,
            QUALITY_PENALTY_UNPAVED,
            QUALITY_PENALTY_PAVED,
        )
        check("src/graph.py imports cleanly", True)
    except ImportError as e:
        check(f"src/graph.py imports cleanly [{e}]", False)

    try:
        from src.algorithms import dijkstra, astar, held_karp, two_opt, clarke_wright
        check("src/algorithms.py imports cleanly", True)
    except ImportError as e:
        check(f"src/algorithms.py imports cleanly [{e}]", False)

    try:
        from src.solvers import (
            CVRPSolution,
            naive_assignment,
            solve_tsp_ortools,
            solve_cvrp,
            solve_cvrptw,
            solve_rolling_horizon,
        )
        check("src/solvers.py imports cleanly", True)
    except ImportError as e:
        check(f"src/solvers.py imports cleanly [{e}]", False)

    try:
        from src.viz import (
            plot_graph,
            plot_routes,
            plot_cvrp_routes,
            plot_benchmark,
            plot_regret_curves,
            export_all_figures,
        )
        check("src/viz.py imports cleanly", True)
    except ImportError as e:
        check(f"src/viz.py imports cleanly [{e}]", False)

    try:
        from src.rl_bridge import (
            simulate_delivery_outcomes,
            compute_linucb_regret,
            CLICK_REWARD,
            CART_REWARD,
            PURCHASE_REWARD,
            DELIVERY_SUCCESS_REWARD,
            DELIVERY_FAILURE_REWARD,
            LAMBDA_DEFAULT,
            DeliveryEvent,
            RegretResult,
        )
        check("src/rl_bridge.py imports cleanly", True)
    except ImportError as e:
        check(f"src/rl_bridge.py imports cleanly [{e}]", False)

    # --- Constant sanity checks ---
    from src.graph import SPEED_BY_HIGHWAY, QUALITY_PENALTY_UNPAVED, QUALITY_PENALTY_PAVED
    from src.rl_bridge import DELIVERY_SUCCESS_REWARD, DELIVERY_FAILURE_REWARD

    check("SPEED_BY_HIGHWAY has 'primary' key", "primary" in SPEED_BY_HIGHWAY)
    check("SPEED_BY_HIGHWAY has 'default' key", "default" in SPEED_BY_HIGHWAY)
    check("QUALITY_PENALTY_UNPAVED > QUALITY_PENALTY_PAVED", QUALITY_PENALTY_UNPAVED > QUALITY_PENALTY_PAVED)
    check("DELIVERY_SUCCESS_REWARD is positive", DELIVERY_SUCCESS_REWARD > 0)
    check("DELIVERY_FAILURE_REWARD is negative", DELIVERY_FAILURE_REWARD < 0)

    # --- CVRPSolution dataclass check ---
    from src.solvers import CVRPSolution
    sol = CVRPSolution(
        routes=[[1, 2, 3]],
        total_distance_km=12.5,
        num_routes=1,
        solve_time_s=0.01,
        algorithm="test",
    )
    check("CVRPSolution instantiates with defaults", sol.time_window_violations == 0)
    check("CVRPSolution estimated_arrival_times defaults to empty dict", sol.estimated_arrival_times == {})

    # --- Third-party library checks ---
    try:
        import osmnx
        check(f"osmnx importable (version: {osmnx.__version__})", True)
    except ImportError:
        check("osmnx importable", False)

    try:
        import networkx
        check(f"networkx importable (version: {networkx.__version__})", True)
    except ImportError:
        check("networkx importable", False)

    try:
        from ortools.constraint_solver import routing_enums_pb2
        check("ortools importable", True)
    except ImportError:
        check("ortools importable", False)

    try:
        import geopandas
        check(f"geopandas importable (version: {geopandas.__version__})", True)
    except ImportError:
        check("geopandas importable", False)

    try:
        import folium
        check(f"folium importable (version: {folium.__version__})", True)
    except ImportError:
        check("folium importable", False)

    print("\nall checks passed")


if __name__ == "__main__":
    main()