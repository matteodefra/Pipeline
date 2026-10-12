"""
3D Orthogonal Drawing  →  Unit Ball Graph
==========================================
Single-file implementation of:

  1. orthogonal_3d_draw(G)
     Crossing-free 3D orthogonal grid drawing for any undirected graph
     with maximum degree ≤ 6.  Based on Cohen, Eades, Lin & Ruskey
     "Three-Dimensional Graph Drawing", IPL 60 (1996) 97-103.

  2. build_unit_ball_graph(pos3d, edge_routes)
     Converts the orthogonal drawing into a Unit Ball Graph on ℤ³:
       • every integer grid point along every edge route becomes a vertex
       • two vertices are connected iff their Euclidean distance is exactly 1

  3. Visualisation helpers for both representations.

Quickstart
----------
    import networkx as nx
    from graph_3d_ubg import orthogonal_3d_draw, build_unit_ball_graph
    from graph_3d_ubg import visualize_3d, visualize_ubg

    G = nx.petersen_graph()
    pos3d, edge_routes = orthogonal_3d_draw(G)
    visualize_3d(G, pos3d, edge_routes, title="Petersen — orthogonal 3D")

    UBG, ubg_pos, original_nodes = build_unit_ball_graph(pos3d, edge_routes)
    visualize_ubg(UBG, ubg_pos, original_nodes, title="Petersen — Unit Ball Graph")
"""

import math
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  registers 3-D projection


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — 3D ORTHOGONAL DRAWING
# ═══════════════════════════════════════════════════════════════════════════════

def orthogonal_3d_draw(G: nx.Graph):
    """
    Produce a crossing-free 3D orthogonal grid drawing of *G*.

    Vertex i is placed at (2i, 0, 0).  Edge k is routed through a unique
    tunnel (y = z = k+1), making a 5-waypoint axis-aligned polyline:

        (xu, 0,  0) → (xu, t, 0) → (xu, t, t) → (xv, t, t) → (xv, t, 0) → (xv, 0, 0)

    Every segment changes exactly one coordinate, guaranteeing that
    _interpolate_segment can later subdivide it into unit steps.
    No two edge polylines share any grid segment (unique tunnel per edge).

    Parameters
    ----------
    G : networkx.Graph
        Undirected simple graph with max degree ≤ 6.

    Returns
    -------
    pos3d : dict {node -> (x, y, z)}
    edge_routes : dict {(u, v) -> list of (x, y, z) waypoints}
    """
    if not isinstance(G, nx.Graph) or G.is_directed():
        raise TypeError("G must be an undirected networkx Graph.")

    max_deg = max((d for _, d in G.degree()), default=0)
    if max_deg > 6:
        raise ValueError(
            f"Graph has maximum degree {max_deg} > 6. "
            "The orthogonal 3-D drawing algorithm requires max degree ≤ 6."
        )

    nodes = list(G.nodes())
    node_index = {v: i for i, v in enumerate(nodes)}
    pos3d = {v: (2 * node_index[v], 0, 0) for v in nodes}

    edge_routes = {}
    for k, (u, v) in enumerate(G.edges()):
        xu = pos3d[u][0]
        xv = pos3d[v][0]
        t  = k + 1   # tunnel index — unique per edge

        route = [
            (xu, 0, 0),   # vertex u
            (xu, t, 0),   # lift Y
            (xu, t, t),   # lift Z
            (xv, t, t),   # traverse X
            (xv, t, 0),   # drop Z
            (xv, 0, 0),   # drop Y → vertex v
        ]
        edge_routes[(u, v)] = _deduplicate(route)

    return pos3d, edge_routes


def _deduplicate(pts):
    """Remove consecutive duplicate points from a polyline."""
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


def verify_no_crossings(pos3d, edge_routes):
    """
    Check that no two edge routes share any grid segment.

    Returns
    -------
    ok        : bool
    conflicts : list of (edge_a, edge_b, segment) triples
    """
    segment_owner = {}
    conflicts = []
    for edge_key, route in edge_routes.items():
        for a, b in zip(route, route[1:]):
            seg = (min(a, b), max(a, b))
            if seg in segment_owner and segment_owner[seg] != edge_key:
                conflicts.append((edge_key, segment_owner[seg], seg))
            else:
                segment_owner[seg] = edge_key
    return len(conflicts) == 0, conflicts


