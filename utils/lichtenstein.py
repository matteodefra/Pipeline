"""
3SAT → Planar3SAT reduction — Lichtenstein (1982).

Reference
─────────
D. Lichtenstein, "Planar formulae and their uses,"
SIAM J. Comput., 11(2):329–343, 1982.

Main entry point
────────────────
    from lichtenstein import three_sat_to_planar_three_sat

    formula, num_vars, num_clauses = three_sat_to_planar_three_sat(
        formula,    # list of clauses (list of signed ints)
        crossings,  # [((lit_a, ci1), (lit_b, ci2)), ...]
    )

The function returns a NamedTuple with three fields:
    .formula      — equisatisfiable Planar-3SAT formula
    .num_vars     — total variable count  (original + 9 per crossing)
    .num_clauses  — total clause count    (original + 22 per crossing)

It also optionally builds and returns a planar NetworkX incidence graph
when called with  return_graph=True  (requires networkx).

CNF format
──────────
A formula  is a list of clauses.
A clause   is a list of literals.
A literal  is a non-zero int: positive k → xk, negative -k → ¬xk.
Variable indices are consecutive positive integers starting from 1.

Crossing descriptor format
──────────────────────────
Each crossing is a pair  ((lit_a, ci1), (lit_b, ci2))  where:
  lit_a  — (possibly unsigned) variable index whose edge to clause ci1
            crosses the other edge.  Sign is ignored — polarity is read
            from the formula.
  ci1    — 0-based index of the clause that lit_a appears in.
  lit_b, ci2 — same for the other crossing edge.

Independence condition (for planar graph output)
────────────────────────────────────────────────
For the resulting incidence graph to be planar the crossing must satisfy:
    var_a (= |lit_a|) does NOT appear in formula[ci2], AND
    var_b (= |lit_b|) does NOT appear in formula[ci1].

Use  filter_crossings(formula, crossings)  to drop invalid ones before
calling the main function, or pass  strict=True  to raise on violation.

Gadget (per crossing)
─────────────────────
For a crossing of edges (a, c1) and (b, c2) the gadget introduces 9 fresh
auxiliary variables  a1, b1, α, β, γ, δ, ξ, a2, b2  and 22 new clauses:

    (¬a2∨¬b2∨α)  (a2∨¬α)  (b2∨¬α)          — a2∧b2 ↔ α
    (¬a2∨b1∨β)   (a2∨¬β)  (¬b1∨¬β)          — a2∧¬b1 ↔ β
    (a1∨b1∨γ)    (¬a1∨¬γ) (¬b1∨¬γ)          — ¬a1∧¬b1 ↔ γ
    (a1∨¬b2∨δ)   (¬a1∨¬δ) (b2∨¬δ)           — ¬a1∧b2 ↔ δ
    (α∨β∨ξ)      (γ∨δ∨¬ξ)                   — α∨β∨γ∨δ
    (¬α∨¬β)      (¬β∨¬γ)  (¬γ∨¬δ)  (¬δ∨¬α)  — at most one true
    (a2∨¬a)      (a∨¬a2)                     — a ↔ a2
    (b2∨¬b)      (b∨¬b2)                     — b ↔ b2

Net effect: a ↔ a1  and  b ↔ b1  (signals cross without interacting).
"""

from __future__ import annotations

from copy import deepcopy
from typing import List, NamedTuple, Optional, Tuple

# networkx is optional — only needed for build_planar_graph / return_graph=True
try:
    import networkx as nx
    _NX_AVAILABLE = True
except ImportError:
    _NX_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Types
# ─────────────────────────────────────────────────────────────────────────────

Literal  = int                    # non-zero signed int
Clause   = List[Literal]
Formula  = List[Clause]
Crossing = Tuple[Literal, int]    # (variable literal, 0-based clause index)


