"""
factoring_to_3sat.py
====================
Reduces integer factoring to 3-SAT and emits a DIMACS .cnf file.

Pipeline
--------
1.  Allocate Boolean variables for the bits of unknown factors p and q.
2.  Build an array multiplier circuit (AND gates + half/full adders).
3.  Encode every gate via the Tseitin transformation: CNF with <= 3 literals/clause.
4.  Pad 1- and 2-literal clauses to exactly 3 by duplicating the last literal
    (semantically equivalent: (a v a) = a, (a v b v b) = (a v b)).
5.  Fix the output wires of the multiplier to the known bits of N.

Any satisfying assignment decodes as a factorisation p * q = N.

Usage
-----
    python factoring_to_3sat.py <N>              # DIMACS to stdout
    python factoring_to_3sat.py <N> out.cnf      # DIMACS to file
    python factoring_to_3sat.py --demo           # self-test on small numbers

Solving the output
------------------
Feed the .cnf file to any DIMACS-compatible SAT solver, e.g.:
    minisat out.cnf solution.txt
    kissat  out.cnf
    cadical out.cnf

Interpreting the solution
-------------------------
The solver outputs a space-separated list of signed integers (positive = TRUE,
negative = FALSE).  Variables p_vars[0..m-1] encode p (LSB first);
q_vars[0..m-1] encode q (LSB first).  See decode_assignment() below.
"""

import sys


# ---------------------------------------------------------------------------
#  SAT builder
# ---------------------------------------------------------------------------

class SATBuilder:
    """
    Accumulates Boolean variables, strict 3-literal clauses, and gate
    definitions for circuit simulation.

    Variables  : positive integers 1, 2, 3, ...  (DIMACS convention)
    Literal    : +v (TRUE) | -v (FALSE)
    Clause     : disjunction of exactly 3 literals

    Gate record: stored as (type_str, input_a, input_b, output_var) for
    direct circuit evaluation -- all indices are positive variable IDs.
    """

    def __init__(self):
        self._nvars: int = 0
        self.clauses: list = []
        self._gates: list = []          # (type, a, b, z)

    # -- Variable allocation ------------------------------------------------

    def new_var(self) -> int:
        self._nvars += 1
        return self._nvars

    def new_vars(self, n: int) -> list:
        return [self.new_var() for _ in range(n)]

    @property
    def num_vars(self) -> int:
        return self._nvars

    # -- Clause addition ----------------------------------------------------

    def add_clause(self, *lits) -> None:
        """
        Add a clause of 1-3 literals.  Short clauses are padded to exactly 3
        by duplicating the last literal -- semantically equivalent:
            (a)       == (a v a v a)
            (a v b)   == (a v b v b)
        """
        clause = list(lits)
        assert 1 <= len(clause) <= 3, f"Expected 1-3 literals, got {clause}"
        while len(clause) < 3:
            clause.append(clause[-1])
        self.clauses.append(clause)

    # -- Gate encodings (Tseitin transformation) ----------------------------

    def gate_and(self, x: int, y: int) -> int:
        """z = x AND y  ->  3 clauses"""
        z = self.new_var()
        self._gates.append(('and', x, y, z))
        self.add_clause(-x, -y,  z)   # x ^ y -> z
        self.add_clause( x,     -z)   # z -> x  (binary, padded)
        self.add_clause( y,     -z)   # z -> y
        return z

    def gate_or(self, x: int, y: int) -> int:
        """z = x OR y  ->  3 clauses"""
        z = self.new_var()
        self._gates.append(('or', x, y, z))
        self.add_clause( x,  y, -z)   # z -> x v y
        self.add_clause(-x,      z)   # x -> z  (binary, padded)
        self.add_clause(-y,      z)   # y -> z
        return z

    def gate_xor(self, x: int, y: int) -> int:
        """
        z = x XOR y  ->  4 clauses (all already exactly 3 literals).

        Derived from truth table -- forbidden rows: (0,0,1)(0,1,0)(1,0,0)(1,1,1)
        Clauses:  x v y v -z,  x v -y v z,  -x v y v z,  -x v -y v -z
        """
        z = self.new_var()
        self._gates.append(('xor', x, y, z))
        self.add_clause( x,  y, -z)
        self.add_clause( x, -y,  z)
        self.add_clause(-x,  y,  z)
        self.add_clause(-x, -y, -z)
        return z

    # -- Adder building blocks ----------------------------------------------

    def half_adder(self, x: int, y: int):
        """Returns (sum_bit, carry_bit)."""
        return self.gate_xor(x, y), self.gate_and(x, y)

    def full_adder(self, x: int, y: int, cin: int):
        """
        Returns (sum_bit, carry_out_bit).
        Two cascaded half-adders:
            s1, c1 = HA(x, y)
            s,  c2 = HA(s1, cin)
            cout   = c1 OR c2
        """
        s1, c1 = self.half_adder(x, y)
        s,  c2 = self.half_adder(s1, cin)
        cout   = self.gate_or(c1, c2)
        return s, cout

    # -- Constant assignment ------------------------------------------------

    def fix_var(self, v: int, bit: int) -> None:
        """Force variable v to Boolean value bit in {0, 1}."""
        self.add_clause(v if bit else -v)

    # -- Circuit simulation -------------------------------------------------

    def evaluate(self, seed: dict) -> dict:
        """
        Given values for input variables (seed dict: var -> bool),
        propagate through all recorded gates in topological (creation) order
        to produce a complete variable assignment.

        This is exact and requires no search: every gate output is fully
        determined by its two inputs.
        """
        vals = dict(seed)
        for gtype, a, b, z in self._gates:
            va, vb = vals[a], vals[b]
            if   gtype == 'and': vals[z] = va and vb
            elif gtype == 'or':  vals[z] = va or  vb
            elif gtype == 'xor': vals[z] = va ^   vb
        return vals

    # -- DIMACS output ------------------------------------------------------

    def to_dimacs(self, comments: str = "") -> str:
        lines = []
        for line in comments.splitlines():
            lines.append(f"c {line}")
        lines.append(f"p cnf {self._nvars} {len(self.clauses)}")
        for clause in self.clauses:
            lines.append(" ".join(map(str, clause)) + " 0")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Array multiplier
