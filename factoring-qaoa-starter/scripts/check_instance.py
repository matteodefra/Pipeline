from __future__ import annotations

import argparse
import json

from factoring_qaoa.classical import (
    assignment_to_independent_set,
    decode_factors,
    solve_mis_cp_sat,
    solve_sat,
)
from factoring_qaoa.instances import build_factoring_mis
from factoring_qaoa.stats import graph_statistics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("N", type=int)
    parser.add_argument(
        "--order", choices=["clause", "sign_blocks", "alternating"], default="clause"
    )
    parser.add_argument("--solve-mis", action="store_true")
    parser.add_argument("--time-limit", type=float, default=60.0)
    args = parser.parse_args()

    instance = build_factoring_mis(args.N, occurrence_order=args.order)
    print(json.dumps(graph_statistics(instance.graph), indent=2, sort_keys=True))

    try:
        assignment = solve_sat(instance)
    except RuntimeError as exc:
        print(f"SAT solve skipped: {exc}")
        assignment = None
    if assignment is not None:
        p, q = decode_factors(instance, assignment)
        witness = assignment_to_independent_set(instance, assignment)
        print(f"SAT witness decodes as {p} x {q} = {p*q}")
        print(f"Constructed independent set: {len(witness)} / target {instance.target_alpha}")

    if args.solve_mis:
        try:
            solution = solve_mis_cp_sat(instance.graph, time_limit_s=args.time_limit)
        except RuntimeError as exc:
            print(f"CP-SAT solve skipped: {exc}")
        else:
            print(
                f"CP-SAT MIS: objective={solution.objective}, "
                f"status={solution.status}, optimal={solution.optimal}"
            )


if __name__ == "__main__":
    main()
