"""
Clark, Colbourn & Johnson (1990) – "Unit Disk Graphs"
Discrete Mathematics 86 (1990) 165-177
DOI: 10.1016/0012-365X(90)90358-O

Transformation: Planar GraphData with max-degree ≤ 3  →  Unit Disk Graph stats

Entry-points
------------
  planar_to_udg_stats(graph_data)
      Full pipeline: GraphData → UDG statistics dict, no UDG object built.

  check_and_run(graph_data)
      Convenience wrapper that checks planarity and degree before calling
      planar_to_udg_stats, returning None with a printed warning if the
      graph is not suitable.
"""

import math
import networkx as nx
import numpy as np


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCALE = 12   # minimum segment length (paper requires ≥ 10; 12 for comfort)


# ---------------------------------------------------------------------------
# 1.  Valiant-style rectilinear grid embedding
# ---------------------------------------------------------------------------

def _rectilinear_embed(nodes: list, edges: set) -> dict:
    """
    Return {node: (ix, iy)} integer grid coordinates.

    Builds a temporary nx.Graph only for the layout computation,
    then discards it.
    """
    tmp = nx.Graph()
    tmp.add_nodes_from(nodes)
    tmp.add_edges_from(edges)

    pos_raw = nx.spring_layout(tmp, seed=42, k=2.0)
    coords  = np.array([pos_raw[n] for n in nodes])

    if len(nodes) >= 2:
        dists = [
            np.linalg.norm(coords[i] - coords[j])
            for i in range(len(nodes))
            for j in range(i + 1, len(nodes))
        ]
        min_dist = min(dists)
        factor = SCALE / min_dist if min_dist > 0 else SCALE
    else:
        factor = SCALE

    coords = np.round(coords * factor).astype(int)

    # Resolve grid collisions by nudging duplicates
    pos_int = {nodes[i]: list(coords[i]) for i in range(len(nodes))}
    used = set()
    for n in nodes:
        xy = tuple(pos_int[n])
        while xy in used:
            pos_int[n][0] += SCALE
            xy = tuple(pos_int[n])
        used.add(xy)

    return {n: tuple(pos_int[n]) for n in nodes}


# ---------------------------------------------------------------------------
# 2.  Rectilinear path between two grid points (one bend at most)
# ---------------------------------------------------------------------------

def _rectilinear_path(p1, p2) -> list:
    """
    Return integer grid points of the L-shaped path p1 → p2
    (horizontal first, then vertical), spaced 1 apart.
    """
    x1, y1 = p1
    x2, y2 = p2

    path = []
    dx = 1 if x2 >= x1 else -1
    for x in range(x1, x2 + dx, dx):
        path.append((x, y1))

    dy = 1 if y2 >= y1 else -1
    for y in range(y1 + dy, y2 + dy, dy):
        path.append((x2, y))

    return path


# ---------------------------------------------------------------------------
# 3.  Stats-only UDG construction (no nx.Graph built for the UDG itself)
# ---------------------------------------------------------------------------

