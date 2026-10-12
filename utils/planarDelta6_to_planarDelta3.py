"""
Planar graph degree reduction: max-degree-6 → max-degree-3
===========================================================
Implements the vertex-splitting / cycle-gadget construction from
Lemma 3.1 of Johnson (1987) "The NP-Completeness Column: An Ongoing
Guide", Journal of Algorithms 8(3).

Construction (per high-degree vertex v with neighbours n1, n2, …, nk, k > 3):
  1. Remove v from the graph.
  2. Introduce k new "gadget" nodes  v_1, v_2, …, v_k  (one per original
     neighbour, in cyclic planar order around v).
  3. Connect them in a cycle:  v_1 – v_2 – … – v_k – v_1
     (uses 2 of the 3 available edges per gadget node).
  4. Reconnect each gadget node v_i to the original neighbour n_i
     (uses the 3rd edge of v_i).

After the transformation:
  • Every gadget node has degree exactly 3.
  • Vertices of original degree ≤ 3 are untouched (degree ≤ 3).
  • Planarity is preserved: the cycle gadget fits inside the face
    that surrounded v in the planar embedding.

The function below works on a NetworkX graph.  It uses a combinatorial
planar embedding (computed by networkx) to obtain the correct cyclic
neighbour order, which is required to keep the result planar.

Dependencies: networkx >= 2.6, (optionally) matplotlib for drawing.
"""

import networkx as nx
from itertools import count


# ── helpers ──────────────────────────────────────────────────────────────────

def _cyclic_neighbours(G: nx.Graph, v, embedding: nx.PlanarEmbedding) -> list:
    """Return neighbours of v in cyclic (planar) order using the embedding."""
    # PlanarEmbedding stores a half-edge linked list; traverse it.
    nbrs = list(embedding.neighbors_cw_order(v))
    return nbrs


# ── main reduction ────────────────────────────────────────────────────────────

def reduce_degree6_to_degree3(G: nx.Graph) -> nx.Graph:
    """
    Given a planar graph G with maximum degree ≤ 6, return a new planar graph
    G' with maximum degree ≤ 3.

    Node labels in G' follow the scheme:
      - Original nodes with degree ≤ 3 keep their label unchanged.
      - Each high-degree original node  v  is replaced by gadget nodes
        labelled  (v, 0), (v, 1), …, (v, k-1)  where k = deg(v).

    An auxiliary dict  `node_map`  is also returned so that you can trace
    which gadget nodes correspond to which original vertex.

    Returns
    -------
    G_prime : nx.Graph
        The reduced planar graph (max degree 3).
    node_map : dict
        { original_node : list_of_gadget_nodes }
        For low-degree nodes the list has a single entry (the node itself).
    """
    if not nx.is_connected(G):
        raise ValueError("Graph must be connected for planar embedding.")

    # ── 1. Compute a combinatorial planar embedding ──────────────────────────
    is_planar, embedding = nx.check_planarity(G, counterexample=False)
    if not is_planar:
        raise ValueError("Input graph is not planar.")

    max_deg = max(d for _, d in G.degree())
    if max_deg > 6:
        raise ValueError(f"Input graph has max degree {max_deg} > 6.")

    # ── 2. Build G' ──────────────────────────────────────────────────────────
    G_prime = nx.Graph()
    node_map: dict = {}          # original v  →  [gadget nodes in cyclic order]

    # Pass 1: add all nodes / gadget nodes
    for v in G.nodes():
        deg = G.degree(v)
        if deg <= 3:
            G_prime.add_node(v, original=v)
            node_map[v] = [v]
        else:
            gadgets = [(v, i) for i in range(deg)]
            for gn in gadgets:
                G_prime.add_node(gn, original=v)
            node_map[v] = gadgets

    # Pass 2: add gadget-cycle edges for high-degree vertices
    for v, gadgets in node_map.items():
        if len(gadgets) > 1:
            k = len(gadgets)
            for i in range(k):
                G_prime.add_edge(gadgets[i], gadgets[(i + 1) % k],
                                 edge_type="gadget_cycle")

    # Pass 3: add edges for original graph edges
    #   For each original edge (u, v) we need to find which gadget node of u
    #   corresponds to the half-edge toward v, and vice-versa.
    #   We use the cyclic neighbour order from the embedding.

    # Pre-compute cyclic neighbour lists
    cyclic_nbrs: dict = {}
    for v in G.nodes():
        cyclic_nbrs[v] = _cyclic_neighbours(G, v, embedding)

    added_edges = set()

    for u, v in G.edges():
        edge_id = frozenset([u, v])
        if edge_id in added_edges:
            continue
        added_edges.add(edge_id)

        # Find the position of v in u's cyclic list  →  gadget index for u
        nbrs_u = cyclic_nbrs[u]
        idx_u = nbrs_u.index(v)
        gu = node_map[u][idx_u] if len(node_map[u]) > 1 else node_map[u][0]

        # Find the position of u in v's cyclic list  →  gadget index for v
        nbrs_v = cyclic_nbrs[v]
        idx_v = nbrs_v.index(u)
        gv = node_map[v][idx_v] if len(node_map[v]) > 1 else node_map[v][0]

        G_prime.add_edge(gu, gv, edge_type="original")

    return G_prime, node_map


