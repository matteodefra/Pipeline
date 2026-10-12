"""
Prime Multiplier → SAT Formula Generator
=========================================
Given two prime numbers p and q, this module:
  1. Builds a binary array multiplier with SYMBOLIC input bits (VAR nodes),
     so the circuit structure is preserved before any values are fixed.
  2. Applies constant folding only on gates whose inputs are already known
     (carry chains, zero-padding, etc.) — partial folding keeps the formula small.
  3. Encodes the surviving circuit via Tseitin (one auxiliary variable per live
     gate) into CNF clauses using AND / OR / NOT only.
  4. Adds unit clauses to pin p's bits, q's bits, and the output bits to their
     known values, producing the final grounded SAT formula.

The formula is satisfiable with the unique assignment that witnesses p * q = n.

Usage
-----
    python prime_multiplier_sat.py            # built-in demo (3x5, 7x11, 13x17)
    python prime_multiplier_sat.py 7 11       # custom primes
    python prime_multiplier_sat.py 7 11 --raw # print raw clauses list only
"""

from __future__ import annotations
import sys
from math import ceil, log2
from itertools import count as _count
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 1.  Circuit node
# ---------------------------------------------------------------------------

_id_gen = _count(1)


@dataclass
class Node:
    """One node in the circuit DAG."""
    id:   int  = field(default_factory=lambda: next(_id_gen))
    kind: str  = "CONST"   # CONST | VAR | AND | OR | NOT
    val:  Optional[int] = None   # CONST: 0/1
    name: Optional[str] = None   # VAR: human label, e.g. "p0"
    i1:   Optional["Node"] = None
    i2:   Optional["Node"] = None

    def __hash__(self):      return hash(self.id)
    def __eq__(self, other): return isinstance(other, Node) and self.id == other.id

    def __repr__(self):
        if self.kind == "CONST": return f"CONST({self.val})"
        if self.kind == "VAR":   return f"VAR({self.name})"
        if self.kind == "NOT":   return f"NOT({self.i1.id})"
        return f"{self.kind}({self.i1.id},{self.i2.id})"


# ---------------------------------------------------------------------------
# 2.  Gate constructors  (constant folding on CONST nodes only)
# ---------------------------------------------------------------------------

def CONST(v: int) -> Node:
    return Node(kind="CONST", val=v & 1)

def VAR(name: str) -> Node:
    return Node(kind="VAR", name=name)

def AND(a: Node, b: Node) -> Node:
    if a.kind == "CONST":
        return b if a.val == 1 else CONST(0)
    if b.kind == "CONST":
        return a if b.val == 1 else CONST(0)
    if a is b:
        return a
    return Node(kind="AND", i1=a, i2=b)

def OR(a: Node, b: Node) -> Node:
    if a.kind == "CONST":
        return a if a.val == 1 else b
    if b.kind == "CONST":
        return b if b.val == 1 else a
    if a is b:
        return a
    return Node(kind="OR", i1=a, i2=b)

def NOT(a: Node) -> Node:
    if a.kind == "CONST":
        return CONST(1 - a.val)
    if a.kind == "NOT":
        return a.i1              # double-negation elimination
    return Node(kind="NOT", i1=a)

def XOR(a: Node, b: Node) -> Node:
    """XOR via AND/OR/NOT: (a AND NOT b) OR (NOT a AND b)."""
    return OR(AND(a, NOT(b)), AND(NOT(a), b))


# ---------------------------------------------------------------------------
# 3.  Adder primitives
# ---------------------------------------------------------------------------

def half_adder(a: Node, b: Node) -> tuple[Node, Node]:
    """Returns (sum_bit, carry_out)."""
    return XOR(a, b), AND(a, b)

def full_adder(a: Node, b: Node, cin: Node) -> tuple[Node, Node]:
    """Returns (sum_bit, carry_out)."""
    s1, c1 = half_adder(a, b)
    s2, c2 = half_adder(s1, cin)
    return s2, OR(c1, c2)