class PlanarResult(NamedTuple):
    """Return value of :func:`three_sat_to_planar_three_sat`."""
    formula:     Formula   # equisatisfiable Planar-3SAT formula
    num_vars:    int       # total variable count (original + aux)
    num_clauses: int       # total clause count


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def three_sat_to_planar_three_sat(
    formula:    Formula,
    crossings:  List[Tuple[Crossing, Crossing]],
    *,
    strict:      bool = False,
    return_graph: bool = False,
) -> PlanarResult:
    """
    Transform a 3-SAT formula into an equisatisfiable Planar-3SAT formula
    using Lichtenstein's crossover gadget at every detected edge crossing.

    Parameters
    ----------
    formula     : list of clauses (each clause = list of signed literals).
    crossings   : list of crossing descriptors  [((lit_a, ci1), (lit_b, ci2)), ...].
                  Use  filter_crossings()  to pre-filter invalid ones.
    strict      : if True, raise ValueError on any crossing that violates the
                  independence condition instead of silently skipping it.
    return_graph: if True, also build and return (as a 4th field) the planar
                  NetworkX incidence graph.  Requires networkx.

    Returns
    -------
    PlanarResult(formula, num_vars, num_clauses)
        Unpack as:  planar_formula, n_vars, n_clauses = three_sat_to_planar_three_sat(...)
        Or access:  result.formula,  result.num_vars,  result.num_clauses

    When return_graph=True the result also has  result.graph  (nx.Graph).
    """
    # ── pre-filter crossings ─────────────────────────────────────────────────
    valid_crossings = filter_crossings(formula, crossings, strict=strict, _quiet=not strict)

    # ── formula rewriting ────────────────────────────────────────────────────
    new_formula: Formula = deepcopy(formula)
    max_var = _max_variable(new_formula)

    # remap[ci][orig_var] = current_var in that clause
    # (handles the case where the same clause is touched by multiple gadgets)
    remap: dict = {}

    def current_var(ci: int, orig: int) -> int:
        return remap.get(ci, {}).get(orig, orig)

    def record_remap(ci: int, orig: int, new: int) -> None:
        if ci not in remap:
            remap[ci] = {}
        for k, v in remap[ci].items():
            if v == orig:
                remap[ci][k] = new
        remap[ci][orig] = new

    for (lit_a, ci1), (lit_b, ci2) in valid_crossings:
        orig_var_a = abs(lit_a)
        orig_var_b = abs(lit_b)
        var_a = current_var(ci1, orig_var_a)
        var_b = current_var(ci2, orig_var_b)

        # Allocate 9 fresh auxiliary variables
        a1, b1, alpha, beta, gamma, delta, xi, a2, b2 = range(max_var + 1, max_var + 10)
        max_var += 9

        # 22 gadget clauses
        new_formula.extend([
            [-a2, -b2,  alpha],   # 1
            [ a2,      -alpha],   # 2
            [ b2,      -alpha],   # 3
            [-a2,  b1,  beta ],   # 4
            [ a2,      -beta ],   # 5
            [-b1,      -beta ],   # 6
            [ a1,  b1,  gamma],   # 7
            [-a1,      -gamma],   # 8
            [-b1,      -gamma],   # 9
            [ a1, -b2,  delta],   # 10
            [-a1,      -delta],   # 11
            [ b2,      -delta],   # 12
            [ alpha, beta,   xi], # 13
            [ gamma, delta, -xi], # 14
            [-alpha, -beta],      # 15
            [-beta,  -gamma],     # 16
            [-gamma, -delta],     # 17
            [-delta, -alpha],     # 18
            [ a2,    -var_a],     # 19
            [ var_a, -a2   ],     # 20
            [ b2,    -var_b],     # 21
            [ var_b, -b2   ],     # 22
        ])

        # Determine polarity of var_a/var_b in their clauses
        neg_a = _sign_in_clause(new_formula[ci1], var_a, lit_a)
        neg_b = _sign_in_clause(new_formula[ci2], var_b, lit_b)

        new_a1_lit = -a1 if neg_a else a1
        new_b1_lit = -b1 if neg_b else b1

        new_formula[ci1] = _replace_literal(new_formula[ci1], var_a, new_a1_lit)
        new_formula[ci2] = _replace_literal(new_formula[ci2], var_b, new_b1_lit)

        record_remap(ci1, orig_var_a, a1)
        record_remap(ci2, orig_var_b, b1)

    result = PlanarResult(
        formula=new_formula,
        num_vars=max_var,
        num_clauses=len(new_formula),
    )

    if return_graph:
        if not _NX_AVAILABLE:
            raise ImportError("networkx is required for return_graph=True")
        graph = build_planar_graph(formula, valid_crossings)
        # Attach graph as an extra attribute (NamedTuple fields are fixed,
        # so we return a plain object that also has .graph)
        return _PlanarResultWithGraph(result, graph)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Crossing filter
