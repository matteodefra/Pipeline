#!/usr/bin/env python3
"""
Literal-conscious strict CNF for factoring via Dadda multiplier.

Given primes p,q (same bit-size), compute N=p*q, then output a CNF over unknown
factor bits A,B (nbits each) such that A*B = N.

Key points:
- Strict DIMACS CNF only.
- Dadda column compression (typically fewer adders than Wallace).
- Exact full adder encoding (IMPORTANT).
- Constant propagation during generation (avoid creating clauses for constants).

Run:
  python3 dadda_factoring_to_cnf.py --p 1019 --q 1237 -o out.cnf
Optional:
  --no-odd   (do not force LSB=1)
  --no-msb   (do not force MSB=1)
  --verify-small (bruteforce check for nbits<=12)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import argparse
import itertools
import math


# ---------- CNF infra ----------

@dataclass
class CNF:
    nvars: int
    clauses: List[List[int]]
    comments: List[str]

    def add_clause(self, lits: List[int]) -> None:
        # Remove zeros; drop tautologies; keep duplicates minimal
        lits = [l for l in lits if l != 0]
        s = set(lits)
        for l in lits:
            if -l in s:
                return
        # Remove duplicate literals (safe)
        if len(lits) > 1:
            lits = list(dict.fromkeys(lits))
        self.clauses.append(lits)

    def add_unit(self, lit: int) -> None:
        self.add_clause([lit])

    def literal_count(self) -> int:
        return sum(len(c) for c in self.clauses)

    def to_dimacs(self) -> str:
        out = []
        for c in self.comments:
            out.append(f"c {c}")
        out.append(f"p cnf {self.nvars} {len(self.clauses)}")
        for cl in self.clauses:
            out.append(" ".join(map(str, cl)) + " 0")
        return "\n".join(out)


class VarPool:
    def __init__(self) -> None:
        self.next_var = 1

    def new(self) -> int:
        v = self.next_var
        self.next_var += 1
        return v

    def reserve(self, k: int) -> List[int]:
        return [self.new() for _ in range(k)]


# ---------- 3-valued "signal" representation for constant propagation ----------

# A signal is either:
#  - None: constant 0
#  - -1:   constant 1
#  - >=1:  a CNF variable id
Sig = Optional[int]  # None=0, -1=1, else var id


def is_const0(x: Sig) -> bool:
    return x is None

def is_const1(x: Sig) -> bool:
    return x == -1

def is_var(x: Sig) -> bool:
    return x is not None and x != -1

def lit_of_sig(x: Sig, sign: int = 1) -> int:
    """
    Return a literal representing (x == 1) if sign=+1, or (x == 0) if sign=-1,
    but only valid when x is a var.
    """
    assert is_var(x)
    return sign * int(x)


# ---------- Gate encodings with constant propagation ----------

def equate(cnf: CNF, a: Sig, b: Sig) -> Sig:
    """Enforce a == b, return a representative signal."""
    if is_const0(a) and is_const0(b):
        return None
    if is_const1(a) and is_const1(b):
        return -1
    if is_const0(a) and is_const1(b):
        cnf.add_clause([])  # UNSAT
        return None
    if is_const1(a) and is_const0(b):
        cnf.add_clause([])  # UNSAT
        return None
    if is_var(a) and is_const0(b):
        cnf.add_unit(-lit_of_sig(a))
        return None
    if is_var(a) and is_const1(b):
        cnf.add_unit(lit_of_sig(a))
        return -1
    if is_const0(a) and is_var(b):
        cnf.add_unit(-lit_of_sig(b))
        return None
    if is_const1(a) and is_var(b):
        cnf.add_unit(lit_of_sig(b))
        return -1
    # both vars
    assert is_var(a) and is_var(b)
    va, vb = int(a), int(b)
    cnf.add_clause([-va, vb])
    cnf.add_clause([va, -vb])
    return a


def enc_and(cnf: CNF, vp: VarPool, x: Sig, y: Sig) -> Sig:
    """Return v = x AND y, adding exact CNF, with constant propagation."""
    if is_const0(x) or is_const0(y):
        return None
    if is_const1(x):
        return y
    if is_const1(y):
        return x
    # both vars
    v = vp.new()
    xv, yv = int(x), int(y)
    # v <-> (x & y): 3 clauses
    cnf.add_clause([-xv, -yv, v])
    cnf.add_clause([xv, -v])
    cnf.add_clause([yv, -v])
    return v


def enc_xor2(cnf: CNF, vp: VarPool, a: Sig, b: Sig) -> Sig:
    """Return s = a XOR b, exact CNF, with constant propagation."""
    if is_const0(a):
        return b
    if is_const0(b):
        return a
    if is_const1(a):
        # 1 xor b = not b
        if is_const0(b):
            return -1
        if is_const1(b):
            return None
        # introduce a NOT by using a fresh var with equality to negation costs clauses;
        # cheaper: represent negation as a literal, but our Sig can't store negated var.
        # So: create v = NOT b with 2 clauses.
        v = vp.new()
        bv = int(b)
        cnf.add_clause([-v, -bv])
        cnf.add_clause([v, bv])
        return v
    if is_const1(b):
        return enc_xor2(cnf, vp, b, a)

    # both vars: 4 clauses
    s = vp.new()
    av, bv = int(a), int(b)
    cnf.add_clause([-av, -bv, -s])
    cnf.add_clause([-av,  bv,  s])
    cnf.add_clause([ av, -bv,  s])
    cnf.add_clause([ av,  bv, -s])
    return s


def enc_maj3(cnf: CNF, vp: VarPool, a: Sig, b: Sig, c: Sig) -> Sig:
    """Return m = majority(a,b,c) = (ab) ∨ (ac) ∨ (bc), exact CNF, with propagation."""
    # Constant cases
    ones = sum(1 for z in (a,b,c) if is_const1(z))
    zeros = sum(1 for z in (a,b,c) if is_const0(z))
    vars_ = [z for z in (a,b,c) if is_var(z)]

    if ones >= 2:
        return -1
    if zeros >= 2:
        return None
    if ones == 1 and zeros == 1:
        # majority(1,0,x) = x
        return vars_[0]
    if ones == 1 and len(vars_) == 2:
        # majority(1,x,y) = x OR y
        # Encode v <-> (x ∨ y) using AND/NOT is expensive; do direct 3-clause encoding:
        # v -> (x ∨ y): (¬v ∨ x ∨ y)
        # x -> v: (¬x ∨ v)
        # y -> v: (¬y ∨ v)
        x, y = int(vars_[0]), int(vars_[1])
        v = vp.new()
        cnf.add_clause([-v, x, y])
        cnf.add_clause([-x, v])
        cnf.add_clause([-y, v])
        return v
    if zeros == 1 and len(vars_) == 2:
        # majority(0,x,y) = x AND y
        return enc_and(cnf, vp, vars_[0], vars_[1])

    # All vars
    assert len(vars_) == 3
    av, bv, cv = int(a), int(b), int(c)
    m = vp.new()
    # (ab -> m), (ac -> m), (bc -> m)
    cnf.add_clause([-av, -bv, m])
    cnf.add_clause([-av, -cv, m])
    cnf.add_clause([-bv, -cv, m])
    # (m -> at least two inputs true) as CNF:
    # (¬m ∨ a ∨ b) ∧ (¬m ∨ a ∨ c) ∧ (¬m ∨ b ∨ c)
    cnf.add_clause([-m, av, bv])
    cnf.add_clause([-m, av, cv])
    cnf.add_clause([-m, bv, cv])
    return m


def enc_full_adder(cnf: CNF, vp: VarPool, a: Sig, b: Sig, cin: Sig) -> Tuple[Sig, Sig]:
    """
    Exact full adder:
      sum = a xor b xor cin
      cout = majority(a,b,cin)

    Implemented as:
      t = a xor b
      sum = t xor cin
      cout = maj(a,b,cin)

    Exact strict CNF, with constant propagation.
    """
    t = enc_xor2(cnf, vp, a, b)
    s = enc_xor2(cnf, vp, t, cin)
    cout = enc_maj3(cnf, vp, a, b, cin)
    return s, cout


# ---------- Dadda compression ----------

def dadda_targets(max_height: int) -> List[int]:
    """
    Dadda target heights:
      start d=2, then d_{k+1} = floor(1.5 * d_k) until >= max_height
    Return list of targets in reverse order for stages, ending with 2.
    """
    ds = [2]
    while ds[-1] < max_height:
        ds.append(int(math.floor(1.5 * ds[-1])))
    # stages go from largest target down to 2 (excluding last which is 2)
    return list(reversed(ds[:-1]))  # e.g., [d_k, ..., d_2] where final target is 2


def dadda_compress_columns(cnf: CNF, vp: VarPool, cols: List[List[Sig]]) -> None:
    """
    In-place Dadda compression:
    cols[k] contains bits of weight k (Sig's).
    After completion, each column has height <= 2.
    """
    # remove const0 from columns immediately
    for k in range(len(cols)):
        cols[k] = [x for x in cols[k] if not is_const0(x)]

    max_h = max((len(col) for col in cols), default=0)
    for target in dadda_targets(max_h):
        # For each column, reduce height to <= target
        for k in range(len(cols)):
            # refresh: drop const0 that may appear by propagation
            cols[k] = [x for x in cols[k] if not is_const0(x)]
            while len(cols[k]) > target:
                # Dadda choice: if we are over target by >=2, use full adder (reduce by 2 locally);
                # else use half-adder-like reduction (reduce by 1 locally).
                over = len(cols[k]) - target
                if over >= 2:
                    x = cols[k].pop()
                    y = cols[k].pop()
                    z = cols[k].pop()
                    s, c = enc_full_adder(cnf, vp, x, y, z)
                    cols[k].append(s)
                    if k + 1 >= len(cols):
                        cols.append([])
                    cols[k + 1].append(c)
                else:
                    # need reduce by 1: use a full adder with a constant 0 is a half-adder
                    # sum = x xor y, carry = x & y
                    x = cols[k].pop()
                    y = cols[k].pop()
                    s = enc_xor2(cnf, vp, x, y)
                    c = enc_and(cnf, vp, x, y)
                    cols[k].append(s)
                    if k + 1 >= len(cols):
                        cols.append([])
                    cols[k + 1].append(c)

    # final cleanup
    for k in range(len(cols)):
        cols[k] = [x for x in cols[k] if not is_const0(x)]


# ---------- Main construction ----------

def bits_of_int(x: int, nbits: int) -> List[int]:
    return [(x >> i) & 1 for i in range(nbits)]


def build_factoring_cnf(p: int, q: int, nbits: int, force_odd: bool, force_msb: bool) -> CNF:
    N = p * q
    vp = VarPool()
    cnf = CNF(nvars=0, clauses=[], comments=[])

    # Unknown factor bits, LSB..MSB
    A_vars = vp.reserve(nbits)
    B_vars = vp.reserve(nbits)

    A: List[Sig] = [v for v in A_vars]
    B: List[Sig] = [v for v in B_vars]

    cnf.comments.append(f"Factoring CNF: enforce A*B = N, with nbits={nbits}")
    cnf.comments.append(f"Given p={p}, q={q}, N={N} (0x{N:x})")
    cnf.comments.append(f"A bits (LSB..MSB): {A_vars[0]}..{A_vars[-1]}")
    cnf.comments.append(f"B bits (LSB..MSB): {B_vars[0]}..{B_vars[-1]}")

    if force_odd:
        cnf.add_unit(A_vars[0])  # A0=1
        cnf.add_unit(B_vars[0])  # B0=1
        A[0] = -1
        B[0] = -1
        cnf.comments.append("Forced A[0]=1 and B[0]=1 (odd factors).")

    if force_msb:
        cnf.add_unit(A_vars[-1])  # MSB=1
        cnf.add_unit(B_vars[-1])
        A[-1] = -1
        B[-1] = -1
        cnf.comments.append("Forced A[MSB]=1 and B[MSB]=1 (same-bit-size normalization).")

    # Columns for partial products
    # Weight range for nbits x nbits product: 0..(2*nbits-2); plus final carry => up to (2*nbits-1)
    max_w = 2 * nbits - 2
    cols: List[List[Sig]] = [[] for _ in range(max_w + 1)]

    # Partial products: pp_ij = A[i] & B[j]
    for i in range(nbits):
        ai = A[i]
        for j in range(nbits):
            bj = B[j]
            pij = enc_and(cnf, vp, ai, bj)  # propagates constants
            cols[i + j].append(pij)

    # Dadda compress to height <= 2
    dadda_compress_columns(cnf, vp, cols)

    # Build two rows R0 and R1 from columns
    # If a column has 0 bits -> 0; 1 bit -> R0; 2 bits -> R0,R1
    R0: List[Sig] = []
    R1: List[Sig] = []
    for k in range(len(cols)):
        col = [x for x in cols[k] if not is_const0(x)]
        if len(col) == 0:
            R0.append(None)
            R1.append(None)
        elif len(col) == 1:
            R0.append(col[0])
            R1.append(None)
        elif len(col) == 2:
            R0.append(col[0])
            R1.append(col[1])
        else:
            raise RuntimeError("Dadda compression failed: column height > 2")

    # Final ripple add R0 + R1 into product bits P[0..2*nbits-1]
    P_bits = 2 * nbits
    P: List[Sig] = [vp.new() for _ in range(P_bits)]
    cnf.comments.append(f"Product bits P[0..{P_bits-1}] are vars {P[0]}..{P[-1]} (LSB..MSB).")

    carry: Sig = None
    # We only have defined columns 0..len(R0)-1 == 0..(2*nbits-2). The MSB P[2n-1] is final carry.
    for k in range(P_bits - 1):
        a = R0[k] if k < len(R0) else None
        b = R1[k] if k < len(R1) else None
        s, carry = enc_full_adder(cnf, vp, a, b, carry)
        # enforce P[k] == s
        equate(cnf, P[k], s)

    # Last product bit is carry
    equate(cnf, P[P_bits - 1], carry)

    # Constrain P to equal constant N
    N_bits = bits_of_int(N, P_bits)
    for k, bit in enumerate(N_bits):
        if bit == 1:
            cnf.add_unit(int(P[k]))
        else:
            cnf.add_unit(-int(P[k]))

    cnf.comments.append("Fixed P == N by unit clauses.")

    cnf.nvars = vp.next_var - 1
    return cnf


# ---------- Optional small verification by brute force ----------

def brute_verify(cnf: CNF, nbits: int, N: int) -> bool:
    """
    Bruteforce check satisfiability for small nbits by enumerating A,B assignments.
    Assumes the first 2*nbits variables are A then B (as constructed).
    """
    A_start = 1
    B_start = 1 + nbits
    # Extract unit constraints on A/B if present (best-effort)
    # We'll just enumerate all A,B and check if any assignment can satisfy all clauses.
    # This is slow, keep nbits small.
    def eval_clause(cl: List[int], assignment: Dict[int, bool]) -> bool:
        for lit in cl:
            v = abs(lit)
            val = assignment.get(v, False)
            if (lit > 0 and val) or (lit < 0 and not val):
                return True
        return False

    # Enumerate A,B, and greedily try to extend to internal vars by brute force is too big.
    # Instead: check existence of A,B that matches N and respects forced A/B units.
    # This verifies that the CNF is not obviously inconsistent with the true factors,
    # not a full SAT check.
    #
    # For a *full* check you'd run a SAT solver; this function is a sanity check only.
    for A in range(1 << nbits):
        for B in range(1 << nbits):
            if A * B != N:
                continue
            assign: Dict[int, bool] = {}
            for i in range(nbits):
                assign[A_start + i] = bool((A >> i) & 1)
                assign[B_start + i] = bool((B >> i) & 1)
            # Check only clauses that mention A/B vars only (sanity)
            ok = True
            for cl in cnf.clauses:
                if all(abs(lit) <= 2 * nbits for lit in cl):
                    if not eval_clause(cl, assign):
                        ok = False
                        break
            if ok:
                return True
    return False


# ---------- CLI ----------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--p", type=int, required=True)
    ap.add_argument("--q", type=int, required=True)
    ap.add_argument("--nbits", type=int, default=0, help="default = bit_length(p) (requires p,q same size)")
    ap.add_argument("--no-odd", action="store_true", help="do NOT force A[0]=B[0]=1")
    ap.add_argument("--no-msb", action="store_true", help="do NOT force A[MSB]=B[MSB]=1")
    ap.add_argument("--verify-small", action="store_true", help="sanity-check A/B units for nbits<=12")
    ap.add_argument("-o", "--out", type=str, default="factoring_dadda.cnf")
    args = ap.parse_args()

    p, q = args.p, args.q
    if p <= 1 or q <= 1:
        raise SystemExit("p,q must be > 1")

    nbits = args.nbits if args.nbits > 0 else p.bit_length()
    if p.bit_length() != nbits or q.bit_length() != nbits:
        raise SystemExit("p and q must have the same bit-length (or pass --nbits matching both).")

    cnf = build_factoring_cnf(
        p=p,
        q=q,
        nbits=nbits,
        force_odd=not args.no_odd,
        force_msb=not args.no_msb,
    )

    with open(args.out, "w") as f:
        f.write(cnf.to_dimacs() + "\n")

    print(f"Wrote: {args.out}")
    print(f"vars={cnf.nvars} clauses={len(cnf.clauses)} total_literals={cnf.literal_count()}")

    if args.verify_small and nbits <= 12:
        ok = brute_verify(cnf, nbits=nbits, N=p*q)
        print(f"Sanity check (A/B-only clauses consistent with true factors): {ok}")
    elif args.verify_small:
        print("verify-small skipped (nbits>12). Use an actual SAT solver instead.")

if __name__ == "__main__":
    main()