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
    pass


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
    pass


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
    pass


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
    pass


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
    pass