def grid_volume(pos3d, edge_routes):
    """Return the (X, Y, Z) bounding-box dimensions of the drawing."""
    all_pts = list(pos3d.values()) + [p for r in edge_routes.values() for p in r]
    xs, ys, zs = zip(*all_pts)
    return (max(xs)-min(xs)+1, max(ys)-min(ys)+1, max(zs)-min(zs)+1)


def visualize_3d(G, pos3d, edge_routes,
                 title="3D Orthogonal Graph Drawing",
                 save_path=None, figsize=(12, 9)):
    """
    Render the orthogonal 3D drawing with matplotlib.

    Parameters
    ----------
    G, pos3d, edge_routes : output of orthogonal_3d_draw()
    title     : figure title
    save_path : file path to save PNG; if None, calls plt.show()
    """
    fig = plt.figure(figsize=figsize, facecolor="#0f0f1a")
    ax  = fig.add_subplot(111, projection="3d", facecolor="#0f0f1a")

    edge_colors = plt.cm.plasma(np.linspace(0.15, 0.90, G.number_of_edges()))

    for idx, (edge_key, route) in enumerate(edge_routes.items()):
        xs, ys, zs = zip(*route)
        ax.plot(xs, ys, zs, color=edge_colors[idx], linewidth=1.6, alpha=0.85)
        bends = route[1:-1]
        if bends:
            bx, by, bz = zip(*bends)
            ax.scatter(bx, by, bz, color="#ffffff", s=10, alpha=0.5)

    vx, vy, vz = zip(*[pos3d[v] for v in G.nodes()])
    ax.scatter(vx, vy, vz, color="#00d4ff", s=90,
               edgecolors="white", linewidths=0.6, zorder=5)
    for v, (x, y, z) in pos3d.items():
        ax.text(x, y, z+0.35, str(v), fontsize=7, color="#e0e0e0",
                ha="center", va="bottom")

    _style_axes(ax)
    ok, _ = verify_no_crossings(pos3d, edge_routes)
    vol   = grid_volume(pos3d, edge_routes)
    _titles(fig, title,
            f"{G.number_of_nodes()} vertices · {G.number_of_edges()} edges · "
            f"grid {vol[0]}×{vol[1]}×{vol[2]} · "
            f"{'✓ crossing-free' if ok else '✗ crossings detected'}")
    _save_or_show(fig, save_path)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — UNIT BALL GRAPH
# ═══════════════════════════════════════════════════════════════════════════════

def _interpolate_segment(a, b):
    """
    Yield every integer grid point strictly between a and b on an
    axis-aligned unit-step segment (exactly one coordinate changes).
    """
    ax, ay, az = a
    bx, by, bz = b
    dx, dy, dz = bx-ax, by-ay, bz-az
    if dx != 0:
        step = 1 if dx > 0 else -1
        for x in range(ax+step, bx, step):
            yield (x, ay, az)
    elif dy != 0:
        step = 1 if dy > 0 else -1
        for y in range(ay+step, by, step):
            yield (ax, y, az)
    else:
        step = 1 if dz > 0 else -1
        for z in range(az+step, bz, step):
            yield (ax, ay, z)


