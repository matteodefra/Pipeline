import networkx as nx
import itertools

def is_vertex_cover(G, cover):
    """Checks if a set of nodes covers all edges."""
    for u, v in G.edges():
        if u not in cover and v not in cover:
            return False
    return True

def find_exact_vc(G, k):
    """Finds a vertex cover of size >= k using recursion."""
    n = G.number_of_nodes()
    # Try all combinations of size up to k
    for size in range(k, n):
        for combo in itertools.combinations(G.nodes(), size):
            if is_vertex_cover(G, set(combo)):
                return set(combo)
    return G.nodes()