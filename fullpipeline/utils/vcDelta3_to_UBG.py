import networkx as nx

def create_3d_ogd_ubg(G, S=3):
    """
    Generates a 3D Orthogonal Grid Drawing suitable for a Unit Ball Graph.
    
    Parameters:
    G (networkx.Graph): Input graph (max degree <= 4).
    S (int): Grid scaling factor. S >= 2 ensures parallel lines don't form UBG edges.
             S=3 is strictly recommended for clearance.
             
    Returns:
    vertex_coords (dict): Coordinates of original nodes {node: (x,y,z)}
    auxiliary_coords (dict): Coordinates of dummy path nodes {aux_node: (x,y,z)}
    new_edges (list): Subdivided path edges [(u, v), ...]
    """
    # Validate degree constraint
    if max(dict(G.degree()).values()) > 4:
        raise ValueError("Graph has a maximum degree > 4. Lemma 2 supports max degree 4.")

    nodes = list(G.nodes())
    node_to_idx = {n: i for i, n in enumerate(nodes)}

    vertex_coords = {}
    auxiliary_coords = {}
    new_edges = []

    # 1. Place vertices on the X-axis, spaced by 4 * S to allow port routing
    for u in nodes:
        idx = node_to_idx[u]
        vertex_coords[u] = (4 * S * idx, 0, 0)

    port_usage = {u: 0 for u in nodes}
    aux_node_counter = 0

    # 2. Route edges
    for k, (u, v) in enumerate(G.edges(), start=1):
        idx_u = node_to_idx[u]
        idx_v = node_to_idx[v]

        # Ensure idx_u < idx_v for consistent X-highway placement
        if idx_u > idx_v:
            u, v = v, u
            idx_u, idx_v = idx_v, idx_u

        # Exclusive Z-plane for this specific edge to avoid 3D crossings
        Z_k = S * k

        def get_port_params(node, idx, port):
            # Returns: (Port_X, Port_Y, Safe_Highway_Y)
            if port == 0:   return 4 * S * idx, S, 3 * S
            elif port == 1: return 4 * S * idx, -S, -3 * S
            elif port == 2: return 4 * S * idx - S, 0, 3 * S
            elif port == 3: return 4 * S * idx + S, 0, 3 * S

        # Assign local ports
        d_u = port_usage[u]
        port_usage[u] += 1
        d_v = port_usage[v]
        port_usage[v] += 1

        X_u, Y_u, Y_safe_u = get_port_params(u, idx_u, d_u)
        X_v, Y_v, Y_safe_v = get_port_params(v, idx_v, d_v)

        # An empty column guaranteed to contain no vertical port segments
        X_hw = 4 * S * idx_u + 2 * S

        # Define the exact orthogonal bends (corners) for this edge
        corners = [
            vertex_coords[u],
            (X_u, Y_u, 0),
            (X_u, Y_u, Z_k),
            (X_u, Y_safe_u, Z_k),
            (X_hw, Y_safe_u, Z_k),
            (X_hw, Y_safe_v, Z_k),
            (X_v, Y_safe_v, Z_k),
            (X_v, Y_v, Z_k),
            (X_v, Y_v, 0),
            vertex_coords[v]
        ]

        # Clean up consecutive duplicates (if a coordinate didn't need to change)
        clean_corners = [corners[0]]
        for c in corners[1:]:
            if c != clean_corners[-1]:
                clean_corners.append(c)

        # 3. Subdivide segments into unit distances (1 unit apart) for the UBG
        prev_node_id = u
        for i in range(len(clean_corners) - 1):
            start = clean_corners[i]
            end = clean_corners[i+1]

            # Calculate orthogonal vector distance
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            dz = end[2] - start[2]
            steps = abs(dx) + abs(dy) + abs(dz)

            step_x = dx // steps if steps > 0 else 0
            step_y = dy // steps if steps > 0 else 0
            step_z = dz // steps if steps > 0 else 0

            # Generate auxiliary nodes along the line segment
            for step in range(1, steps):
                curr = (start[0] + step * step_x,
                        start[1] + step * step_y,
                        start[2] + step * step_z)
                aux_name = f"e{k}_aux_{aux_node_counter}"
                auxiliary_coords[aux_name] = curr
                new_edges.append((prev_node_id, aux_name))
                prev_node_id = aux_name
                aux_node_counter += 1

            # Register the bend/corner itself as an auxiliary node 
            # (unless it's the very last segment connecting directly to v)
            if i < len(clean_corners) - 2:
                aux_name = f"e{k}_aux_{aux_node_counter}"
                auxiliary_coords[aux_name] = end
                new_edges.append((prev_node_id, aux_name))
                prev_node_id = aux_name
                aux_node_counter += 1

        # Final connection to the target vertex
        new_edges.append((prev_node_id, v))

    return vertex_coords, auxiliary_coords, new_edges