# ─────────────────────────────────────────────────────────────────────────────

def filter_crossings(
    formula:   Formula,
    crossings: List[Tuple[Crossing, Crossing]],
    *,
    strict: bool = False,
    _quiet: bool = False,
) -> List[Tuple[Crossing, Crossing]]:
    """
    Return only crossings that satisfy the independence condition:
        var_a ∉ formula[ci2]  AND  var_b ∉ formula[ci1]

    Parameters
    ----------
    strict : if True, raise ValueError on the first violation instead of
             skipping it.
    """
    valid = []
    for (lit_a, ci1), (lit_b, ci2) in crossings:
        var_a = abs(lit_a);  var_b = abs(lit_b)
        c1_vars = {abs(l) for l in formula[ci1]}
        c2_vars = {abs(l) for l in formula[ci2]}

        ok = True
        for var, ci_other, ci_own in [(var_a, ci2, ci1), (var_b, ci1, ci2)]:
            other_vars = c2_vars if ci_other == ci2 else c1_vars
            if var in other_vars:
                msg = (
                    f"crossing (v{var_a},c{ci1})×(v{var_b},c{ci2}) skipped: "
                    f"v{var} appears in both c{ci_own} and c{ci_other} "
                    f"(independence condition violated)"
                )
                if strict:
                    raise ValueError(msg)
                if not _quiet:
                    print(f"  [filter_crossings] {msg}")
                ok = False
                break
        if ok:
            valid.append(((lit_a, ci1), (lit_b, ci2)))
    return valid


# ─────────────────────────────────────────────────────────────────────────────
# Planar graph builder  (requires networkx)
# ─────────────────────────────────────────────────────────────────────────────

def build_planar_graph(
    formula:   Formula,
    crossings: List[Tuple[Crossing, Crossing]],
) -> "nx.Graph":
    """
    Build the planar NetworkX incidence graph after applying all gadgets.

    The crossings list must already be filtered (all must satisfy the
    independence condition).  Raises ValueError if the graph becomes
    non-planar, which indicates an invalid crossing descriptor.

    Returns
    -------
    G : nx.Graph  — bipartite variable-clause incidence graph.
                    Verify with  nx.check_planarity(G).
    """
    if not _NX_AVAILABLE:
        raise ImportError("networkx is required for build_planar_graph()")

    G = _formula_to_graph(formula)

    # is_planar, _ = nx.check_planarity(G)
    # if not is_planar:
    #     raise ValueError(
    #         "The original formula's incidence graph is already non-planar. "
    #         "The gadget can only be applied to formulas whose incidence graph "
    #         "is planar (even if drawn with crossings)."
    #     )

    orig_max = _max_variable(formula)
    aux_start = orig_max + 1
    serial = [0]

    def fn(role):
        name = f"_gc{serial[0]}_{role}";  serial[0] += 1;  return name

    for idx, ((lit_a, ci1), (lit_b, ci2)) in enumerate(crossings):
        var_a = abs(lit_a);  var_b = abs(lit_b)
        n_a = f"v{var_a}";   n_b = f"v{var_b}"
        n_c1 = f"c{ci1}";    n_c2 = f"c{ci2}"

        a1i, b1i, ali, bei, gai, dei, xii, a2i, b2i = range(aux_start, aux_start + 9)
        aux_start += 9

        n_a1=f"v{a1i}"; n_b1=f"v{b1i}"; n_a2=f"v{a2i}"; n_b2=f"v{b2i}"
        n_al=f"v{ali}"; n_be=f"v{bei}"; n_ga=f"v{gai}"; n_de=f"v{dei}"; n_xi=f"v{xii}"

        if G.has_edge(n_a, n_c1): G.remove_edge(n_a, n_c1)
        if G.has_edge(n_b, n_c2): G.remove_edge(n_b, n_c2)

        for n in [n_a1,n_b1,n_a2,n_b2,n_al,n_be,n_ga,n_de,n_xi]:
            G.add_node(n, type="variable")

        def gc(role, vars_):
            nid = fn(role);  G.add_node(nid, type="clause")
            for v in vars_:  G.add_edge(nid, v)

        gc("c1", [n_a2,n_b2,n_al]); gc("c2",[n_a2,n_al]); gc("c3",[n_b2,n_al])
        gc("c4", [n_a2,n_b1,n_be]); gc("c5",[n_a2,n_be]); gc("c6",[n_b1,n_be])
        gc("c7", [n_a1,n_b1,n_ga]); gc("c8",[n_a1,n_ga]); gc("c9",[n_b1,n_ga])
        gc("c10",[n_a1,n_b2,n_de]); gc("c11",[n_a1,n_de]); gc("c12",[n_b2,n_de])
        gc("c13",[n_al,n_be,n_xi]); gc("c14",[n_ga,n_de,n_xi])
        gc("c15",[n_al,n_be]); gc("c16",[n_be,n_ga])
        gc("c17",[n_ga,n_de]); gc("c18",[n_de,n_al])
        gc("ra", [n_a, n_a2])
        gc("rb", [n_b, n_b2])
        G.add_edge(n_a1, n_c1)
        G.add_edge(n_b1, n_c2)

        is_ok, _ = nx.check_planarity(G)
        if not is_ok:
            raise ValueError(
                f"Graph became non-planar after gadget {idx}: "
                f"({n_a},{n_c1})×({n_b},{n_c2}). "
                f"Check that the crossing satisfies the independence condition."
            )

    return G