# ── verification ──────────────────────────────────────────────────────────────

def verify_reduction(G_original: nx.Graph, G_prime: nx.Graph) -> dict:
    """Check the key properties that must hold after the reduction."""
    results = {}

    # 1. Max degree ≤ 3
    max_deg = max(d for _, d in G_prime.degree())
    results["max_degree"] = max_deg
    results["degree_ok"] = max_deg <= 3

    # 2. Planarity
    is_planar, _ = nx.check_planarity(G_prime)
    results["is_planar"] = is_planar

    # 3. Node / edge counts
    results["original_nodes"] = G_original.number_of_nodes()
    results["original_edges"] = G_original.number_of_edges()
    results["reduced_nodes"] = G_prime.number_of_nodes()
    results["reduced_edges"] = G_prime.number_of_edges()

    # 4. Connectivity preserved
    results["connected"] = nx.is_connected(G_prime)

    return results


# ── demo ──────────────────────────────────────────────────────────────────────

def _demo():
    """Build a small degree-6 planar graph and run the reduction."""
    # Wheel graph W_6: centre has degree 6, rim nodes degree 3.
    W = nx.wheel_graph(7)   # nodes 0..6, node 0 is the hub (degree 6)

    print("=== Input graph ===")
    print(f"  Nodes: {W.number_of_nodes()},  Edges: {W.number_of_edges()}")
    print(f"  Degrees: { {v: d for v, d in W.degree()} }")
    print(f"  Max degree: {max(d for _, d in W.degree())}")
    is_planar, _ = nx.check_planarity(W)
    print(f"  Planar: {is_planar}")

    G_prime, node_map = reduce_degree6_to_degree3(W)

    print("\n=== Reduced graph ===")
    stats = verify_reduction(W, G_prime)
    for k, val in stats.items():
        print(f"  {k}: {val}")

    print("\n=== Node map (hub vertex 0) ===")
    print(f"  Original node 0 (deg 6) → gadget nodes: {node_map[0]}")

    # Optional: draw if matplotlib is available
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Original
        pos_orig = nx.planar_layout(W)
        nx.draw(W, pos=pos_orig, ax=axes[0], with_labels=True,
                node_color="skyblue", node_size=600, font_size=9)
        axes[0].set_title(f"Original (max deg {max(d for _,d in W.degree())})")

        # Reduced
        pos_red = nx.planar_layout(G_prime)
        edge_colors = [
            "red" if G_prime[u][v].get("edge_type") == "gadget_cycle" else "black"
            for u, v in G_prime.edges()
        ]
        labels = {
            n: f"{n[0]}_{n[1]}" if isinstance(n, tuple) else str(n)
            for n in G_prime.nodes()
        }
        nx.draw(G_prime, pos=pos_red, ax=axes[1], labels=labels,
                edge_color=edge_colors, node_color="lightgreen",
                node_size=500, font_size=7)
        axes[1].set_title(f"Reduced (max deg {stats['max_degree']}) — red=gadget cycle")

        plt.tight_layout()
        plt.savefig("/mnt/user-data/outputs/degree_reduction_demo.png", dpi=150)
        print("\nPlot saved to degree_reduction_demo.png")
    except ImportError:
        print("\n(matplotlib not available – skipping plot)")


if __name__ == "__main__":
    _demo()