from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import networkx as nx

from .instances import FactoringMISInstance


@dataclass(frozen=True)
class MISSolution:
    selected: set
    objective: int
    optimal: bool
    status: str


def is_independent_set(graph: nx.Graph, selected: set) -> bool:
    return all(not (u in selected and v in selected) for u, v in graph.edges)


def solve_sat(instance: FactoringMISInstance) -> dict[int, bool] | None:
    """Solve the generated CNF with PySAT. Install the `solvers` extra."""
    try:
        from pysat.solvers import Solver
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install solver dependencies with: uv sync --extra solvers") from exc

    with Solver(name="g4", bootstrap_with=instance.sat.clauses) as solver:
        if not solver.solve():
            return None
        model = solver.get_model()
    return {abs(lit): lit > 0 for lit in model}


def decode_factors(instance: FactoringMISInstance, assignment: Mapping[int, bool]) -> tuple[int, int]:
    p = sum(int(assignment.get(v, False)) << i for i, v in enumerate(instance.p_vars))
    q = sum(int(assignment.get(v, False)) << i for i, v in enumerate(instance.q_vars))
    return p, q


def assignment_to_independent_set(
    instance: FactoringMISInstance,
    assignment: Mapping[int, bool],
) -> set:
    """Map a satisfying SAT assignment to an independent set of target size."""
    selected: set = set()

    # The complement of the theorem's vertex cover selects F nodes for True
    # variables and T nodes for False variables.
    for var, items in instance.occurrences.items():
        side = "F" if assignment.get(var, False) else "T"
        selected.update((side, var, r) for r in range(len(items)))

    for h, clause in enumerate(instance.sat.clauses):
        chosen = None
        for j, literal in enumerate(clause):
            value = assignment.get(abs(literal), False)
            if (literal > 0 and value) or (literal < 0 and not value):
                chosen = ("C", h, j)
                break
        if chosen is None:
            raise ValueError(f"Assignment does not satisfy clause {h}: {clause}")
        selected.add(chosen)

    if not is_independent_set(instance.graph, selected):
        raise AssertionError("SAT-to-MIS witness construction produced a non-independent set.")
    return selected


def solve_mis_cp_sat(graph: nx.Graph, *, time_limit_s: float = 60.0) -> MISSolution:
    """Exact/anytime MIS baseline using OR-Tools CP-SAT."""
    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Install solver dependencies with: uv sync --extra solvers") from exc

    nodes = list(graph.nodes)
    model = cp_model.CpModel()
    x = {node: model.new_bool_var(f"x_{k}") for k, node in enumerate(nodes)}
    for u, v in graph.edges:
        model.add(x[u] + x[v] <= 1)
    model.maximize(sum(x.values()))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = 1  # deterministic baseline
    status_code = solver.solve(model)
    status_name = solver.status_name(status_code)
    feasible = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    selected = {node for node in nodes if feasible and solver.value(x[node]) == 1}
    return MISSolution(
        selected=selected,
        objective=len(selected),
        optimal=status_code == cp_model.OPTIMAL,
        status=status_name,
    )