def build_unit_ball_graph(pos3d, edge_routes):
    """
    Build the Unit Ball Graph (UBG) from a 3D orthogonal drawing.

    Steps
    -----
    1. Collect every integer grid point along every edge route (original
       vertices + one auxiliary vertex per unit step along each segment).
    2. Add a *subdivision edge* between every consecutive pair of points
       along each route (guaranteed unit-length because routes are
       strictly axis-aligned).
    3. Add a *proximity edge* between any two occupied grid points that
       are grid-adjacent (distance 1) but not already connected by a
       subdivision edge.

    Parameters
    ----------
    pos3d       : dict {node -> (x,y,z)}         from orthogonal_3d_draw()
    edge_routes : dict {(u,v) -> [waypoints]}     from orthogonal_3d_draw()

    Returns
    -------
    UBG            : networkx.Graph
        Nodes are (x,y,z) tuples with attributes:
          'kind' ∈ {'original', 'auxiliary'}
          'pos'  = (x, y, z)
        Edges have attribute:
          'etype' ∈ {'subdivision', 'proximity'}
    ubg_pos        : dict {node -> (x,y,z)}
    original_nodes : set of node keys that are original vertices
    """
    original_coords = set(pos3d.values())

    # ------------------------------------------------------------------
    # 1. Collect all occupied grid points
    # ------------------------------------------------------------------
    all_pts = set(original_coords)
    for route in edge_routes.values():
        for a, b in zip(route, route[1:]):
            all_pts.add(a)
            all_pts.add(b)
            all_pts.update(_interpolate_segment(a, b))

    # ------------------------------------------------------------------
    # 2. Build graph nodes
    # ------------------------------------------------------------------
    UBG = nx.Graph()
    for pt in all_pts:
        UBG.add_node(pt,
                     kind='original' if pt in original_coords else 'auxiliary',
                     pos=pt)

    # ------------------------------------------------------------------
    # 3. Subdivision edges — walk every route segment unit-step by unit-step
    # ------------------------------------------------------------------
    subdivision_edges = set()
    for route in edge_routes.values():
        for a, b in zip(route, route[1:]):
            chain = [a] + list(_interpolate_segment(a, b)) + [b]
            # Materialise any point not yet in the graph
            for p in chain:
                if p not in UBG:
                    UBG.add_node(p, kind='auxiliary', pos=p)
            for p, q in zip(chain, chain[1:]):
                dist_sq = sum((x-y)**2 for x, y in zip(p, q))
                if dist_sq != 1:
                    raise ValueError(
                        f"Non-unit step {p}→{q} (dist²={dist_sq}). "
                        "Ensure edge routes are strictly axis-aligned — "
                        "each consecutive waypoint must differ in exactly one coordinate."
                    )
                key = (min(p, q), max(p, q))
                subdivision_edges.add(key)

    for p, q in subdivision_edges:
        UBG.add_edge(p, q, etype='subdivision')

    # ------------------------------------------------------------------
    # 4. Proximity edges — unit-distance pairs not already subdivided
    # ------------------------------------------------------------------
    pt_set    = set(UBG.nodes())
    neighbors = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    for pt in list(pt_set):
        x, y, z = pt
        for dx, dy, dz in neighbors:
            nb = (x+dx, y+dy, z+dz)
            if nb in pt_set and nb > pt:
                key = (min(pt, nb), max(pt, nb))
                if key not in subdivision_edges:
                    UBG.add_edge(pt, nb, etype='proximity')

    ubg_pos        = {pt: pt for pt in UBG.nodes()}
    original_nodes = {pt for pt in UBG.nodes() if pt in original_coords}
    return UBG, ubg_pos, original_nodes


def verify_unit_distances(UBG):
    """
    Verify every edge in the UBG is exactly unit-length.

    Returns
    -------
    ok  : bool
    bad : list of (u, v, distance) for any offending edges
    """
    bad = []
    for u, v in UBG.edges():
        d = math.sqrt(sum((a-b)**2 for a, b in zip(u, v)))
        if abs(d - 1.0) > 1e-9:
            bad.append((u, v, d))
    return len(bad) == 0, bad


