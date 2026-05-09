"""
viz.py — All visualization for kigali-route-optimization.

Produces two output types:
  - Folium HTML maps  (interactive, opens in browser)
  - Matplotlib figures (static PNG/PDF for the paper)

Never put visualization logic in notebooks. Notebooks call functions from here.
"""

from typing import Optional

import folium
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Folium maps
# ---------------------------------------------------------------------------


def plot_graph(
    G,
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render the full Kigali road network as a Folium map, colored by highway type.

    Args:
        G: NetworkX graph with 'y' (lat), 'x' (lon) node attributes and
           'highway' edge attributes.
        output_path: If provided, save the HTML map to this path.

    Returns:
        folium.Map object (also saved to output_path if specified).
    """
    pass


def plot_routes(
    G,
    paths: list[list[int]],
    labels: Optional[list[str]] = None,
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render a list of paths (from shortest-path algorithms) on a Folium map.

    Each path is drawn as a polyline following actual road geometry from the graph.
    Paths are colored distinctly. Start and end nodes are marked.

    Args:
        G: Enriched NetworkX graph.
        paths: List of paths, each a list of OSM node IDs.
        labels: Optional label for each path (shown in the legend).
        output_path: If provided, save the HTML map to this path.

    Returns:
        folium.Map object.
    """
    pass


def plot_cvrp_routes(
    G,
    solution,
    node_coordinates: dict[int, tuple[float, float]],
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render a CVRPSolution on a Folium map.

    Each vehicle route is drawn in a distinct color. The depot is marked
    with a star icon. Customer stops are numbered in delivery order.
    Route lines follow actual road geometry.

    This is the reference visualization that GiraXpress admin map is modeled on.

    Args:
        G: Enriched NetworkX graph (used to trace road geometry).
        solution: CVRPSolution from any solver.
        node_coordinates: Maps OSM node ID → (lat, lon). Used to place markers.
        output_path: If provided, save the HTML map to this path.

    Returns:
        folium.Map object.
    """
    pass


# ---------------------------------------------------------------------------
# Matplotlib figures
# ---------------------------------------------------------------------------


def plot_benchmark(
    csv_path: str,
    metric: str,
    group_by: str,
    output_path: Optional[str] = None,
) -> plt.Figure:
    """
    Grouped bar chart from a benchmark CSV file.

    Args:
        csv_path: Path to a CSV with at minimum columns: algorithm, n_stops,
                  and the metric column.
        metric: Column name to plot on the y-axis (e.g. 'total_dist_km').
        group_by: Column name to group bars by (e.g. 'n_stops').
        output_path: If provided, save as PNG and PDF (strips extension,
                     appends both).

    Returns:
        matplotlib Figure object.
    """
    pass


def plot_regret_curves(
    regret_data: dict[str, np.ndarray],
    output_path: Optional[str] = None,
) -> plt.Figure:
    """
    Plot cumulative regret curves for multiple routing quality scenarios.

    Args:
        regret_data: Dict mapping scenario name → cumulative regret array (length T).
        output_path: If provided, save as PNG and PDF.

    Returns:
        matplotlib Figure object.
    """
    pass


def export_all_figures(results_dir: str = "results/") -> None:
    """
    Regenerate all paper figures from their source CSVs in results_dir.

    Run this after any benchmark re-run to update all figures atomically.
    Each figure is saved as both PNG (300 DPI) and PDF.

    Args:
        results_dir: Directory containing benchmark CSVs and where figures
                     will be written.
    """
    pass
