import networkx as nx
import numpy as np

from factoring_qaoa.qaoa_exact import metrics, statevector


def test_statevector_normalized() -> None:
    graph = nx.path_graph(3)
    psi = statevector(graph, [0.4], [0.2])
    assert np.isclose(np.vdot(psi, psi), 1.0)


def test_metrics_are_probabilities() -> None:
    graph = nx.path_graph(3)
    result = metrics(graph, [0.4], [0.2])
    assert 0.0 <= result.feasible_probability <= 1.0
    assert 0.0 <= result.best_probability <= 1.0


def test_p1_local_matches_full_statevector() -> None:
    from factoring_qaoa.p1_local import p1_objective
    from factoring_qaoa.qaoa_exact import cost_values

    graph = nx.cycle_graph(4)
    psi = statevector(graph, [0.4], [0.2], penalty=1.25)
    full = float((np.abs(psi) ** 2) @ cost_values(graph, penalty=1.25))
    local = p1_objective(graph, 0.4, 0.2, penalty=1.25).objective
    assert np.isclose(full, local)