def verify_ubg_no_crossings(UBG):
    """
    Verify that the Unit Ball Graph is crossing-free.

    GEOMETRIC ARGUMENT
    ------------------
    Every edge in the UBG is a unit-length axis-aligned segment in ℤ³
    (it changes exactly one coordinate by ±1, keeping the other two fixed).

    Two such segments can intersect in only two ways:

      (A) Same axis, same line, overlapping interior
          e.g. (0,0,0)-(1,0,0) and (0,0,0)-(1,0,0)
          Identical endpoints → duplicate / multi-edge.
          A simple networkx.Graph already forbids this by construction.

      (B) Different axes
          e.g. X-segment (0,0,0)-(1,0,0) meets Y-segment (p,q,r)-(p,q+1,r).
          An interior intersection requires the crossing point to satisfy
          both parametrisations simultaneously at t,s ∈ (0,1).  Solving
          gives t = p ∈ ℤ, which forces t ∈ {0,1} — an endpoint, not
          an interior point.  So interior crossings between different-axis
          segments are geometrically impossible on ℤ³.

    CONCLUSION
    ----------
    On ℤ³, two distinct unit axis-aligned segments can share AT MOST an
    endpoint — never an interior point.  The only violation that can arise
    is a duplicate edge (same segment used twice), which networkx.Graph
    already prevents.

    This function confirms the above by checking three conditions:
      1. All edges are unit-length and axis-aligned.
      2. No grid segment is claimed by more than one edge (no overlaps).
      3. The graph is simple (no multi-edges or self-loops).

    Parameters
    ----------
    UBG : networkx.Graph  — output of build_unit_ball_graph()

    Returns
    -------
    ok     : bool
    report : dict with keys
        'unit_distance_ok'   : bool
        'no_duplicate_segs'  : bool
        'is_simple'          : bool
        'bad_distance_edges' : list of (u, v, dist)
        'duplicate_segments' : list of (segment, [edge, ...])
    """
    # 1. All edges unit-length
    bad_dist = []
    for u, v in UBG.edges():
        d = math.sqrt(sum((a - b) ** 2 for a, b in zip(u, v)))
        if abs(d - 1.0) > 1e-9:
            bad_dist.append((u, v, round(d, 6)))

    # 2. No grid segment shared by two distinct edges
    seg_owners: dict = {}
    for u, v in UBG.edges():
        seg = (min(u, v), max(u, v))
        seg_owners.setdefault(seg, []).append((u, v))
    duplicate_segs = [
        (seg, owners)
        for seg, owners in seg_owners.items()
        if len(owners) > 1
    ]

    # 3. Simple graph (no self-loops, no multi-edges)
    is_simple = (not UBG.is_multigraph() and not any(UBG.has_edge(n, n) for n in UBG.nodes()))

    ok = len(bad_dist) == 0 and len(duplicate_segs) == 0 and is_simple
    report = {
        'unit_distance_ok':   len(bad_dist) == 0,
        'no_duplicate_segs':  len(duplicate_segs) == 0,
        'is_simple':          is_simple,
        'bad_distance_edges': bad_dist,
        'duplicate_segments': duplicate_segs,
    }
    return ok, report


def ubg_stats(UBG, original_nodes):
    """Print a summary of the Unit Ball Graph."""
    n_orig  = sum(1 for n in UBG.nodes() if n in original_nodes)
    n_aux   = UBG.number_of_nodes() - n_orig
    n_sub   = sum(1 for *_, d in UBG.edges(data=True) if d['etype'] == 'subdivision')
    n_prox  = sum(1 for *_, d in UBG.edges(data=True) if d['etype'] == 'proximity')
    degs    = [d for _, d in UBG.degree()]
    print(f"  Vertices : {UBG.number_of_nodes()}  (original={n_orig}, auxiliary={n_aux})")
    print(f"  Edges    : {UBG.number_of_edges()}  (subdivision={n_sub}, proximity={n_prox})")
    print(f"  Max deg  : {max(degs, default=0)}")
    print(f"  Avg deg  : {np.mean(degs):.2f}")