# ─────────────────────────────────────────────────────────────────────────────
# SAT-solver verification  (requires pysat)
# ─────────────────────────────────────────────────────────────────────────────

def verify_equisatisfiability(
    formula:   Formula,
    crossings: List[Tuple[Crossing, Crossing]],
    verbose:   bool = True,
) -> bool:
    """
    Solve both the original and the reduced formula with PySAT and check:
      1. Both are SAT or both are UNSAT.
      2. The planar assignment satisfies every clause (including gadget clauses).
      3. The planar assignment restricted to original variables satisfies the
         original formula.

    Returns True if all checks pass.  Requires  python-sat.
    """
    try:
        from pysat.solvers import Solver
    except ImportError:
        raise ImportError("python-sat is required: pip install python-sat")

    def solve(f):
        with Solver(name="g4") as s:
            for clause in f:
                s.add_clause(clause)
            sat = s.solve()
            model = {abs(l): l > 0 for l in s.get_model()} if sat else None
        return sat, model

    orig_sat, orig_model = solve(formula)
    planar_result = three_sat_to_planar_three_sat(formula, crossings)
    planar_sat, planar_model = solve(planar_result.formula)

    orig_max = _max_variable(formula)

    if verbose:
        print("=" * 56)
        print("Equisatisfiability check")
        print("=" * 56)
        print(f"  Original : {'SAT' if orig_sat else 'UNSAT'}")
        print(f"  Planar   : {'SAT' if planar_sat else 'UNSAT'}")
        print(f"  Variables: {orig_max} → {planar_result.num_vars} "
              f"(+{planar_result.num_vars - orig_max} aux)")
        print(f"  Clauses  : {len(formula)} → {planar_result.num_clauses} "
              f"(+{planar_result.num_clauses - len(formula)} gadget)")

    passed = True

    if orig_sat != planar_sat:
        print("  ✗ EQUISATISFIABILITY VIOLATED")
        passed = False
    elif verbose:
        print("  ✓ Equisatisfiability holds")

    if orig_sat and planar_sat:
        ok2 = _eval(planar_result.formula, planar_model)
        ok3 = _eval(formula, planar_model)
        if verbose:
            print(f"  {'✓' if ok2 else '✗'} Planar model satisfies all planar clauses")
            print(f"  {'✓' if ok3 else '✗'} Planar model satisfies original formula")
        if not (ok2 and ok3):
            passed = False

    if verbose:
        print("=" * 56)
    return passed


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _max_variable(formula: Formula) -> int:
    return max((abs(l) for clause in formula for l in clause), default=0)


