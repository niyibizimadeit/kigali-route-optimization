"""
viz.py — All visualization for kigali-route-optimization.

Produces:
  - Folium HTML maps  (interactive, opens in browser)
  - Matplotlib figures (PNG 300dpi + PDF for the paper)

Never put visualization logic in notebooks. Notebooks call functions here.
"""

from typing import Optional

import folium
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd

# Paper figure defaults — applied globally when this module is imported
matplotlib.rcParams.update({
    "figure.dpi":        300,
    "savefig.dpi":       300,
    "font.size":         11,
    "axes.labelsize":    12,
    "axes.titlesize":    12,
    "legend.fontsize":   10,
    "figure.facecolor":  "white",
})

# Consistent color palette across all figures
PALETTE = {
    "naive":          "#adb5bd",
    "clarke-wright":  "#f4a261",
    "ortools-cvrp":   "#2a9d8f",
    "ortools-cvrptw": "#e63946",
    "route_0":        "#e63946",
    "route_1":        "#2a9d8f",
    "route_2":        "#f4a261",
    "route_3":        "#6a4c93",
    "route_4":        "#118ab2",
}

ALGO_LABELS = {
    "naive":          "Naive",
    "clarke-wright":  "Clarke-Wright",
    "ortools-cvrp":   "OR-Tools CVRP",
    "ortools-cvrptw": "OR-Tools CVRPTW",
}


# ---------------------------------------------------------------------------
# Folium maps
# ---------------------------------------------------------------------------