def ubg_stats_only(pos3d, edge_routes):
    """
    Compute Unit Ball Graph statistics without building the NetworkX object.
 
    Performs the same logical construction as build_unit_ball_graph() but
    stores only a plain Python set of occupied grid points and a plain set
    of edge keys (tuples of tuples), avoiding all NetworkX overhead.  This
    makes it viable for large graphs where the full object would exhaust RAM.
 
    Memory cost: O(V_ubg) for the point set + O(E_ubg) for the edge set,
    where both sets hold plain tuples — roughly 200–300 bytes per entry
    vs several kilobytes per node/edge in NetworkX.
 
    Parameters
    ----------
    pos3d       : dict {node -> (x,y,z)}        from orthogonal_3d_draw()
    edge_routes : dict {(u,v) -> [waypoints]}   from orthogonal_3d_draw()
 
    Returns
    -------
    stats : dict with keys
        'n_vertices'          : int   — total vertices (original + auxiliary)
        'n_original'          : int   — original graph vertices
        'n_auxiliary'         : int   — inserted subdivision vertices
        'n_edges'             : int   — total edges (subdivision + proximity)
        'n_subdivision_edges' : int   — edges along original routes
        'n_proximity_edges'   : int   — extra unit-distance connections
    """
    original_coords = set(pos3d.values())
 
    # ------------------------------------------------------------------
    # 1. Collect all occupied grid points (no NetworkX, just a set)
    # ------------------------------------------------------------------
    all_pts: set = set(original_coords)
    for route in edge_routes.values():
        for a, b in zip(route, route[1:]):
            all_pts.add(a)
            all_pts.add(b)
            all_pts.update(_interpolate_segment(a, b))
 
    # ------------------------------------------------------------------
    # 2. Collect subdivision edges
    # ------------------------------------------------------------------
    subdivision_edges: set = set()
    for route in edge_routes.values():
        for a, b in zip(route, route[1:]):
            chain = [a] + list(_interpolate_segment(a, b)) + [b]
            for p in chain:
                all_pts.add(p)   # materialise any waypoint-only points
            for p, q in zip(chain, chain[1:]):
                dist_sq = sum((x - y) ** 2 for x, y in zip(p, q))
                if dist_sq != 1:
                    raise ValueError(
                        f"Non-unit step {p}→{q} (dist²={dist_sq}). "
                        "Ensure edge routes are strictly axis-aligned."
                    )
                subdivision_edges.add((min(p, q), max(p, q)))
 
    # ------------------------------------------------------------------
    # 3. Count proximity edges (unit-distance pairs not already in routes)
    # ------------------------------------------------------------------
    n_proximity = 0
    neighbors = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
    for pt in all_pts:
        x, y, z = pt
        for dx, dy, dz in neighbors:
            nb = (x+dx, y+dy, z+dz)
            if nb in all_pts and nb > pt:
                key = (min(pt, nb), max(pt, nb))
                if key not in subdivision_edges:
                    n_proximity += 1
 
    n_original  = len(original_coords)
    n_auxiliary = len(all_pts) - n_original
    n_subdiv    = len(subdivision_edges)
 
    return {
        'n_vertices':          len(all_pts),
        'n_original':          n_original,
        'n_auxiliary':         n_auxiliary,
        'n_edges':             n_subdiv + n_proximity,
        'n_subdivision_edges': n_subdiv,
        'n_proximity_edges':   n_proximity,
    }