def _build_udg_plain(nodes: list, edges: set, grid_pos: dict) -> dict:
    """
    Build the UDG as plain Python dicts/sets and return statistics.

    Tracks:
      - all_pos  : dict {node_label -> (x, y)}   of every UDG point
      - udg_edges: set of canonical edge keys     {(min, max)}

    Then counts proximity edges (distance ≤ 1 pairs not on any chain)
    without constructing a networkx object.
    """
    all_pos   = {n: (float(x), float(y)) for n, (x, y) in grid_pos.items()}
    udg_edges = set()   # canonical (min_label, max_label) — needs care with
                        # mixed str/int labels, so we use a frozenset key

    def ekey(a, b):
        return (a, b) if str(a) <= str(b) else (b, a)

    original_nodes = set(nodes)
    chain_nodes    = set()

    # Walk every original edge → chain
    for u, v in edges:
        path = _rectilinear_path(grid_pos[u], grid_pos[v])

        prev_node = u
        for i, (px, py) in enumerate(path[1:], start=1):
            if (px, py) == grid_pos[v]:
                curr_node = v
            else:
                curr_node = f"e_{u}_{v}_{i}"
                all_pos[curr_node] = (float(px), float(py))
                chain_nodes.add(curr_node)

            udg_edges.add(ekey(prev_node, curr_node))
            prev_node = curr_node

    # Proximity pass: any two points at distance ≤ 1 must be connected
    all_node_list = list(all_pos.keys())
    for i in range(len(all_node_list)):
        for j in range(i + 1, len(all_node_list)):
            a, b = all_node_list[i], all_node_list[j]
            xa, ya = all_pos[a]
            xb, yb = all_pos[b]
            d = math.sqrt((xa - xb) ** 2 + (ya - yb) ** 2)
            if d <= 1.0 + 1e-6:
                udg_edges.add(ekey(a, b))

    n_total    = len(all_pos)
    n_original = len(original_nodes)
    n_chain    = len(chain_nodes)
    n_edges    = len(udg_edges)

    # Count chain (subdivision) vs proximity edges
    # Rebuild chain edge set for the split count
    chain_edge_set = set()
    for u, v in edges:
        path = _rectilinear_path(grid_pos[u], grid_pos[v])
        prev_node = u
        for i, (px, py) in enumerate(path[1:], start=1):
            curr_node = v if (px, py) == grid_pos[v] else f"e_{u}_{v}_{i}"
            chain_edge_set.add(ekey(prev_node, curr_node))
            prev_node = curr_node

    n_chain_edges     = len(chain_edge_set)
    n_proximity_edges = n_edges - n_chain_edges

    return {
        'n_vertices':         n_total,
        'n_original':         n_original,
        'n_chain':            n_chain,
        'n_edges':            n_edges,
        'n_chain_edges':      n_chain_edges,
        'n_proximity_edges':  n_proximity_edges,
    }


# ---------------------------------------------------------------------------
# 4.  Public entry-points
# ---------------------------------------------------------------------------

def planar_to_udg_stats(graph_data) -> dict:
    """
    Compute Unit Disk Graph statistics for a planar GraphData with max degree ≤ 3.

    No UDG object is constructed; all intermediate structures are plain
    Python dicts and sets.

    Parameters
    ----------
    graph_data : GraphData
        Must be planar with max degree ≤ 3.

    Returns
    -------
    dict with keys:
        'n_vertices'        : total UDG vertices (original + chain)
        'n_original'        : original graph vertices
        'n_chain'           : inserted chain (edge-gadget) vertices
        'n_edges'           : total UDG edges
        'n_chain_edges'     : edges along rectilinear chains
        'n_proximity_edges' : extra unit-distance connections
    """
    nodes    = list(graph_data.nodes)
    edges    = graph_data.edges
    grid_pos = _rectilinear_embed(nodes, edges)
    return _build_udg_plain(nodes, edges, grid_pos)


def check_and_run(graph_data) -> dict | None:
    """
    Verify planarity and max-degree ≤ 3, then return UDG stats.

    Returns None (with a printed message) if the graph is not suitable.
    """
    # Degree check (cheap, no networkx needed)
    max_deg = graph_data.max_degree()
    if max_deg > 3:
        print(f"Graph has max degree {max_deg} > 3 — not suitable for this construction.")
        return None

    # Planarity check
    tmp = nx.Graph()
    tmp.add_nodes_from(graph_data.nodes)
    tmp.add_edges_from(graph_data.edges)
    if not nx.is_planar(tmp):
        print("Graph is not planar — use the 3D orthogonal / unit ball graph pipeline instead.")
        return None

    return planar_to_udg_stats(graph_data)


# ---------------------------------------------------------------------------
# 5.  Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from sat3_to_vcDelta3 import (
        count_occurences, create_subgraph_variables,
        create_subgraph_clauses, create_full_graph,
    )

    n, m = 3, 3
    cnf3 = {
        0: [ 1,  2,  3],
        1: [-1,  2, -3],
        2: [ 1, -2,  3],
    }

    occ = count_occurences(cnf3, n, m)
    gd  = create_full_graph(n, cnf3,
              create_subgraph_variables(n, occ),
              create_subgraph_clauses(cnf3, n, m))

    print(f"Input: {gd}")
    stats = check_and_run(gd)   # will warn if non-planar
    if stats:
        for k, v in stats.items():
            print(f"  {k:<22}: {v}")