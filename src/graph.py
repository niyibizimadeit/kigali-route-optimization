"""
graph.py — OSM ingestion and composite edge cost model.

This is the only module that touches the road network data. Every other module
that needs the graph imports it from here. Never create graph objects inline
in notebooks or other src files.

Composite edge weight formula:
    w(e) = travel_time(e) × quality_penalty(e)
    travel_time(e) = (length_m / 1000) / speed_kmh(highway_type) × 60  [minutes]
    quality_penalty = QUALITY_PENALTY_UNPAVED if surface is unpaved, else QUALITY_PENALTY_PAVED

Note on coordinate system:
    The graph is kept in WGS84 (lat/lon). Node 'x' = longitude, 'y' = latitude.
    Edge 'length' attributes are in metres (OSMnx always computes these).
    We do not project to UTM — 'length' gives us metric distances directly,
    and WGS84 coordinates are needed for Folium map rendering.
"""

import os
from typing import Optional

import networkx as nx
import numpy as np
import osmnx as ox

# ---------------------------------------------------------------------------
# Edge cost constants
# These are the exact parameters used in giraxpress_integration/export_solver.py.
# If you change any value here, change it there too.
# ---------------------------------------------------------------------------

SPEED_BY_HIGHWAY: dict[str, float] = {
    "motorway": 80,
    "trunk": 60,
    "primary": 50,
    "secondary": 40,
    "tertiary": 30,
    "residential": 25,
    "service": 15,
    "unclassified": 20,
    "track": 8,
    "path": 5,
    "default": 20,
}

UNPAVED_SURFACES: set[str] = {
    "unpaved",
    "dirt",
    "gravel",
    "compacted",
    "ground",
    "mud",
    "sand",
    "grass",
}

QUALITY_PENALTY_UNPAVED: float = 1.4
QUALITY_PENALTY_PAVED: float = 1.0

RAW_GRAPH_PATH: str = "data/kigali_raw.graphml"
ENRICHED_GRAPH_PATH: str = "data/kigali_enriched.graphml"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_raw_graph(
    output_path: str = RAW_GRAPH_PATH,
    force_refresh: bool = False,
) -> nx.MultiDiGraph:
    """
    Pull the Kigali drive network from OpenStreetMap and save to disk.

    If output_path already exists and force_refresh is False, loads from disk
    instead of hitting the OSM API again. Pass force_refresh=True to re-pull.

    The graph is kept in WGS84 (lat/lon). Node attributes 'x' (longitude) and
    'y' (latitude) are preserved for Folium map rendering. Edge 'length'
    attributes are in metres — used by enrich_graph() for travel time calculation.

    Args:
        output_path: Where to save/load the raw graphml file.
        force_refresh: If True, always re-pull from OSM even if file exists.

    Returns:
        NetworkX MultiDiGraph in WGS84 with OSM edge attributes.
    """
    if os.path.exists(output_path) and not force_refresh:
        print(f"Loading raw graph from disk: {output_path}")
        G = ox.load_graphml(output_path)
        print(f"Loaded — {len(G.nodes):,} nodes, {len(G.edges):,} edges")
        return G

    print("Pulling Kigali road network from OpenStreetMap...")
    G = ox.graph_from_place("Kigali, Rwanda", network_type="drive")

    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    ox.save_graphml(G, output_path)
    print(f"Saved to {output_path} — {len(G.nodes):,} nodes, {len(G.edges):,} edges")
    return G