# ---------------------------------------------------------------------------

def build_array_multiplier(sat: SATBuilder,
                           p_bits: list,
                           q_bits: list) -> list:
    """
    Encode  product = p * q  using an array multiplier.

    p_bits, q_bits : SAT variable lists, length m, LSB first.
    Returns        : list of 2m SAT variables (product bits, LSB first).

    Phase 1 - partial products
        pp[i][j] = p[i] AND q[j]  ->  column i+j

    Phase 2 - left-to-right column reduction
        Full adders consume triples; half adders consume pairs.
        Carries spill into the next column.
    """
    m = len(p_bits)
    assert len(q_bits) == m

    pp = [[sat.gate_and(p_bits[i], q_bits[j]) for j in range(m)]
          for i in range(m)]

    columns = [[] for _ in range(2 * m)]
    for i in range(m):
        for j in range(m):
            columns[i + j].append(pp[i][j])

    carries = [[] for _ in range(2 * m + 1)]
    out_bits = []

    for k in range(2 * m):
        bits = columns[k] + carries[k]

        while len(bits) >= 3:
            a, b, c = bits[0], bits[1], bits[2]
            bits = bits[3:]
            s, co = sat.full_adder(a, b, c)
            bits.append(s)
            carries[k + 1].append(co)

        if len(bits) == 2:
            a, b = bits[0], bits[1]
            s, co = sat.half_adder(a, b)
            bits = [s]
            carries[k + 1].append(co)

        if bits:
            out_bits.append(bits[0])
        else:
            z = sat.new_var()
            sat.fix_var(z, 0)
            out_bits.append(z)

    return out_bits


# ---------------------------------------------------------------------------
#  Main reduction: Factoring -> 3-SAT
# ---------------------------------------------------------------------------

def factoring_to_3sat(N: int):
    """
    Build a 3-SAT instance encoding  p * q = N.

    Returns (sat, p_vars, q_vars).

    Decoding a solution
    -------------------
    Given satisfying assignment A (var -> bool):
        p = sum(A[p_vars[i]] * 2**i for i in range(m))
        q = sum(A[q_vars[i]] * 2**i for i in range(m))
    """
    n = N.bit_length()
    m = (n + 1) // 2       # each factor gets ceil(n/2) bits

    sat = SATBuilder()
    p_vars = sat.new_vars(m)
    q_vars = sat.new_vars(m)

    out_bits = build_array_multiplier(sat, p_vars, q_vars)

    for k in range(2 * m):
        sat.fix_var(out_bits[k], (N >> k) & 1)

    return sat, p_vars, q_vars


def decode_assignment(assignment: dict, p_vars: list, q_vars: list):
    """Recover integer factors from a satisfying assignment (var -> bool)."""
    p = sum(int(assignment[v]) << i for i, v in enumerate(p_vars))
    q = sum(int(assignment[v]) << i for i, v in enumerate(q_vars))
    return p, q