def _sign_in_clause(clause: Clause, var: int, fallback_lit: int) -> bool:
    """Return True if `var` appears negated in `clause`."""
    for lit in clause:
        if abs(lit) == var:
            return lit < 0
    return fallback_lit < 0


def _replace_literal(clause: Clause, old_var: int, new_lit: int) -> Clause:
    """Replace the literal for old_var in clause with new_lit (preserving polarity)."""
    result = list(clause)
    new_var = abs(new_lit)
    for i, lit in enumerate(result):
        if abs(lit) == old_var:
            result[i] = new_var if lit > 0 else -new_var
            return result
    raise ValueError(
        f"Variable {old_var} not found in clause {clause}. "
        "Check that the crossing descriptor matches the formula."
    )


def _eval(formula: Formula, assignment: dict) -> bool:
    for clause in formula:
        if not any(
            (l > 0) == assignment.get(abs(l), False) for l in clause
        ):
            return False
    return True


def _formula_to_graph(formula: Formula) -> "nx.Graph":
    G = nx.Graph()
    for vi in sorted({abs(l) for clause in formula for l in clause}):
        G.add_node(f"v{vi}", type="variable", index=vi)
    for ci, clause in enumerate(formula):
        G.add_node(f"c{ci}", type="clause", index=ci)
        for lit in clause:
            G.add_edge(f"v{abs(lit)}", f"c{ci}", negated=(lit < 0))
    return G


class _PlanarResultWithGraph:
    """Thin wrapper that adds a .graph attribute to PlanarResult."""
    def __init__(self, result: PlanarResult, graph):
        self._r = result
        self.graph = graph

    @property
    def formula(self):     return self._r.formula
    @property
    def num_vars(self):    return self._r.num_vars
    @property
    def num_clauses(self): return self._r.num_clauses

    def __iter__(self):
        return iter((self._r.formula, self._r.num_vars, self._r.num_clauses))

    def __repr__(self):
        return (f"PlanarResult(formula=<{self.num_clauses} clauses>, "
                f"num_vars={self.num_vars}, num_clauses={self.num_clauses}, "
                f"graph={self.graph})")


# ─────────────────────────────────────────────────────────────────────────────
# Quick demo when run as a script
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # ── edit these two to test your own instance ──────────────────────────
    YOUR_FORMULA: Formula = [
        [ 1,  3,  5],   # c0
        [ 2,  4,  6],   # c1
        [ 7,  9, 11],   # c2
        [ 8, 10, 12],   # c3
    ]
    YOUR_CROSSINGS = [
        ((1, 0), (2, 1)),   # edge (x1,c0) crosses edge (x2,c1)
        ((7, 2), (8, 3)),   # edge (x7,c2) crosses edge (x8,c3)
    ]
    # ─────────────────────────────────────────────────────────────────────

    print("── Formula rewriting ──────────────────────────────────")
    result = three_sat_to_planar_three_sat(YOUR_FORMULA, YOUR_CROSSINGS)
    print(f"  Original : {_max_variable(YOUR_FORMULA)} vars, {len(YOUR_FORMULA)} clauses")
    print(f"  Planar   : {result.num_vars} vars, {result.num_clauses} clauses")

    print("\n── Planarity check (requires networkx) ────────────────")
    if _NX_AVAILABLE:
        valid = filter_crossings(YOUR_FORMULA, YOUR_CROSSINGS)
        G = build_planar_graph(YOUR_FORMULA, valid)
        is_p, _ = nx.check_planarity(G)
        n_var = sum(1 for _,d in G.nodes(data=True) if d.get("type")=="variable")
        n_cls = sum(1 for _,d in G.nodes(data=True) if d.get("type")=="clause")
        print(f"  nodes={G.number_of_nodes()} (var={n_var} cls={n_cls})  "
              f"edges={G.number_of_edges()}  planar={'✓' if is_p else '✗'}")
    else:
        print("  networkx not installed — skipped")

    print("\n── Equisatisfiability check (requires python-sat) ─────")
    try:
        verify_equisatisfiability(YOUR_FORMULA, YOUR_CROSSINGS)
    except ImportError as e:
        print(f"  {e} — skipped")