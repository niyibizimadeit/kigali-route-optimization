"""
generate_instances.py — Write benchmark CVRP instances to results/instances/.

Run from the repo root:
    python src/generate_instances.py

Produces:
    results/instances/instance_n50_seed42.json
    results/instances/instance_n100_seed42.json
    results/instances/instance_n200_seed42.json
"""

import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import networkx as nx
from src.graph import load_enriched_graph, get_node_coordinates

def main():
    print("Loading enriched graph...")
    G = load_enriched_graph()
    for u, v, k, d in G.edges(keys=True, data=True):
        if "composite_weight" in d:
            G[u][v][k]["composite_weight"] = float(d["composite_weight"])

    scc = max(nx.strongly_connected_components(G), key=len)
    scc_nodes = list(scc)

    depot_node = min(scc_nodes, key=lambda n: (
        (G.nodes[n]["y"] - (-1.9500))**2 + (G.nodes[n]["x"] - 30.0588)**2
    ))

    os.makedirs("results/instances", exist_ok=True)

    SEED = 42
    random.seed(SEED)

    for N in [50, 100, 200]:
        customers = random.sample([n for n in scc_nodes if n != depot_node], N)
        demands   = [round(random.uniform(1, 4), 1) for _ in customers]

        depot_lat, depot_lon = get_node_coordinates(G, depot_node)
        customer_coords = [get_node_coordinates(G, n) for n in customers]

        instance = {
            "seed":            SEED,
            "n_customers":     N,
            "vehicle_capacity": 20,
            "n_vehicles":      5,
            "depot": {
                "osm_node_id": depot_node,
                "lat": depot_lat,
                "lon": depot_lon,
            },
            "customers": [
                {
                    "osm_node_id": node,
                    "lat": lat,
                    "lon": lon,
                    "demand_kg": demand,
                }
                for node, (lat, lon), demand in zip(customers, customer_coords, demands)
            ],
        }

        path = f"results/instances/instance_n{N}_seed{SEED}.json"
        with open(path, "w") as f:
            json.dump(instance, f, indent=2)
        print(f"  Written {path}  ({N} customers, total_demand={sum(demands):.1f}kg)")

    print("\nDone.")

if __name__ == "__main__":
    main()