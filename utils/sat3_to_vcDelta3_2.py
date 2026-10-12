"""
Reduction: 3-SAT → Vertex Cover on a Δ=3 graph
================================================
Based on:
  Garey, Johnson & Stockmeyer, "Some simplified NP-complete graph problems"
  Theoretical Computer Science 1 (1976) 237-267.
  https://www.sciencedirect.com/science/article/pii/0304397576900591

All graph objects are represented as plain Python dataclasses (no NetworkX).
The resulting ``GraphData`` can be fed directly into ``vcDelta3_to_unitBallGraph``
without any conversion step.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight graph representation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GraphData:
    """
    Minimal undirected graph stored as plain Python sets.

    Attributes
    ----------
    nodes : set[str]
        Node identifiers (strings).
    edges : set[tuple[str, str]]
        Undirected edges stored as *sorted* 2-tuples so that
        (u, v) and (v, u) are the same key:  (min(u,v), max(u,v)).
    """
    nodes: set = field(default_factory=set)
    edges: set = field(default_factory=set)

    # ── mutation helpers ──────────────────────────────────────────────────

    def add_node(self, u: str) -> None:
        self.nodes.add(u)

    def add_nodes_from(self, iterable) -> None:
        self.nodes.update(iterable)

    def add_edge(self, u: str, v: str) -> None:
        self.nodes.add(u)
        self.nodes.add(v)
        self.edges.add(_ekey(u, v))

    def add_edges_from(self, iterable) -> None:
        for u, v in iterable:
            self.add_edge(u, v)

    # ── query helpers ─────────────────────────────────────────────────────

    def number_of_nodes(self) -> int:
        return len(self.nodes)

    def number_of_edges(self) -> int:
        return len(self.edges)

    def has_edge(self, u: str, v: str) -> bool:
        return _ekey(u, v) in self.edges

    def neighbors(self, u: str):
        """Yield all neighbours of *u*."""
        for a, b in self.edges:
            if a == u:
                yield b
            elif b == u:
                yield a

    def degree(self, u: str) -> int:
        return sum(1 for _ in self.neighbors(u))

    def max_degree(self) -> int:
        if not self.nodes:
            return 0
        return max(self.degree(u) for u in self.nodes)

    # ── merge ─────────────────────────────────────────────────────────────

    def union(self, other: "GraphData") -> "GraphData":
        """Return a new GraphData that is the disjoint union of self and other."""
        g = GraphData()
        g.nodes = self.nodes | other.nodes
        g.edges = self.edges | other.edges
        return g

    def __repr__(self) -> str:
        return (f"GraphData(nodes={self.number_of_nodes()}, "
                f"edges={self.number_of_edges()})")


def _ekey(u: str, v: str) -> tuple:
    """Canonical (sorted) edge key so (u,v) == (v,u)."""
    return (u, v) if u <= v else (v, u)


def union_all(graphs) -> GraphData:
    """Merge an iterable of GraphData objects into a single GraphData."""
    result = GraphData()
    for g in graphs:
        result.nodes.update(g.nodes)
        result.edges.update(g.edges)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SAT → 3-SAT clause splitting
# ─────────────────────────────────────────────────────────────────────────────

def _reduce_clause_iter(vars_: list, first_var: int, desired_k: int = 3):
    """
    Split one over-sized clause (>desired_k literals) into a chain of
    exactly *desired_k*-literal clauses using fresh auxiliary variables.

    Parameters
    ----------
    vars_      : list of signed integers (literals)
    first_var  : next available auxiliary variable index
    desired_k  : target clause width (default 3)

    Returns
    -------
    new_clauses : dict {int -> list of literals}
    first_var   : updated next-available index
    """
    first  = vars_[:desired_k - 1]
    last   = vars_[-(desired_k - 1):]
    remaining = vars_[desired_k - 1: -(desired_k - 1)]

    new_clauses = {0: first + [first_var]}
    i = 1

    for var in remaining:
        new_clauses[i] = [-first_var, var, first_var + 1]
        first_var += 1
        i += 1

    new_clauses[i] = [-first_var] + last
    return new_clauses, first_var


def sat_to_3sat(n_vars: int, n_clauses: int, clauses: dict,
                desired_k: int = 3):
    """
    Reduce an arbitrary SAT formula to an equivalent 3-SAT formula.

    Parameters
    ----------
    n_vars    : number of original variables
    n_clauses : number of original clauses (length of *clauses*)
    clauses   : dict {int -> list of signed-int literals}
    desired_k : target clause width (default 3)

    Returns
    -------
    cnf3      : dict {int -> list[int]}  — reindexed 3-SAT clauses
    n_vars3   : int                      — variable count after expansion
    n_clauses3: int                      — clause count after expansion
    """
    clauses_to_split = []
    next_clause_idx  = n_clauses
    first_var        = n_vars + 1

    for idx, lits in clauses.items():
        if len(lits) > desired_k:
            clauses_to_split.append(idx)
        elif len(lits) < desired_k:
            lit = lits[0]
            while len(clauses[idx]) < desired_k:
                clauses[idx].append(lit)

    for clause_idx in clauses_to_split:
        new_clauses, first_var = _reduce_clause_iter(clauses[clause_idx],
                                                     first_var)
        first_var += 1
        for vals in new_clauses.values():
            clauses[next_clause_idx] = vals
            next_clause_idx += 1

    for clause_idx in clauses_to_split:
        del clauses[clause_idx]

    cnf3 = dict(enumerate(clauses.values()))
    return cnf3, first_var - 1, len(cnf3)


# ─────────────────────────────────────────────────────────────────────────────
# 3-SAT → Vertex Cover (Δ ≤ 3) graph construction
# ─────────────────────────────────────────────────────────────────────────────

def count_occurences(cnf3: dict, n: int, m: int) -> dict:
    """
    Count how many times each variable appears (as x_i or ¬x_i) across
    all clauses.

    Returns
    -------
    dict {variable_index -> occurrence_count}
    """
    occ = {i: 0 for i in range(1, n + 1)}
    for lits in cnf3.values():
        for lit in lits:
            occ[abs(lit)] += 1
    return occ


def create_subgraph_variables(n: int, occurences: dict) -> dict:
    """
    Build the variable gadget H_i for each variable i = 1..n.

    H_i is a cycle of 2·m_i nodes alternating T_{i,j} / F_{i,j},
    where m_i = occurences[i].

    Returns
    -------
    dict {variable_index -> GraphData}
    """
    Hs = {}
    for i in range(1, n + 1):
        m_i = occurences[i]
        H   = GraphData()

        t_nodes = ["T_{},{}".format(i, j) for j in range(1, m_i + 1)]
        f_nodes = ["F_{},{}".format(i, j) for j in range(1, m_i + 1)]
        H.add_nodes_from(t_nodes)
        H.add_nodes_from(f_nodes)

        # horizontal T-F pairs
        for j in range(1, m_i + 1):
            H.add_edge("T_{},{}".format(i, j), "F_{},{}".format(i, j))

        # chain F_{i,j} — T_{i,j+1}
        for j in range(1, m_i):
            H.add_edge("F_{},{}".format(i, j), "T_{},{}".format(i, j + 1))

        # close the cycle
        H.add_edge("F_{},{}".format(i, m_i), "T_{},{}".format(i, 1))

        Hs[i] = H
    return Hs


def create_subgraph_clauses(cnf3: dict, n: int, m: int) -> dict:
    """
    Build the clause gadget H'_k for each clause k.

    H'_k is a triangle on three nodes V_{k,1}, V_{k,2}, V_{k,3}.

    Returns
    -------
    dict {clause_index -> GraphData}
    """
    Hprimes = {}
    for k in cnf3:
        H = GraphData()
        v_nodes = ["V_{},{}".format(k, j) for j in range(1, 4)]
        H.add_nodes_from(v_nodes)

        # complete graph on 3 nodes = triangle
        H.add_edge(v_nodes[0], v_nodes[1])
        H.add_edge(v_nodes[0], v_nodes[2])
        H.add_edge(v_nodes[1], v_nodes[2])

        Hprimes[k] = H
    return Hprimes


def create_full_graph(n: int, cnf3: dict,
                      variablegraphs: dict,
                      clausegraphs: dict) -> GraphData:
    """
    Assemble the full Vertex-Cover / Δ=3 graph from variable and clause gadgets
    plus the two families of inter-gadget edges (B1 and B2).

    Parameters
    ----------
    n              : number of variables
    cnf3           : dict {clause_index -> [lit1, lit2, lit3]}
    variablegraphs : output of create_subgraph_variables()
    clausegraphs   : output of create_subgraph_clauses()

    Returns
    -------
    G : GraphData
    """
    # Track occurrence counts again to correctly index T/F nodes
    occurences = {i: 0 for i in range(1, n + 1)}

    edgesetB1 = []   # T-node ↔ clause node  (positive literal)
    edgesetB2 = []   # F-node ↔ clause node  (negative literal)

    for k, lits in cnf3.items():
        for index, lit in enumerate(lits):
            var = abs(lit)
            occurences[var] += 1
            j_th = occurences[var]

            clause_node = "V_{},{}".format(k, index + 1)
            if lit < 0:
                edgesetB2.append(("F_{},{}".format(var, j_th), clause_node))
            else:
                edgesetB1.append(("T_{},{}".format(var, j_th), clause_node))

    # Merge all gadget sub-graphs
    all_graphs = (list(variablegraphs.values()) +
                  list(clausegraphs.values()))
    G = union_all(all_graphs)

    # Add inter-gadget edges
    G.add_edges_from(edgesetB1)
    G.add_edges_from(edgesetB2)

    return G