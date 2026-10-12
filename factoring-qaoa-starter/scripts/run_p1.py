from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution, minimize

from factoring_qaoa.instances import build_factoring_mis
from factoring_qaoa.p1_local import p1_objective


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("N", type=int)
    parser.add_argument("--penalty", type=float, default=1.25)
    parser.add_argument("--order", choices=["clause", "sign_blocks", "alternating"], default="clause")
    parser.add_argument("--global-iters", type=int, default=12)
    parser.add_argument("--output", type=Path, default=Path("data/p1_result.csv"))
    args = parser.parse_args()

    instance = build_factoring_mis(args.N, occurrence_order=args.order)

    def loss(theta: np.ndarray) -> float:
        gamma, beta = theta
        return -p1_objective(
            instance.graph, gamma, beta, penalty=args.penalty
        ).objective

    result_global = differential_evolution(
        loss,
        bounds=[(0.0, 2 * np.pi), (0.0, np.pi)],
        maxiter=args.global_iters,
        popsize=8,
        rng=0,
        polish=False,
        workers=1,
    )
    result = minimize(
        loss,
        result_global.x,
        method="L-BFGS-B",
        bounds=[(0.0, 2 * np.pi), (0.0, np.pi)],
    )
    gamma, beta = result.x
    breakdown = p1_objective(instance.graph, gamma, beta, penalty=args.penalty)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "N",
                "bit_width",
                "nodes",
                "clauses",
                "order",
                "penalty",
                "gamma",
                "beta",
                "expectation",
                "target_alpha",
                "success",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "N": args.N,
                "bit_width": instance.bit_width,
                "nodes": instance.graph.number_of_nodes(),
                "clauses": instance.num_clauses,
                "order": args.order,
                "penalty": args.penalty,
                "gamma": gamma,
                "beta": beta,
                "expectation": breakdown.objective,
                "target_alpha": instance.target_alpha,
                "success": result.success,
            }
        )

    print(f"gamma={gamma:.10f}, beta={beta:.10f}")
    print(f"p=1 expectation={breakdown.objective:.10f}")
    print(f"target independent-set size={instance.target_alpha}")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