def plot_graph(
    G,
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render the Kigali road network as a Folium map, colored by highway type.

    Args:
        G: NetworkX graph with 'y' (lat), 'x' (lon) node attrs and 'highway' edge attrs.
        output_path: If provided, save HTML to this path.

    Returns:
        folium.Map object.
    """
    hw_colors = {
        "primary":     "#e63946",
        "secondary":   "#f4a261",
        "tertiary":    "#2a9d8f",
        "residential": "#adb5bd",
        "service":     "#dee2e6",
    }

    # Center on mean node coordinates
    lats = [d["y"] for _, d in G.nodes(data=True)]
    lons = [d["x"] for _, d in G.nodes(data=True)]
    m = folium.Map(location=[np.mean(lats), np.mean(lons)], zoom_start=13)

    for u, v, data in G.edges(data=True):
        hw = data.get("highway", "other")
        if isinstance(hw, list):
            hw = hw[0]
        color = hw_colors.get(hw, "#ced4da")
        lat_u, lon_u = float(G.nodes[u]["y"]), float(G.nodes[u]["x"])
        lat_v, lon_v = float(G.nodes[v]["y"]), float(G.nodes[v]["x"])
        folium.PolyLine(
            [(lat_u, lon_u), (lat_v, lon_v)],
            color=color, weight=1.5, opacity=0.6,
            tooltip=hw,
        ).add_to(m)

    if output_path:
        m.save(output_path)
    return m


def plot_routes(
    G,
    paths: list[list[int]],
    labels: Optional[list[str]] = None,
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render shortest-path results on a Folium map.

    Each path is a polyline following node coordinates. Start/end marked.

    Args:
        G: Enriched NetworkX graph.
        paths: List of paths, each a list of OSM node IDs.
        labels: Optional label per path for tooltips.
        output_path: If provided, save HTML.

    Returns:
        folium.Map object.
    """
    route_colors = [
        PALETTE.get(f"route_{i}", "#333333") for i in range(len(paths))
    ]
    lats = [float(G.nodes[n]["y"]) for path in paths for n in path]
    lons = [float(G.nodes[n]["x"]) for path in paths for n in path]
    m = folium.Map(location=[np.mean(lats), np.mean(lons)], zoom_start=13)

    for idx, path in enumerate(paths):
        color = route_colors[idx]
        label = labels[idx] if labels else f"Route {idx+1}"
        coords = [(float(G.nodes[n]["y"]), float(G.nodes[n]["x"])) for n in path]

        folium.PolyLine(coords, color=color, weight=4, opacity=0.85,
                        tooltip=label).add_to(m)
        folium.CircleMarker(coords[0],  radius=8, color=color, fill=True,
                            fill_opacity=1.0, tooltip=f"{label} start").add_to(m)
        folium.CircleMarker(coords[-1], radius=8, color=color, fill=True,
                            fill_opacity=0.3, tooltip=f"{label} end").add_to(m)

    if output_path:
        m.save(output_path)
    return m


def plot_cvrp_routes(
    G,
    solution,
    node_coordinates: dict[int, tuple[float, float]],
    depot_node: Optional[int] = None,
    output_path: Optional[str] = None,
) -> folium.Map:
    """
    Render a CVRPSolution on a Folium map.

    Each vehicle route in a distinct color. Depot marked with home icon.
    Customer stops numbered in delivery order.

    This is the reference visualization that GiraXpress admin map is modeled on.

    Args:
        G: Enriched NetworkX graph (for geometry).
        solution: CVRPSolution from any solver.
        node_coordinates: Maps OSM node ID → (lat, lon).
        depot_node: OSM node ID of the depot (for depot marker).
        output_path: If provided, save HTML.

    Returns:
        folium.Map object.
    """
    all_lats = [lat for lat, lon in node_coordinates.values()]
    all_lons = [lon for lat, lon in node_coordinates.values()]
    m = folium.Map(location=[np.mean(all_lats), np.mean(all_lons)], zoom_start=13)

    # Depot marker
    if depot_node and depot_node in node_coordinates:
        dlat, dlon = node_coordinates[depot_node]
        folium.Marker(
            [dlat, dlon],
            tooltip="Depot",
            icon=folium.Icon(color="black", icon="home"),
        ).add_to(m)

    for v_idx, route in enumerate(solution.routes):
        color = PALETTE.get(f"route_{v_idx % 5}", "#333333")

        for stop_order, node_idx in enumerate(route):
            if node_idx not in node_coordinates:
                continue
            lat, lon = node_coordinates[node_idx]
            folium.CircleMarker(
                [lat, lon], radius=7,
                color=color, fill=True, fill_opacity=0.9,
                tooltip=f"Vehicle {v_idx+1} — stop {stop_order+1}",
            ).add_to(m)

            # Stop number label
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:9px;font-weight:bold;color:{color}">'
                         f'{stop_order+1}</div>',
                    icon_size=(20, 20),
                ),
            ).add_to(m)

        # Route line (straight segments — road geometry requires per-edge path lookup)
        if depot_node and depot_node in node_coordinates:
            depot_coord = node_coordinates[depot_node]
            route_coords = (
                [depot_coord]
                + [node_coordinates[n] for n in route if n in node_coordinates]
                + [depot_coord]
            )
            folium.PolyLine(route_coords, color=color, weight=3,
                            opacity=0.7, tooltip=f"Vehicle {v_idx+1}").add_to(m)

    if output_path:
        m.save(output_path)
    return m


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
    Grouped bar chart from a benchmark CSV.

    Args:
        csv_path: Path to CSV with columns: algorithm, n_stops (or similar), metric.
        metric: Column to plot on y-axis.
        group_by: Column to group bars by (e.g. 'n').
        output_path: If provided, save as PNG and PDF.

    Returns:
        matplotlib Figure.
    """
    df = pd.read_csv(csv_path)
    agg = df.groupby(["algorithm", group_by])[metric].mean().reset_index()

    groups   = sorted(agg[group_by].unique())
    algos    = [a for a in ALGO_LABELS if a in agg["algorithm"].unique()]
    x        = np.arange(len(groups))
    width    = 0.8 / len(algos)

    fig, ax = plt.subplots(figsize=(10, 6))
    for i, algo in enumerate(algos):
        vals = [
            agg[(agg["algorithm"] == algo) & (agg[group_by] == g)][metric].values[0]
            if len(agg[(agg["algorithm"] == algo) & (agg[group_by] == g)]) > 0 else 0
            for g in groups
        ]
        ax.bar(x + i * width, vals, width, label=ALGO_LABELS[algo],
               color=PALETTE[algo], alpha=0.9)

    ax.set_xlabel(group_by)
    ax.set_ylabel(metric)
    ax.set_xticks(x + width * (len(algos) - 1) / 2)
    ax.set_xticklabels(groups)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    if output_path:
        base = output_path.rsplit(".", 1)[0]
        plt.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
        plt.savefig(f"{base}.pdf", bbox_inches="tight")

    return fig


def plot_regret_curves(
    regret_data: dict[str, np.ndarray],
    output_path: Optional[str] = None,
) -> plt.Figure:
    """
    Cumulative regret curves for multiple routing quality scenarios.

    Args:
        regret_data: Dict mapping scenario name → cumulative regret array (length T).
        output_path: If provided, save as PNG and PDF.

    Returns:
        matplotlib Figure.
    """
    scenario_colors = {
        "Naive routing":   "#e63946",
        "Clarke-Wright":   "#f4a261",
        "OR-Tools CVRPTW": "#2a9d8f",
    }
    scenario_styles = {
        "Naive routing":   "--",
        "Clarke-Wright":   "-.",
        "OR-Tools CVRPTW": "-",
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    for scenario, regret in regret_data.items():
        T = len(regret)
        ax.plot(
            range(T), regret,
            label=scenario,
            color=scenario_colors.get(scenario, "#333333"),
            linestyle=scenario_styles.get(scenario, "-"),
            linewidth=2,
        )

    ax.set_xlabel("Interaction step (T)")
    ax.set_ylabel("Cumulative regret")
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()

    if output_path:
        base = output_path.rsplit(".", 1)[0]
        plt.savefig(f"{base}.png", dpi=300, bbox_inches="tight")
        plt.savefig(f"{base}.pdf", bbox_inches="tight")

    return fig


def export_all_figures(results_dir: str = "results/") -> None:
    """
    Regenerate all paper figures from source CSVs in results_dir.

    Run this after any benchmark re-run to update figures atomically.
    Each figure saved as PNG (300 DPI) and PDF.

    Args:
        results_dir: Directory containing CSVs and where figures are written.
    """
    import os

    print(f"Regenerating figures from {results_dir}...")

    # Figure 1: distance benchmark
    dist_csv = os.path.join(results_dir, "cvrp_benchmark_full.csv")
    if os.path.exists(dist_csv):
        fig = plot_benchmark(dist_csv, metric="total_dist", group_by="n",
                             output_path=os.path.join(results_dir, "benchmark_distance.png"))
        plt.close(fig)
        print("  ✓ benchmark_distance.png / .pdf")
    else:
        print(f"  skipped benchmark_distance (no {dist_csv})")

    # Figure 2: regret curves
    rl_csv = os.path.join(results_dir, "rl_reward_impact.csv")
    if os.path.exists(rl_csv):
        # rl_reward_impact.csv doesn't store the full curve — just final values.
        # Re-run the simulation to regenerate curves.
        print("  skipped regret_curves (requires re-running notebook 07)")
    else:
        print(f"  skipped regret_curves (no {rl_csv})")

    print("Done.")