# ---------------------------------------------------------------------------
#  Verification via direct gate simulation
# ---------------------------------------------------------------------------

def verify(N: int, verbose: bool = True) -> bool:
    """
    Build the 3-SAT encoding for N and verify it accepts the known
    factorisation by direct gate simulation (no SAT solver needed).

    Steps:
      1. Find a factor pair (p_true, q_true) by trial division.
      2. Seed input variables with the factor bits.
      3. Propagate all gates deterministically.
      4. Check every clause in the formula.
    """
    import math

    p_true, q_true = None, None
    for d in range(2, math.isqrt(N) + 1):
        if N % d == 0:
            p_true, q_true = d, N // d
            break

    sat, p_vars, q_vars = factoring_to_3sat(N)

    if p_true is None:
        if verbose:
            print(f"  N={N:>8}  prime (UNSAT expected)  "
                  f"vars={sat.num_vars}  clauses={len(sat.clauses)}")
        return True

    # Seed input bits
    seed = {}
    for i, v in enumerate(p_vars):
        seed[v] = bool((p_true >> i) & 1)
    for i, v in enumerate(q_vars):
        seed[v] = bool((q_true >> i) & 1)

    # Propagate through all gates
    assignment = sat.evaluate(seed)

    # Check all clauses
    ok = True
    for clause in sat.clauses:
        satisfied = any(
            (assignment.get(abs(lit), False) if lit > 0
             else not assignment.get(abs(lit), True))
            for lit in clause
        )
        if not satisfied:
            ok = False
            if verbose:
                print(f"    UNSATISFIED clause: {clause}")

    if verbose:
        status = "PASS" if ok else "FAIL"
        print(f"  N={N:>9}  =  {p_true:>6} x {q_true:<7}"
              f"  vars={sat.num_vars:>5}  clauses={len(sat.clauses):>6}"
              f"  literals={3*len(sat.clauses):>7}  [{status}]")
    return ok


# ---------------------------------------------------------------------------
#  Demo / self-test
# ---------------------------------------------------------------------------

def run_demo() -> None:
    print("=" * 78)
    print("Factoring -> 3-SAT  |  self-test (direct gate simulation)")
    print("=" * 78)
    print(f"  {'N':>9}  factorisation               vars  clauses  literals  result")
    print("-" * 78)

    test_cases = [
        (3,    3),
        (5,    7),
        (11,   13),
        (17,   19),
        (23,   29),
        (97,   101),
        (257,  263),
        (1009, 1013),
        (7919, 7927),
    ]

    all_ok = all(verify(p * q) for p, q in test_cases)
    print("-" * 78)
    print("All tests passed." if all_ok else "SOME TESTS FAILED.")
    print()

    # Scaling table
    print("Formula size as n (total product bits) grows:")
    print(f"  {'n':>8}  {'m=ceil(n/2)':>12}  {'vars':>8}  {'clauses':>10}  {'literals':>10}")
    print("  " + "-" * 54)
    for n in [8, 16, 32, 40, 64, 128, 256]:
        m = (n + 1) // 2
        p_dummy = (1 << (m - 1)) | 1
        q_dummy = (1 << (m - 1)) | 3
        sat, _, _ = factoring_to_3sat(p_dummy * q_dummy)
        print(f"  {n:>8}  {m:>12}  {sat.num_vars:>8}  "
              f"{len(sat.clauses):>10}  {3*len(sat.clauses):>10}")
    print()
    print("Rule of thumb:  literals ~= 22.5 * n^2  for large n")


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if args[0] == "--demo":
        run_demo()
        sys.exit(0)

    N = int(args[0])
    if N < 4:
        print("Error: N must be >= 4.", file=sys.stderr)
        sys.exit(1)

    sat, p_vars, q_vars = factoring_to_3sat(N)

    n = N.bit_length()
    m = (n + 1) // 2
    stats = (
        f"Factoring N = {N}  ({n} bits)\n"
        f"Factor bit-width      : {m} bits each\n"
        f"Variables             : {sat.num_vars}\n"
        f"Clauses               : {len(sat.clauses)}\n"
        f"Literals (x3/clause)  : {3 * len(sat.clauses)}\n"
        f"p vars LSB->MSB       : {p_vars}\n"
        f"q vars LSB->MSB       : {q_vars}"
    )
    print(stats, file=sys.stderr)

    dimacs = sat.to_dimacs(comments=stats)
    if len(args) >= 2:
        with open(args[1], "w") as fh:
            fh.write(dimacs + "\n")
        print(f"DIMACS written to '{args[1]}'", file=sys.stderr)
    else:
        print(dimacs)


if __name__ == "__main__":
    main()