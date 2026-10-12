from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

import networkx as nx

from .factoring_3sat import SATBuilder, factoring_to_3sat


Node = tuple


@dataclass(frozen=True)
class FactoringMISInstance:
    N: int
    sat: SATBuilder
    p_vars: list[int]
    q_vars: list[int]
    graph: nx.Graph
    occurrences: dict[int, list[tuple[int, int, int]]]
    target_alpha: int

    @property
    def bit_width(self) -> int:
        return len(self.p_vars)

    @property
    def num_clauses(self) -> int:
        return len(self.sat.clauses)


def sat_to_mis_graph(
    clauses: Iterable[Iterable[int]],
    *,
    occurrence_order: str = "clause",
) -> tuple[nx.Graph, dict[int, list[tuple[int, int, int]]]]:
    """Construct the degree-3 graph from Theorem 2.6.

    Node labels
    -----------
    ("T", var, occurrence), ("F", var, occurrence): variable-cycle nodes.
    ("C", clause, position): clause-triangle nodes.

    The occurrence index is local to each SAT variable.  `occurrence_order` can be:
    - ``clause``: clause order, then literal position;
    - ``sign_blocks``: positive occurrences followed by negative occurrences;
    - ``alternating``: greedily alternate positive and negative occurrences.
    """
    clauses = [list(c) for c in clauses]
    if any(len(c) != 3 for c in clauses):
        raise ValueError("The reduction expects exactly three literal positions per clause.")

    raw: dict[int, list[tuple[int, int, int]]] = defaultdict(list)
    for h, clause in enumerate(clauses):
        for j, literal in enumerate(clause):
            raw[abs(literal)].append((h, j, literal))

    def order_occurrences(items: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
        if occurrence_order == "clause":
            return sorted(items, key=lambda x: (x[0], x[1]))
        if occurrence_order == "sign_blocks":
            return sorted(items, key=lambda x: (x[2] < 0, x[0], x[1]))
        if occurrence_order == "alternating":
            pos = sorted((x for x in items if x[2] > 0), key=lambda x: (x[0], x[1]))
            neg = sorted((x for x in items if x[2] < 0), key=lambda x: (x[0], x[1]))
            out: list[tuple[int, int, int]] = []
            take_pos = len(pos) >= len(neg)
            while pos or neg:
                source = pos if take_pos else neg
                other = neg if take_pos else pos
                if source:
                    out.append(source.pop(0))
                elif other:
                    out.append(other.pop(0))
                take_pos = not take_pos
            return out
        raise ValueError(f"Unknown occurrence_order={occurrence_order!r}")

    occurrences = {var: order_occurrences(items) for var, items in raw.items()}
    occurrence_number: dict[tuple[int, int], tuple[int, int]] = {}
    for var, items in occurrences.items():
        for r, (h, j, literal) in enumerate(items):
            occurrence_number[(h, j)] = (var, r)

    graph = nx.Graph()

    # Variable cycles: T_0-F_0-T_1-F_1-...-T_{m-1}-F_{m-1}-T_0.
    for var, items in occurrences.items():
        m = len(items)
        if m == 0:
            continue
        cycle: list[Node] = []
        for r, (_, _, literal) in enumerate(items):
            t = ("T", var, r)
            f = ("F", var, r)
            graph.add_node(t, kind="variable", side="T", variable=var, occurrence=r)
            graph.add_node(f, kind="variable", side="F", variable=var, occurrence=r)
            cycle.extend([t, f])
        if len(cycle) == 2:
            # A simple graph cannot contain the two parallel edges of a 2-cycle.
            # Factoring instances do not normally create a one-occurrence variable,
            # but reject it explicitly rather than silently changing the reduction.
            raise ValueError(f"Variable {var} occurs only once; multigraph handling is required.")
        graph.add_edges_from(zip(cycle, cycle[1:] + cycle[:1]), kind="cycle")

    # Clause triangles and occurrence matching.
    for h, clause in enumerate(clauses):
        c_nodes = [("C", h, j) for j in range(3)]
        for j, node in enumerate(c_nodes):
            graph.add_node(node, kind="clause", clause=h, position=j, literal=clause[j])
        graph.add_edges_from(
            [(c_nodes[0], c_nodes[1]), (c_nodes[1], c_nodes[2]), (c_nodes[2], c_nodes[0])],
            kind="triangle",
        )
        for j, literal in enumerate(clause):
            var, r = occurrence_number[(h, j)]
            endpoint = ("T", var, r) if literal > 0 else ("F", var, r)
            graph.add_edge(c_nodes[j], endpoint, kind="occurrence", literal=literal)

    graph.graph.update(
        num_clauses=len(clauses),
        num_variables=len(occurrences),
        target_alpha=sum(len(v) for v in occurrences.values()) + len(clauses),
        occurrence_order=occurrence_order,
    )
    return graph, occurrences


def build_factoring_mis(N: int, *, occurrence_order: str = "clause") -> FactoringMISInstance:
    sat, p_vars, q_vars = factoring_to_3sat(N)
    graph, occurrences = sat_to_mis_graph(sat.clauses, occurrence_order=occurrence_order)
    target_alpha = graph.graph["target_alpha"]
    return FactoringMISInstance(
        N=N,
        sat=sat,
        p_vars=p_vars,
        q_vars=q_vars,
        graph=graph,
        occurrences=occurrences,
        target_alpha=target_alpha,
    )
