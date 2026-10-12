from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Iterable

import networkx as nx
import numpy as np

from .qaoa_exact import statevector, term_expectation_from_probabilities


@dataclass(frozen=True)
class P1Breakdown:
    vertex_sum: float
    edge_penalty_sum: float

    @property
    def objective(self) -> float:
        return self.vertex_sum - self.edge_penalty_sum


def radius_one_subgraph(graph: nx.Graph, support: Iterable[Hashable]) -> nx.Graph:
    nodes = set(support)
    for node in tuple(nodes):
        nodes.update(graph.neighbors(node))
    return graph.subgraph(nodes).copy()


def p1_objective(
    graph: nx.Graph,
    gamma: float,
    beta: float,
    *,
    penalty: float = 1.25,
) -> P1Breakdown:
    """Exact p=1 expectation by contracting each term's radius-one light cone.

    Each local calculation uses at most 1+Delta qubits for a vertex term and
    2+deg(u)+deg(v) qubits for an edge term. For this graph family Delta=3.
    This implementation favors clarity over motif caching; add caching after the
    first experiments are validated.
    """
    vertex_sum = 0.0
    for v in graph.nodes:
        local = radius_one_subgraph(graph, [v])
        psi = statevector(local, [gamma], [beta], penalty=penalty)
        probs = np.abs(psi) ** 2
        vertex_sum += term_expectation_from_probabilities(local, probs, [v])

    edge_product_sum = 0.0
    for u, v in graph.edges:
        local = radius_one_subgraph(graph, [u, v])
        psi = statevector(local, [gamma], [beta], penalty=penalty)
        probs = np.abs(psi) ** 2
        edge_product_sum += term_expectation_from_probabilities(local, probs, [u, v])

    return P1Breakdown(
        vertex_sum=vertex_sum,
        edge_penalty_sum=penalty * edge_product_sum,
    )