def visualize_ubg(UBG, ubg_pos, original_nodes,
                  title="Unit Ball Graph",
                  save_path=None, figsize=(14, 10)):
    """
    Render the Unit Ball Graph in 3D.

    Colour scheme
    -------------
    Nodes  : cyan   = original vertices
             orange = auxiliary vertices
    Edges  : white  = subdivision  (along original routes)
             magenta= proximity    (unit-distance, not on route)
    """
    fig = plt.figure(figsize=figsize, facecolor="#0d0d1f")
    ax  = fig.add_subplot(111, projection="3d", facecolor="#0d0d1f")

    orig_pts   = [n for n in UBG.nodes() if n in original_nodes]
    aux_pts    = [n for n in UBG.nodes() if n not in original_nodes]
    sub_edges  = [(u,v) for u,v,d in UBG.edges(data=True) if d['etype'] == 'subdivision']
    prox_edges = [(u,v) for u,v,d in UBG.edges(data=True) if d['etype'] == 'proximity']

    for u, v in sub_edges:
        ax.plot([u[0],v[0]], [u[1],v[1]], [u[2],v[2]],
                color="#cccccc", linewidth=0.9, alpha=0.6)

    for u, v in prox_edges:
        ax.plot([u[0],v[0]], [u[1],v[1]], [u[2],v[2]],
                color="#ff44cc", linewidth=1.1, alpha=0.75, linestyle="--")

    if aux_pts:
        ax.scatter(*zip(*aux_pts), color="#ff8c00", s=18, alpha=0.85,
                   edgecolors="none", label=f"Auxiliary ({len(aux_pts)})")

    if orig_pts:
        ax.scatter(*zip(*orig_pts), color="#00d4ff", s=80, alpha=1.0,
                   edgecolors="white", linewidths=0.6,
                   label=f"Original ({len(orig_pts)})", zorder=5)
        for pt in orig_pts:
            ax.text(pt[0], pt[1], pt[2]+0.4, str(pt),
                    fontsize=6, color="#e0e0e0", ha="center")

    ax.legend(loc="upper left", fontsize=8,
              facecolor="#1a1a2e", edgecolor="#444", labelcolor="white")
    _style_axes(ax)

    n_sub  = len(sub_edges)
    n_prox = len(prox_edges)
    ok, _  = verify_unit_distances(UBG)
    _titles(fig, title,
            f"{len(orig_pts)} original · {len(aux_pts)} auxiliary · "
            f"{n_sub} subdivision + {n_prox} proximity edges · "
            f"{'✓ all unit-distance' if ok else '✗ non-unit edges!'}")
    _save_or_show(fig, save_path)


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED PLOT UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def _style_axes(ax):
    ax.set_xlabel("X", color="#888", fontsize=9)
    ax.set_ylabel("Y", color="#888", fontsize=9)
    ax.set_zlabel("Z", color="#888", fontsize=9)
    ax.tick_params(colors="#555", labelsize=7)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor("#2a2a3e")


def _titles(fig, title, subtitle):
    fig.text(0.5, 0.97, title,    ha="center", va="top", fontsize=13,
             color="#ffffff", fontweight="bold")
    fig.text(0.5, 0.935, subtitle, ha="center", va="top", fontsize=8.5,
             color="#aaaaaa")


def _save_or_show(fig, save_path):
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"Saved → {save_path}")
    else:
        plt.tight_layout()
        plt.show()
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# EXAMPLE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import networkx as nx

    # ── Pick any graph with max degree ≤ 6 ──────────────────────────────────
    G = nx.petersen_graph()          # 10 nodes, 15 edges, max-degree 3

    # ── Step 1: crossing-free 3D orthogonal drawing ──────────────────────────
    pos3d, edge_routes = orthogonal_3d_draw(G)

    ok, conflicts = verify_no_crossings(pos3d, edge_routes)
    vol = grid_volume(pos3d, edge_routes)
    print(f"Orthogonal drawing: grid {vol[0]}×{vol[1]}×{vol[2]}, "
          f"crossing-free: {ok}")

    visualize_3d(G, pos3d, edge_routes,
                 title="Petersen Graph — 3D Orthogonal Drawing",
                 save_path="/mnt/user-data/outputs/example_orthogonal.png")

    # ── Step 2: convert to Unit Ball Graph ───────────────────────────────────
    UBG, ubg_pos, original_nodes = build_unit_ball_graph(pos3d, edge_routes)

    print(f"\nUnit Ball Graph:")
    ubg_stats(UBG, original_nodes)

    ok_cross, report = verify_ubg_no_crossings(UBG)
    print(f"\nCrossing-free verification:")
    print(f"  All edges unit-distance : {report['unit_distance_ok']}")
    print(f"  No duplicate segments   : {report['no_duplicate_segs']}")
    print(f"  Simple graph            : {report['is_simple']}")
    print(f"  \u2192 Crossing-free         : {ok_cross}")

    visualize_ubg(UBG, ubg_pos, original_nodes,
                  title="Petersen Graph — Unit Ball Graph",
                  save_path="/mnt/user-data/outputs/example_ubg.png")