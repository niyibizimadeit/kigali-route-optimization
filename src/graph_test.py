"""
graph_test.py — Phase 4 hardening validation.

Tests actual function behavior on a small synthetic graph.
Run from the repo root:
    python src/graph_test.py

Must print 'all checks passed' without error.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check(name: str, condition: bool) -> None:
    if not condition:
        print(f"FAILED: {name}")
        sys.exit(1)
    print(f"  ok: {name}")


def make_synthetic_graph():
    """
    Build a small 4-node directed graph that mimics OSM structure.

    Layout:
        0 ──(primary, 1000m)──> 1
        1 ──(residential, 500m)──> 2
        2 ──(track, 200m, surface=dirt)──> 3
        3 ──(primary, 800m)──> 0
    """
    import networkx as nx

    G = nx.MultiDiGraph()

    # Nodes with lat/lon (WGS84 coords near Kigali)
    G.add_node(0, y=-1.9441, x=30.0619)
    G.add_node(1, y=-1.9500, x=30.0700)
    G.add_node(2, y=-1.9550, x=30.0750)
    G.add_node(3, y=-1.9600, x=30.0800)

    G.add_edge(0, 1, key=0, highway="primary",     length=1000.0)
    G.add_edge(1, 2, key=0, highway="residential", length=500.0)
    G.add_edge(2, 3, key=0, highway="track",       length=200.0, surface="dirt")
    G.add_edge(3, 0, key=0, highway="primary",     length=800.0)

    return G


def main():
    print("Running Phase 4 hardening checks...\n")

    import networkx as nx
    import numpy as np

    from src.graph import (
        enrich_graph,
        save_enriched_graph,
        load_enriched_graph,
        get_node_coordinates,
        build_distance_matrix,
        SPEED_BY_HIGHWAY,
        QUALITY_PENALTY_UNPAVED,
        QUALITY_PENALTY_PAVED,
    )

    G = make_synthetic_graph()

    # ------------------------------------------------------------------
    # enrich_graph — default params
    # ------------------------------------------------------------------
    enrich_graph(G)

    check("all edges have composite_weight after enrich_graph",
          all("composite_weight" in d for _, _, d in G.edges(data=True)))

    check("composite_weight is always positive",
          all(d["composite_weight"] > 0 for _, _, d in G.edges(data=True)))

    # Edge 0→1: primary, 1000m, paved
    # travel_time = (1000/1000) / 50 * 60 = 1.2 min, penalty = 1.0 → weight = 1.2
    w_primary = G[0][1][0]["composite_weight"]
    check("primary 1000m edge weight ≈ 1.2 min",
          abs(w_primary - 1.2) < 1e-6)

    # Edge 2→3: track, 200m, surface=dirt (unpaved)
    # travel_time = (200/1000) / 8 * 60 = 1.5 min, penalty = 1.4 → weight = 2.1
    w_track = G[2][3][0]["composite_weight"]
    check("track+dirt 200m edge weight ≈ 2.1 min",
          abs(w_track - 2.1) < 1e-6)

    # Edge 1→2: residential, 500m, no surface tag → paved penalty
    # travel_time = (500/1000) / 25 * 60 = 1.2 min, penalty = 1.0 → weight = 1.2
    w_residential = G[1][2][0]["composite_weight"]
    check("residential 500m edge weight ≈ 1.2 min",
          abs(w_residential - 1.2) < 1e-6)

    # ------------------------------------------------------------------
    # enrich_graph — params override (ablation)
    # ------------------------------------------------------------------
    G2 = make_synthetic_graph()
    enrich_graph(G2, params={"QUALITY_PENALTY_UNPAVED": 1.0, "QUALITY_PENALTY_PAVED": 1.0})

    w_track_no_penalty = G2[2][3][0]["composite_weight"]
    # With penalty=1.0: (200/1000) / 8 * 60 = 1.5 min exactly
    check("ablation override: track+dirt weight ≈ 1.5 min (no penalty)",
          abs(w_track_no_penalty - 1.5) < 1e-6)

    check("ablation: unpaved edge lighter than with penalty",
          w_track_no_penalty < w_track)

    # ------------------------------------------------------------------
    # get_node_coordinates
    # ------------------------------------------------------------------
    lat, lon = get_node_coordinates(G, 0)
    check("get_node_coordinates returns correct lat", abs(lat - (-1.9441)) < 1e-6)
    check("get_node_coordinates returns correct lon", abs(lon - 30.0619) < 1e-6)

    # ------------------------------------------------------------------
    # build_distance_matrix
    # ------------------------------------------------------------------
    node_ids = [0, 1, 2, 3]
    matrix = build_distance_matrix(G, node_ids, weight="composite_weight")

    check("distance matrix shape is (4, 4)", matrix.shape == (4, 4))
    check("distance matrix diagonal is all zeros",
          all(matrix[i][i] == 0.0 for i in range(4)))
    check("distance matrix has no negative values",
          np.all(matrix[matrix != np.inf] >= 0))

    # Direct edge 0→1 = 1.2 min; matrix[0][1] should equal that
    check("matrix[0][1] matches direct edge weight",
          abs(matrix[0][1] - w_primary) < 1e-6)

    # Path 0→1→2: 1.2 + 1.2 = 2.4 min
    check("matrix[0][2] matches 2-hop path cost",
          abs(matrix[0][2] - (w_primary + w_residential)) < 1e-6)

    # ------------------------------------------------------------------
    # save_enriched_graph / load_enriched_graph round-trip
    # ------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(suffix=".graphml", delete=False) as f:
        tmp_path = f.name

    try:
        save_enriched_graph(G, tmp_path)
        check("enriched graph file exists after save", os.path.exists(tmp_path))
        check("enriched graph file is non-empty", os.path.getsize(tmp_path) > 0)

        G_reloaded = load_enriched_graph(tmp_path)
        check("reloaded node count matches", len(G.nodes) == len(G_reloaded.nodes))
        check("reloaded edge count matches", len(G.edges) == len(G_reloaded.edges))

        w_reloaded = float(G_reloaded[0][1][0]["composite_weight"])
        check("composite_weight survives round-trip",
              abs(w_reloaded - w_primary) < 1e-6)
    finally:
        os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # load_enriched_graph — FileNotFoundError on missing file
    # ------------------------------------------------------------------
    try:
        load_enriched_graph("/tmp/does_not_exist_kigali.graphml")
        check("load_enriched_graph raises FileNotFoundError on missing file", False)
    except FileNotFoundError as e:
        check("load_enriched_graph raises FileNotFoundError on missing file", True)
        check("error message mentions notebook 02",
              "02" in str(e) or "notebook" in str(e).lower())

    print("\nall checks passed")


if __name__ == "__main__":
    main()