from __future__ import annotations

from dataclasses import dataclass
from math import cos, sin
from typing import Iterable, Sequence

import networkx as nx
import numpy as np


@dataclass(frozen=True)
class QAOAMetrics:
    expectation: float
    feasible_probability: float
    best_probability: float
    best_cost: float


def _indexed_graph(graph: nx.Graph) -> tuple[nx.Graph, list]:
    nodes = list(graph.nodes)
    return nx.convert_node_labels_to_integers(graph, ordering="default"), nodes


def cost_values(graph: nx.Graph, penalty: float = 1.25) -> np.ndarray:
    """C(x)=sum_v x_v - penalty * sum_(u,v) x_u x_v for all bit strings."""
    indexed, _ = _indexed_graph(graph)
    n = indexed.number_of_nodes()
    if n > 25:
        raise ValueError("Dense statevector utilities are intended for at most about 25 qubits.")
    states = np.arange(1 << n, dtype=np.uint64)
    selected = np.stack([((states >> q) & 1).astype(np.float64) for q in range(n)], axis=1)
    values = selected.sum(axis=1)
    for u, v in indexed.edges:
        values -= penalty * selected[:, u] * selected[:, v]
    return values


def _apply_x_mixer(state: np.ndarray, beta: float, qubit: int, n: int) -> None:
    """In-place application of exp(-i beta X) on one little-endian qubit."""
    c, s = cos(beta), -1j * sin(beta)
    step = 1 << qubit
    block = step << 1
    for start in range(0, 1 << n, block):
        a = state[start : start + step].copy()
        b = state[start + step : start + block].copy()
        state[start : start + step] = c * a + s * b
        state[start + step : start + block] = s * a + c * b


def statevector(
    graph: nx.Graph,
    gammas: Sequence[float],
    betas: Sequence[float],
    *,
    penalty: float = 1.25,
) -> np.ndarray:
    if len(gammas) != len(betas):
        raise ValueError("gammas and betas must have equal length")
    indexed, _ = _indexed_graph(graph)
    n = indexed.number_of_nodes()
    values = cost_values(indexed, penalty=penalty)
    psi = np.full(1 << n, 1 / np.sqrt(1 << n), dtype=np.complex128)
    for gamma, beta in zip(gammas, betas):
        psi *= np.exp(-1j * gamma * values)
        for q in range(n):
            _apply_x_mixer(psi, beta, q, n)
    return psi


def metrics(
    graph: nx.Graph,
    gammas: Sequence[float],
    betas: Sequence[float],
    *,
    penalty: float = 1.25,
) -> QAOAMetrics:
    indexed, _ = _indexed_graph(graph)
    n = indexed.number_of_nodes()
    values = cost_values(indexed, penalty=penalty)
    psi = statevector(indexed, gammas, betas, penalty=penalty)
    probs = np.abs(psi) ** 2

    states = np.arange(1 << n, dtype=np.uint64)
    selected = np.stack([((states >> q) & 1).astype(np.int8) for q in range(n)], axis=1)
    violations = np.zeros(1 << n, dtype=np.int16)
    for u, v in indexed.edges:
        violations += selected[:, u] * selected[:, v]
    feasible = violations == 0
    cardinality = selected.sum(axis=1)
    best_size = int(cardinality[feasible].max(initial=0))
    best = feasible & (cardinality == best_size)

    return QAOAMetrics(
        expectation=float(probs @ values),
        feasible_probability=float(probs[feasible].sum()),
        best_probability=float(probs[best].sum()),
        best_cost=float(values.max()),
    )


def term_expectation_from_probabilities(
    graph: nx.Graph,
    probabilities: np.ndarray,
    support: Iterable,
) -> float:
    """Expectation of product_{v in support} x_v on a small graph."""
    nodes = list(graph.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    support_idx = [index[v] for v in support]
    states = np.arange(len(probabilities), dtype=np.uint64)
    product = np.ones(len(probabilities), dtype=np.float64)
    for q in support_idx:
        product *= ((states >> q) & 1)
    return float(probabilities @ product)