def enrich_graph(
    G: nx.MultiDiGraph,
    params: Optional[dict] = None,
) -> nx.MultiDiGraph:
    """
    Apply the composite edge cost model to every edge in the graph.

    Adds a 'composite_weight' attribute to every edge. The weight is:
        travel_time_min × quality_penalty

    Args:
        G: Raw OSM graph (from load_raw_graph).
        params: Optional dict to override default constants. Supported keys:
                SPEED_BY_HIGHWAY, UNPAVED_SURFACES,
                QUALITY_PENALTY_UNPAVED, QUALITY_PENALTY_PAVED.
                Useful for the ablation study — do not use in production.

    Returns:
        The same graph with 'composite_weight' added to all edges (mutates in place,
        also returns for chaining).
    """
    # Resolve active constants — merge defaults with any overrides
    speed_map   = (params or {}).get("SPEED_BY_HIGHWAY",       SPEED_BY_HIGHWAY)
    unpaved_set = (params or {}).get("UNPAVED_SURFACES",        UNPAVED_SURFACES)
    pen_unpaved = (params or {}).get("QUALITY_PENALTY_UNPAVED", QUALITY_PENALTY_UNPAVED)
    pen_paved   = (params or {}).get("QUALITY_PENALTY_PAVED",   QUALITY_PENALTY_PAVED)

    default_speed = speed_map.get("default", 20)

    for u, v, key, data in G.edges(keys=True, data=True):
        # --- highway type → speed ---
        hw = data.get("highway", "default")
        if isinstance(hw, list):
            hw = hw[0]          # OSM sometimes stores a list; take the first
        speed_kmh = speed_map.get(hw, default_speed)

        # --- length → travel time ---
        length_m = data.get("length", 0)
        travel_time_min = (length_m / 1000.0) / speed_kmh * 60.0

        # --- surface → quality penalty ---
        surface = data.get("surface", None)
        if isinstance(surface, list):
            surface = surface[0]
        if surface is not None and surface.lower() in unpaved_set:
            quality_penalty = pen_unpaved
        else:
            quality_penalty = pen_paved

        # --- composite weight ---
        G[u][v][key]["composite_weight"] = travel_time_min * quality_penalty

    return G


def save_enriched_graph(
    G: nx.MultiDiGraph,
    output_path: str = ENRICHED_GRAPH_PATH,
) -> None:
    """
    Save the enriched graph to disk as graphml.

    Args:
        G: Enriched graph (composite_weight must already be set on all edges).
        output_path: Destination path.
    """
    dir_name = os.path.dirname(output_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    ox.save_graphml(G, output_path)
    print(f"Saved enriched graph to {output_path}")


def load_enriched_graph(
    path: str = ENRICHED_GRAPH_PATH,
) -> nx.MultiDiGraph:
    """
    Load the enriched graph from disk.

    Raises:
        FileNotFoundError: If the file does not exist. Message will tell you
                           which notebook to run to generate it.

    Args:
        path: Path to the enriched graphml file.

    Returns:
        Enriched NetworkX MultiDiGraph.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Enriched graph not found at '{path}'. "
            "Run notebooks/02_graph_construction.ipynb first to generate it."
        )
    print(f"Loading enriched graph from: {path}")
    G = ox.load_graphml(path)
    print(f"Loaded — {len(G.nodes):,} nodes, {len(G.edges):,} edges")
    return G


def get_node_coordinates(
    G: nx.MultiDiGraph,
    node_id: int,
) -> tuple[float, float]:
    """
    Return (lat, lon) for a given OSM node ID.

    Args:
        G: Any graph with 'y' (lat) and 'x' (lon) node attributes.
        node_id: OSM node ID.

    Returns:
        (latitude, longitude) as floats.
    """
    node = G.nodes[node_id]
    return float(node["y"]), float(node["x"])


def build_distance_matrix(
    G: nx.MultiDiGraph,
    node_ids: list[int],
    weight: str = "composite_weight",
) -> np.ndarray:
    """
    Build an N×N matrix of shortest-path costs between a list of nodes.

    Uses Dijkstra under the hood. Diagonal is always 0. If no path exists
    between two nodes, the cell is set to float('inf').

    Args:
        G: Enriched graph.
        node_ids: List of OSM node IDs. Length N.
        weight: Edge attribute to use as cost. Default is 'composite_weight'.

    Returns:
        numpy ndarray of shape (N, N).
    """
    n = len(node_ids)
    matrix = np.full((n, n), fill_value=np.inf)
    np.fill_diagonal(matrix, 0.0)

    for i, source in enumerate(node_ids):
        try:
            lengths = nx.single_source_dijkstra_path_length(
                G, source, weight=weight
            )
            for j, target in enumerate(node_ids):
                if i == j:
                    continue
                if target in lengths:
                    matrix[i][j] = lengths[target]
        except nx.NodeNotFound:
            # Leave row as inf if source not in graph
            pass

    return matrix