# ---------------------------------------------------------------------------
# 4.  Array multiplier  (symbolic inputs)
# ---------------------------------------------------------------------------

def build_multiplier(n: int) -> tuple[list[Node], list[Node], list[Node]]:
    """
    Build an n x n binary array multiplier with symbolic VAR inputs.

    Returns (p_bits, q_bits, output_bits) where:
      p_bits[i]      = VAR node for bit i of p  (LSB first)
      q_bits[j]      = VAR node for bit j of q  (LSB first)
      output_bits[k] = circuit node for bit k of p*q (LSB first, 2n bits total)
    """
    m = 2 * n

    p_bits = [VAR(f"p{i}") for i in range(n)]
    q_bits = [VAR(f"q{j}") for j in range(n)]

    # Partial products
    pp = [[AND(p_bits[i], q_bits[j]) for j in range(n)] for i in range(n)]

    # Running sum (starts at 0)
    sums = [CONST(0)] * m

    for i in range(n):
        carry = CONST(0)
        for j in range(n):
            s, carry = full_adder(sums[i + j], pp[i][j], carry)
            sums[i + j] = s
        for k in range(i + n, m):
            s, carry = full_adder(sums[k], CONST(0), carry)
            sums[k] = s

    return p_bits, q_bits, sums


# ---------------------------------------------------------------------------
# 5.  Tseitin SAT encoding
# ---------------------------------------------------------------------------

def _collect_live(roots: list[Node]) -> list[Node]:
    """
    Topological DFS over the DAG; returns all non-CONST nodes in
    dependency order (inputs before the gates that use them).
    """
    visited: set[int] = set()
    order:   list[Node] = []

    def dfs(node: Node):
        if node.id in visited:
            return
        visited.add(node.id)
        if node.i1: dfs(node.i1)
        if node.i2: dfs(node.i2)
        if node.kind != "CONST":
            order.append(node)

    for r in roots:
        dfs(r)
    return order


def _lit(node: Node, var_map: dict[int, str], neg: bool = False) -> str:
    """String literal for a node (positive or negated)."""
    if node.kind == "CONST":
        raw = str(node.val)
    elif node.kind == "VAR":
        raw = node.name          # human-readable name
    else:
        raw = var_map[node.id]
    return ("NOT " + raw) if neg else raw


