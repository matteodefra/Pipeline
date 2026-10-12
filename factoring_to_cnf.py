#!/usr/bin/env python3
"""
Factoring-to-CNF generator (strict DIMACS CNF).
Given primes p, q (same bit-size), builds CNF over unknown A,B such that A*B = N.

Architecture:
- Partial products a_i AND b_j
- Wallace-style column compression with full adders (3->2)
- Final ripple addition of the remaining two rows

Encodings:
- AND: 3 clauses for v <-> (x & y)
- Full adder: 7 clauses for (a,b,cin) -> (s,cout) without extra aux vars
  (clauses as in common compact encodings; see e.g. Sinz 2005 discussion / reproduced in theses).
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


@dataclass
class CNF:
    nvars: int
    clauses: List[List[int]]
    comments: List[str]

    def add_clause(self, lits: List[int]) -> None:
        # remove zeros and duplicates conservatively
        lits = [l for l in lits if l != 0]
        # trivial tautology check (x v ~x)
        s = set(lits)
        for l in lits:
            if -l in s:
                return
        self.clauses.append(lits)

    def add_unit(self, lit: int) -> None:
        self.add_clause([lit])

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


def enc_and(cnf: CNF, x: int, y: int, v: int) -> None:
    # v <-> (x & y)
    # (¬x ∨ ¬y ∨ v) ∧ (x ∨ ¬v) ∧ (y ∨ ¬v)
    cnf.add_clause([-x, -y, v])
    cnf.add_clause([x, -v])
    cnf.add_clause([y, -v])


def enc_full_adder_7(cnf: CNF, a: int, b: int, cin: int, s: int, cout: int) -> None:
    """
    Full adder:
      s = a xor b xor cin
      cout = majority(a,b,cin)

    7-clause compact CNF (no aux vars), commonly used in SAT encodings.
    Clauses:
      (a ∨ b ∨ ¬cin ∨ s)
      (a ∨ ¬b ∨ cin ∨ s)
      (¬a ∨ b ∨ cin ∨ s)
      (¬a ∨ ¬b ∨ ¬cin ∨ s)
      (¬a ∨ ¬b ∨ cout)
      (¬a ∨ ¬cin ∨ cout)
      (¬b ∨ ¬cin ∨ cout)
    """
    cnf.add_clause([ a,  b, -cin,  s])
    cnf.add_clause([ a, -b,  cin,  s])
    cnf.add_clause([-a,  b,  cin,  s])
    cnf.add_clause([-a, -b, -cin,  s])
    cnf.add_clause([-a, -b,  cout])
    cnf.add_clause([-a, -cin, cout])
    cnf.add_clause([-b, -cin, cout])


def enc_half_adder(cnf: CNF, a: int, b: int, s: int, c: int, vp: VarPool) -> None:
    """
    Half adder via one AND + one XOR (XOR as 4 clauses).
    This is used only at the very end if needed.
    """
    # c = a & b
    enc_and(cnf, a, b, c)
    # s = a xor b (4 clauses)
    cnf.add_clause([-a, -b, -s])
    cnf.add_clause([-a,  b,  s])
    cnf.add_clause([ a, -b,  s])
    cnf.add_clause([ a,  b, -s])


def bits_of_int(x: int, nbits: int) -> List[int]:
    return [(x >> i) & 1 for i in range(nbits)]


def factoring_cnf_for_product(N: int, nbits: int, force_odd: bool = True, force_msb: bool = True) -> CNF:
    """
    Create CNF over unknown A,B each nbits, enforcing A*B = N (where N fits in 2*nbits bits).
    """
    vp = VarPool()
    cnf = CNF(nvars=0, clauses=[], comments=[])

    # Factor bits (LSB first)
    A = vp.reserve(nbits)
    B = vp.reserve(nbits)

    cnf.comments.append(f"A bits (LSB..MSB): vars {A[0]}..{A[-1]}")
    cnf.comments.append(f"B bits (LSB..MSB): vars {B[0]}..{B[-1]}")

    if force_odd:
        cnf.add_unit(A[0])  # A0 = 1
        cnf.add_unit(B[0])  # B0 = 1
        cnf.comments.append("Forced A[0]=1 and B[0]=1 (odd factors)")

    if force_msb:
        cnf.add_unit(A[-1])  # top bit 1
        cnf.add_unit(B[-1])
        cnf.comments.append("Forced A[MSB]=1 and B[MSB]=1 (same bit-size normalization)")

    # Partial products p_ij = A[i] & B[j]
    pp: List[List[int]] = [[vp.new() for _ in range(nbits)] for _ in range(nbits)]
    for i in range(nbits):
        for j in range(nbits):
            enc_and(cnf, A[i], B[j], pp[i][j])

    # Columns by weight k = i+j
    max_w = 2 * nbits - 2
    cols: List[List[int]] = [[] for _ in range(max_w + 1)]
    for i in range(nbits):
        for j in range(nbits):
            cols[i + j].append(pp[i][j])

    # Wallace-style compression: while a column has >=3 bits, consume 3 with a full adder
    # producing sum in same column and carry in next column.
    for k in range(max_w + 1):
        while len(cols[k]) >= 3:
            x = cols[k].pop()
            y = cols[k].pop()
            z = cols[k].pop()
            s = vp.new()
            c = vp.new()
            enc_full_adder_7(cnf, x, y, z, s, c)
            cols[k].append(s)
            if k + 1 <= max_w:
                cols[k + 1].append(c)
            else:
                # carry beyond max_w would be overflow bit; create an extra column if needed
                cols.append([c])
                max_w += 1

    # Now each column has 0..2 bits. Interpret as two rows R0 and R1:
    # R0[k] = first bit (or 0), R1[k] = second bit (or 0)
    R0: List[Optional[int]] = [None] * (max_w + 1)
    R1: List[Optional[int]] = [None] * (max_w + 1)
    for k in range(max_w + 1):
        if len(cols[k]) >= 1:
            R0[k] = cols[k][0]
        if len(cols[k]) >= 2:
            R1[k] = cols[k][1]
        # if len == 0 => None

    # Final ripple add R0 + R1 -> P (product bits), with carry
    P: List[int] = [vp.new() for _ in range(max_w + 2)]  # includes possible top carry
    cnf.comments.append(f"Product bits P[0..{len(P)-1}] are vars {P[0]}..{P[-1]} (LSB..MSB)")

    carry = None  # carry variable (or None meaning 0)
    for k in range(max_w + 1):
        x = R0[k]
        y = R1[k]
        if x is None and y is None:
            # P[k] = carry
            if carry is None:
                # P[k] = 0 => set false
                cnf.add_unit(-P[k])
            else:
                # P[k] <-> carry (2 clauses)
                cnf.add_clause([-carry, P[k]])
                cnf.add_clause([carry, -P[k]])
            carry = None  # because both x,y are 0, next carry remains 0
        elif carry is None:
            # P[k] = x xor y ; carry = x & y
            if x is None:
                # P[k] = y
                cnf.add_clause([-y, P[k]])
                cnf.add_clause([y, -P[k]])
                carry = None
            elif y is None:
                cnf.add_clause([-x, P[k]])
                cnf.add_clause([x, -P[k]])
                carry = None
            else:
                # half adder
                c = vp.new()
                enc_half_adder(cnf, x, y, P[k], c, vp)
                carry = c
        else:
            # full adder with inputs x,y,carry (treat missing x/y as 0)
            # If x/y None, we can reduce:
            if x is None and y is None:
                # P[k] = carry, next carry = 0
                cnf.add_clause([-carry, P[k]])
                cnf.add_clause([carry, -P[k]])
                carry = None
            else:
                a = x if x is not None else None
                b = y if y is not None else None
                if a is None:
                    # full adder (0, b, carry): sum=b xor carry, cout=b & carry
                    # Use half adder
                    c = vp.new()
                    enc_half_adder(cnf, b, carry, P[k], c, vp)
                    carry = c
                elif b is None:
                    c = vp.new()
                    enc_half_adder(cnf, a, carry, P[k], c, vp)
                    carry = c
                else:
                    cout = vp.new()
                    enc_full_adder_7(cnf, a, b, carry, P[k], cout)
                    carry = cout

    # Most significant bit:
    if carry is None:
        cnf.add_unit(-P[max_w + 1])
    else:
        cnf.add_clause([-carry, P[max_w + 1]])
        cnf.add_clause([carry, -P[max_w + 1]])

    # Constrain product bits to equal N (in 2*nbits bits)
    target_bits = bits_of_int(N, max_w + 2)
    for k, bit in enumerate(target_bits):
        cnf.add_unit(P[k] if bit == 1 else -P[k])

    cnf.comments.append(f"Fixed product to N={N} (0x{N:x}) in {len(target_bits)} bits")

    cnf.nvars = vp.next_var - 1
    return cnf


def main():
    # Example usage:
    # p = 1019
    # q = 1237
    # nbits inferred as max(p,q).bit_length()
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--p", type=int, required=True)
    ap.add_argument("--q", type=int, required=True)
    ap.add_argument("--nbits", type=int, default=0, help="bit-size of factors; default = max(p,q).bit_length()")
    ap.add_argument("--no-odd", action="store_true", help="do NOT force LSB=1 for factors")
    ap.add_argument("--no-msb", action="store_true", help="do NOT force MSB=1 for factors")
    ap.add_argument("-o", "--out", type=str, default="factoring.cnf")
    args = ap.parse_args()

    p, q = args.p, args.q
    if p <= 1 or q <= 1:
        raise SystemExit("p and q must be > 1")
    N = p * q

    nbits = args.nbits if args.nbits > 0 else max(p, q).bit_length()
    if p.bit_length() != nbits or q.bit_length() != nbits:
        raise SystemExit("p and q are not the same bit-size (or nbits mismatched). Provide --nbits to force.")

    cnf = factoring_cnf_for_product(
        N=N,
        nbits=nbits,
        force_odd=not args.no_odd,
        force_msb=not args.no_msb,
    )

    dimacs = cnf.to_dimacs()
    with open(args.out, "w") as f:
        f.write(dimacs + "\n")

    print(f"Wrote {args.out}")
    print(f"vars={cnf.nvars}, clauses={len(cnf.clauses)}")
    # quick literal count
    lit_count = sum(len(c) for c in cnf.clauses)
    print(f"total_literals={lit_count}")


if __name__ == "__main__":
    main()