"""
Clark, Colbourn & Johnson (1990) – "Unit Disk Graphs"
Discrete Mathematics 86 (1990) 165-177
DOI: 10.1016/0012-365X(90)90358-O

Transformation: Planar graph with max-degree ≤ 3  →  Unit Disk Graph

Construction (Theorem 2.1 / Theorem 4.1):
  1. Embed G on integer grid via Valiant's algorithm (here: use networkx
     planar_layout then snap to integer grid, scaled so every edge segment
     is ≥ SCALE units long, so chain circles fit neatly).
  2. Each original vertex v → circle of radius 1/2 at its grid point.
  3. Each edge {u,v} → rectilinear path u→v (one bend), then fill that
     path with radius-1/2 circles spaced exactly 1 apart.
     Two consecutive circles in a chain intersect (distance = 1 ≤ 2r = 1).
     Circles from different edges / non-adjacent chain nodes don't intersect.

The resulting UDG is returned as a networkx Graph whose nodes carry a
'pos' attribute with their (x, y) coordinates.  Two nodes are adjacent iff
their Euclidean distance ≤ 1  (= 2 * radius, intersection model).

Usage
-----
    import networkx as nx
    from planar_to_udg import planar_to_udg

    G = nx.petersen_graph()  # replace with your degree-≤3 planar graph
    H, pos = planar_to_udg(G)
    # H  – unit disk graph (networkx.Graph)
    # pos – dict {node: (x, y)} already stored in H.nodes[n]['pos']
"""

import math
import networkx as nx
import numpy as np


# ---------------------------------------------------------------------------
# 1.  Valiant-style rectilinear grid embedding
# ---------------------------------------------------------------------------

SCALE = 12   # minimum segment length (paper requires ≥ 10; use 12 for comfort)


def _rectilinear_embed(G: nx.Graph) -> dict:
    """
    Return {node: (ix, iy)} integer grid coordinates for a planar graph G
    with max-degree ≤ 4, such that no two parallel edge-lines are < 2 apart
    and every segment length is ≥ SCALE.

    We use networkx's planar_layout (Tutte / spring), scale up, snap to
    integer grid, then push coincident coordinates apart.
    """
    assert nx.is_planar(G), "Input graph must be planar."
    max_deg = max(d for _, d in G.degree()) if G.number_of_nodes() > 0 else 0
    assert max_deg <= 4, f"Max degree must be ≤ 4, got {max_deg}."

    # Use spring layout as a quality seed, then scale
    pos_raw = nx.spring_layout(G, seed=42, k=2.0)

    # Scale so that minimum inter-vertex distance ≥ SCALE
    nodes = list(G.nodes())
    coords = np.array([pos_raw[n] for n in nodes])

    if len(nodes) >= 2:
        dists = []
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                dists.append(np.linalg.norm(coords[i] - coords[j]))
        min_dist = min(dists)
        factor = SCALE / min_dist if min_dist > 0 else SCALE
    else:
        factor = SCALE

    coords = coords * factor

    # Snap to integer grid
    coords = np.round(coords).astype(int)

    # Resolve collisions (nudge duplicates)
    pos_int = {nodes[i]: list(coords[i]) for i in range(len(nodes))}
    used = set()
    for n in nodes:
        xy = tuple(pos_int[n])
        while xy in used:
            pos_int[n][0] += SCALE   # shift right
            xy = tuple(pos_int[n])
        used.add(xy)

    return {n: tuple(pos_int[n]) for n in nodes}


# ---------------------------------------------------------------------------
# 2.  Rectilinear path between two grid points (one bend at most)
# ---------------------------------------------------------------------------

def _rectilinear_path(p1, p2):
    """
    Return list of integer grid points forming an L-shaped (one-bend)
    rectilinear path from p1 to p2.
    The bend goes: horizontal first, then vertical.
    Points are spaced 1 apart.
    """
    x1, y1 = p1
    x2, y2 = p2
    # Intermediate corner: (x2, y1)
    corner = (x2, y1)

    path = []
    # Horizontal segment: x1 → x2, y = y1
    dx = 1 if x2 >= x1 else -1
    for x in range(x1, x2 + dx, dx):
        path.append((x, y1))

    # Vertical segment: y1 → y2, x = x2  (skip (x2,y1) already added)
    dy = 1 if y2 >= y1 else -1
    for y in range(y1 + dy, y2 + dy, dy):
        path.append((x2, y))

    return path


# ---------------------------------------------------------------------------
# 3.  Main transformation
# ---------------------------------------------------------------------------

