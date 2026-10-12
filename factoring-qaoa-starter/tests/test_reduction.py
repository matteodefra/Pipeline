import networkx as nx

from factoring_qaoa.classical import assignment_to_independent_set, is_independent_set
from factoring_qaoa.instances import sat_to_mis_graph


def test_satisfying_assignment_reaches_target() -> None:
    # Every variable appears at least twice, avoiding the multigraph edge case.
    clauses = [[1, 2, 3], [-1, 2, 3], [1, -2, 3], [1, 2, -3]]
    graph, occurrences = sat_to_mis_graph(clauses)

    class DummySAT:
        pass

    class DummyInstance:
        pass

    sat = DummySAT()
    sat.clauses = clauses
    instance = DummyInstance()
    instance.graph = graph
    instance.occurrences = occurrences
    instance.sat = sat

    assignment = {1: True, 2: True, 3: True}
    selected = assignment_to_independent_set(instance, assignment)
    assert is_independent_set(graph, selected)
    assert len(selected) == graph.graph["target_alpha"]
    assert max(dict(graph.degree()).values()) <= 3
    assert nx.number_of_nodes(graph) == 9 * len(clauses)
    assert nx.number_of_edges(graph) == 12 * len(clauses)