def tseitin_encode(
    p_bits:      list[Node],
    q_bits:      list[Node],
    output_bits: list[Node],
    p_val:       int,
    q_val:       int,
) -> dict:
    """
    Tseitin-encode the multiplier circuit.

    Steps
    -----
    1. Collect every live (non-CONST) node reachable from output_bits.
    2. Assign a SAT variable to each live node:
         - VAR nodes keep their human name (p0, q1, ...)
         - Gate nodes get auxiliary names (g1, g2, ...)
    3. Add Tseitin equivalence clauses for each gate.
    4. Add unit clauses to fix input bits to p_val / q_val.
    5. Add unit clauses to fix output bits to (p_val * q_val).

    Returns a dict with 'clauses', 'formula', 'var_count', 'gate_counts'.
    """
    product = p_val * q_val
    live = _collect_live(output_bits)

    # Build variable name map
    var_map: dict[int, str] = {}
    aux_idx = 0
    for node in live:
        if node.kind == "VAR":
            var_map[node.id] = node.name      # p0, p1, ..., q0, q1, ...
        else:
            aux_idx += 1
            var_map[node.id] = f"g{aux_idx}"  # auxiliary gate variables

    gate_counts = {"AND": 0, "OR": 0, "NOT": 0}
    for node in live:
        if node.kind in gate_counts:
            gate_counts[node.kind] += 1

    clauses: list[str] = []

    # --- Tseitin gate clauses ---
    for node in live:
        if node.kind == "VAR":
            continue   # input variables need no structural clause

        g = var_map[node.id]

        if node.kind == "NOT":
            a = _lit(node.i1, var_map)
            # g <-> NOT a  =>  (g OR a) AND (NOT g OR NOT a)
            clauses.append(f"({g} OR {a})")
            clauses.append(f"(NOT {g} OR NOT {a})")

        elif node.kind == "AND":
            a = _lit(node.i1, var_map)
            b = _lit(node.i2, var_map)
            # g <-> a AND b  =>  (NOT g OR a) AND (NOT g OR b) AND (g OR NOT a OR NOT b)
            clauses.append(f"(NOT {g} OR {a})")
            clauses.append(f"(NOT {g} OR {b})")
            clauses.append(f"({g} OR NOT {a} OR NOT {b})")

        elif node.kind == "OR":
            a = _lit(node.i1, var_map)
            b = _lit(node.i2, var_map)
            # g <-> a OR b  =>  (g OR NOT a) AND (g OR NOT b) AND (NOT g OR a OR b)
            clauses.append(f"({g} OR NOT {a})")
            clauses.append(f"({g} OR NOT {b})")
            clauses.append(f"(NOT {g} OR {a} OR {b})")

    # --- Unit clauses fixing input bits ---
    n = len(p_bits)
    for i, node in enumerate(p_bits):
        bit = (p_val >> i) & 1
        clauses.append(node.name if bit == 1 else f"NOT {node.name}")
    for j, node in enumerate(q_bits):
        bit = (q_val >> j) & 1
        clauses.append(node.name if bit == 1 else f"NOT {node.name}")

    # --- Unit clauses fixing output bits to p*q ---
    for k, node in enumerate(output_bits):
        bit = (product >> k) & 1
        if node.kind == "CONST":
            continue   # folded away; no variable to constrain
        g = var_map[node.id]
        clauses.append(g if bit == 1 else f"NOT {g}")

    formula = "\nAND\n".join(clauses)

    return {
        "clauses":     clauses,
        "formula":     formula,
        "var_count":   len(live),
        "gate_counts": gate_counts,
        "aux_vars":    aux_idx,
        "input_vars":  2 * n,
    }


# ---------------------------------------------------------------------------
# 6.  DIMACS-style integer clause dict
# ---------------------------------------------------------------------------

def clauses_to_dimacs(clauses: list[str]) -> tuple[dict[int, list[int]], dict[str, int]]:
    """
    Convert the list of string clauses produced by tseitin_encode into a
    DIMACS-style integer representation.

    Each variable name (p0, q1, g5, …) is assigned a unique positive integer
    index.  A literal is positive if the variable appears without NOT, and
    negative if it appears with NOT.

    Parameters
    ----------
    clauses : list[str]
        Clauses in the form "(NOT g1 OR p0 OR NOT g3)" as returned by
        tseitin_encode.

    Returns
    -------
    clause_dict : dict[int, list[int]]
        {clause_index: [signed_literal, ...]}
        e.g. {0: [-1, 2], 1: [3, -1, -2], ...}

    var_index : dict[str, int]
        Mapping from variable name to its positive integer index,
        e.g. {"p0": 1, "p1": 2, ..., "g1": 7, ...}
    """
    # --- Build a consistent variable → integer mapping ---
    # We do one pass first to collect all variable names in encounter order,
    # so the numbering is deterministic and readable.
    var_index: dict[str, int] = {}

    def _register(name: str) -> int:
        if name not in var_index:
            var_index[name] = len(var_index) + 1   # 1-based
        return var_index[name]

    def _parse_clause(clause_str: str) -> list[int]:
        """Parse one clause string into a list of signed ints."""
        # Strip outer parens, split on ' OR '
        inner = clause_str.strip().lstrip("(").rstrip(")")
        literals = [tok.strip() for tok in inner.split(" OR ")]
        result = []
        for lit in literals:
            if lit.startswith("NOT "):
                var_name = lit[4:].strip()
                result.append(-_register(var_name))
            else:
                result.append(_register(lit))
        return result

    # Two-pass: first register all variables (preserves encounter order),
    # then build the dict.
    parsed: list[list[int]] = []
    for c in clauses:
        parsed.append(_parse_clause(c))

    clause_dict = {i: lits for i, lits in enumerate(parsed)}
    return clause_dict, var_index