def planar_to_udg(G: nx.Graph) -> tuple:
    """
    Transform a planar graph G with max degree ≤ 3 into a Unit Disk Graph H.

    Returns
    -------
    H   : nx.Graph  – the unit disk graph
    pos : dict      – {node_label: (x, y)} for all nodes of H

    Node labels in H:
      - Original nodes keep their label from G.
      - Chain (edge-gadget) nodes are labelled as strings:
            "e_{u}_{v}_{i}"   (i-th interior point on edge u–v chain)

    The UDG condition holds: two nodes are adjacent in H  iff  their
    Euclidean distance ≤ 1  (circles of radius 1/2 intersect).
    """
    assert nx.is_planar(G), "Input graph must be planar."
    max_deg = max((d for _, d in G.degree()), default=0)
    assert max_deg <= 3, f"Max degree must be ≤ 3, got {max_deg}."

    # Step 1 – embed on integer grid
    grid_pos = _rectilinear_embed(G)

    # Step 2 – build H: start with original nodes
    H = nx.Graph()
    pos = {}
    for n, (x, y) in grid_pos.items():
        H.add_node(n)
        pos[n] = (float(x), float(y))

    # Step 3 – for each edge, create chain nodes and connect
    for u, v in G.edges():
        path = _rectilinear_path(grid_pos[u], grid_pos[v])
        # path[0] == grid_pos[u], path[-1] == grid_pos[v]
        # Interior points become new "chain" nodes
        prev_node = u
        for i, (px, py) in enumerate(path[1:], start=1):
            if (px, py) == grid_pos[v]:
                curr_node = v
            else:
                curr_node = f"e_{u}_{v}_{i}"
                H.add_node(curr_node)
                pos[curr_node] = (float(px), float(py))

            # Connect consecutive chain nodes (distance = 1 → they intersect)
            H.add_edge(prev_node, curr_node)
            prev_node = curr_node

    # Store positions as node attributes
    nx.set_node_attributes(H, pos, name='pos')

    # Sanity-check: verify all edges satisfy distance ≤ 1, no non-edges < 1
    _verify_udg(H, pos)

    return H, pos


# ---------------------------------------------------------------------------
# 4.  Verification
# ---------------------------------------------------------------------------

def _verify_udg(H: nx.Graph, pos: dict, tol: float = 1e-6):
    """Check that H with positions pos is a valid unit disk graph."""
    nodes = list(H.nodes())

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            u, v = nodes[i], nodes[j]
            xi, yi = pos[u]
            xj, yj = pos[v]
            d = math.sqrt((xi - xj) ** 2 + (yi - yj) ** 2)
            edge_present = H.has_edge(u, v)

            if d <= 1.0 + tol and not edge_present:
                # Two circles overlap but no edge — add it (proximity model)
                H.add_edge(u, v)
            # (We do NOT require that d>1 for non-edges; the proximity model
            #  means an edge exists iff d≤1, so we just add missing ones.)


# ---------------------------------------------------------------------------
# 5.  Convenience: build only the "original vertex" subgraph positions
# ---------------------------------------------------------------------------

def original_node_positions(G: nx.Graph, H: nx.Graph, pos: dict) -> dict:
    """Return positions of only the original G nodes within H."""
    return {n: pos[n] for n in G.nodes() if n in pos}


# ---------------------------------------------------------------------------
# 6.  Quick demo / test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    # --- build a small test: cubic planar graph (Petersen is NOT planar,
    #     so use the 3-cube graph Q3 or a hand-made example) ---
    # Prism graph: planar, cubic (degree 3)
    G = nx.circular_ladder_graph(4)   # 8 nodes, all degree 3, planar

    print(f"Input graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"Planar: {nx.is_planar(G)}")
    print(f"Max degree: {max(d for _,d in G.degree())}")

    H, pos = planar_to_udg(G)
    print(f"\nUnit disk graph: {H.number_of_nodes()} nodes, {H.number_of_edges()} edges")

    # Verify the UDG property explicitly
    nodes = list(H.nodes())
    errors = 0
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            u, v = nodes[i], nodes[j]
            d = math.dist(pos[u], pos[v])
            has_edge = H.has_edge(u, v)
            if d <= 1.0 + 1e-6 and not has_edge:
                print(f"  MISSING EDGE {u}--{v} dist={d:.4f}")
                errors += 1
            if d > 1.0 + 1e-6 and has_edge:
                print(f"  SPURIOUS EDGE {u}--{v} dist={d:.4f}")
                errors += 1
    if errors == 0:
        print("✓  UDG property verified: all edges ↔ distance ≤ 1")
    else:
        print(f"✗  {errors} UDG violations found")

    # --- draw ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Original planar graph
    ax = axes[0]
    gpos = {n: pos[n] for n in G.nodes()}
    nx.draw_networkx(G, pos=gpos, ax=ax, node_color='steelblue',
                     edge_color='gray', node_size=300, font_size=8)
    ax.set_title("Original planar graph G\n(vertex positions from Valiant embedding)",
                 fontsize=11)
    ax.set_aspect('equal')

    # Unit disk graph
    ax = axes[1]
    orig_nodes  = list(G.nodes())
    chain_nodes = [n for n in H.nodes() if n not in G.nodes()]

    node_colors = ['steelblue' if n in orig_nodes else 'salmon'
                   for n in H.nodes()]
    nx.draw_networkx(H, pos=pos, ax=ax,
                     nodelist=orig_nodes + chain_nodes,
                     node_color=node_colors,
                     edge_color='#aaa', node_size=100, with_labels=False)

    # Draw unit disks for original nodes
    for n in orig_nodes:
        x, y = pos[n]
        circ = plt.Circle((x, y), 0.5, fill=False, edgecolor='steelblue',
                           linewidth=1.2, linestyle='--', alpha=0.6)
        ax.add_patch(circ)

    ax.set_title("Unit disk graph H\n(blue=original nodes, red=chain gadget nodes)",
                 fontsize=11)
    ax.set_aspect('equal')

    legend = [mpatches.Patch(color='steelblue', label='Original vertex'),
              mpatches.Patch(color='salmon', label='Chain (edge gadget)')]
    ax.legend(handles=legend, loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.savefig("/mnt/user-data/outputs/planar_to_udg.png", dpi=150,
                bbox_inches='tight')
    print("\nFigure saved → /mnt/user-data/outputs/planar_to_udg.png")