from __future__ import annotations

from collections import Counter

import networkx as nx


def graph_statistics(graph: nx.Graph) -> dict:
    edge_kinds = Counter(data.get("kind", "unknown") for _, _, data in graph.edges(data=True))
    node_kinds = Counter(data.get("kind", "unknown") for _, data in graph.nodes(data=True))
    degree_counts = Counter(dict(graph.degree()).values())
    triangles = sum(nx.triangles(graph).values()) // 3
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "max_degree": max(dict(graph.degree()).values(), default=0),
        "node_kinds": dict(node_kinds),
        "edge_kinds": dict(edge_kinds),
        "degree_counts": dict(sorted(degree_counts.items())),
        "triangles": triangles,
        "target_alpha": graph.graph.get("target_alpha"),
        "occurrence_order": graph.graph.get("occurrence_order"),
    }