# ---------------------------------------------------------------------------
# 7.  Primality check
# ---------------------------------------------------------------------------

def is_prime(n: int) -> bool:
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0: return False
    return True


# ---------------------------------------------------------------------------
# 7.  Public entry point
# ---------------------------------------------------------------------------

def generate(p: int, q: int, verbose: bool = True, raw: bool = False) -> dict:
    """
    Full pipeline: two primes -> SAT formula.

    Parameters
    ----------
    p, q    : prime integers
    verbose : print human-readable report
    raw     : print raw clause list instead of formatted report

    Returns the encoding dict (clauses, formula, var_count, gate_counts, ...).
    """
    if not is_prime(p): raise ValueError(f"{p} is not prime")
    if not is_prime(q): raise ValueError(f"{q} is not prime")

    n = max(2, ceil(log2(max(p, q) + 1)))
    p_bits, q_bits, output_bits = build_multiplier(n)
    result = tseitin_encode(p_bits, q_bits, output_bits, p, q)

    clause_dict, var_index = clauses_to_dimacs(result["clauses"])
    result.update(p=p, q=q, product=p * q, n_bits=n, output_bits_count=2 * n,
                  clause_dict=clause_dict, var_index=var_index)

    if raw:
        for c in result["clauses"]:
            print(c)
    elif verbose:
        _print_report(result)

    return result


def _print_report(r: dict):
    p, q, product = r["p"], r["q"], r["product"]
    n  = r["n_bits"]
    m  = r["output_bits_count"]
    gc = r["gate_counts"]

    bar = "=" * 64
    print(bar)
    print("  Prime multiplier -> SAT formula")
    print(bar)
    print(f"  p = {p:<6}  binary: {p:0{n}b}")
    print(f"  q = {q:<6}  binary: {q:0{n}b}")
    print(f"  p x q = {product}  binary: {product:0{m}b}")
    print()
    print(f"  Bit width : {n}-bit inputs, {m}-bit output")
    print()
    print("  Live gates in circuit (partial constant folding applied):")
    print(f"    AND : {gc['AND']}")
    print(f"    OR  : {gc['OR']}")
    print(f"    NOT : {gc['NOT']}")
    print(f"    Total : {sum(gc.values())}")
    print()
    print(f"  Input variables  : {r['input_vars']}  "
          f"(p0...p{n-1}, q0...q{n-1})")
    print(f"  Auxiliary vars   : {r['aux_vars']}")
    print(f"  Total SAT vars   : {r['var_count']}")
    print(f"  Total clauses    : {len(r['clauses'])}")
    print()
    print("  Formula (CNF -- each line is a clause; full formula = AND of all):")
    print("-" * 64)
    print(r["formula"])
    print()
    print("  DIMACS-style clause dict  (variable index map shown first):")
    print("-" * 64)
    vi = r["var_index"]
    print("  Variable index: " + ", ".join(f"{name}={idx}" for name, idx in vi.items()))
    print()
    cd = r["clause_dict"]
    for i, lits in cd.items():
        print(f"  {i}: {lits}")
    print(bar)


# # ---------------------------------------------------------------------------
# # 8.  CLI
# # ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     args  = [a for a in sys.argv[1:] if not a.startswith("--")]
#     flags = {a for a in sys.argv[1:] if a.startswith("--")}
#     raw   = "--raw" in flags

#     if len(args) == 2:
#         try:
#             p, q = int(args[0]), int(args[1])
#         except ValueError:
#             print("Usage: python prime_multiplier_sat.py <prime1> <prime2> [--raw]")
#             sys.exit(1)
#         generate(p, q, verbose=not raw, raw=raw)

#     else:
#         for p, q in [(3, 5), (7, 11), (13, 17)]:
#             generate(p, q, verbose=True)
#             print()