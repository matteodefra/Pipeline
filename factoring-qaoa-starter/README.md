# Factoring-derived MIS + QAOA starter

This repository is a small, deliberately transparent research scaffold for the graph family obtained by

1. encoding `p*q=N` as 3-SAT with an array multiplier and Tseitin clauses;
2. applying the degree-3 SAT-to-Vertex-Cover construction;
3. studying the complementary Maximum Independent Set problem with classical solvers and QAOA.

It is **not** a claim that QAOA factors efficiently. Its purpose is to make the analytical and numerical questions reproducible.

## 1. Installation

Install [`uv`](https://docs.astral.sh/uv/) and run:

```bash
uv sync --extra solvers --extra quantum --group dev
```

The lockfile created by `uv` should be committed once the environment works on your machine.

## 2. First sanity check

`N=9` gives factor width 2 and already produces a 270-vertex MIS graph, so do not attempt a full statevector simulation.

```bash
uv run python scripts/check_instance.py 9
uv run python scripts/check_instance.py 9 --solve-mis --time-limit 60
uv run pytest
```

The script prints graph counts, solves the CNF with PySAT, decodes the factors, and constructs an independent set of the theoretical target size. The optional CP-SAT run supplies an exact/anytime classical MIS baseline.

## 3. First QAOA experiment

The included `p=1` evaluator does **local light-cone calculations**, not a 270-qubit statevector. For every vertex and edge term it simulates only the radius-one neighborhood, which has at most eight qubits because the graph has maximum degree three.

```bash
uv run python scripts/run_p1.py 9 --order clause --global-iters 8
uv run python scripts/run_p1.py 9 --order sign_blocks --global-iters 8 \
  --output data/p1_sign_blocks.csv
uv run python scripts/run_p1.py 9 --order alternating --global-iters 8 \
  --output data/p1_alternating.csv
```

The current implementation prioritizes correctness and readability. Before large sweeps, group isomorphic rooted light cones and cache one calculation per motif.

## 4. Recommended research stages

### Stage A — instance validation

For every generated instance, record:

- product `N`, factor width, SAT variables and clauses;
- graph vertices, edges, degree distribution, triangle count;
- theoretical target `alpha*=sum_i m_i + M`;
- SAT witness and decoded factors;
- exact/anytime MIS result and solver time.

Never compare a quantum result against an unverified target.

### Stage B — analytical `p=1`

Write the objective as

```text
C_lambda(x) = sum_v x_v - lambda * sum_(u,v in E) x_u x_v,
```

with `lambda > 1`. For a one-layer product-mixer QAOA, classify the rooted light cones of:

- a degree-2 variable-cycle vertex;
- a degree-3 variable-cycle vertex;
- a clause vertex;
- a triangle edge;
- an occurrence edge;
- each possible variable-cycle edge type.

Use `sympy` only after the numerical local evaluator passes tests. The safest route is:

1. enumerate each distinct rooted motif;
2. build its small exact circuit symbolically;
3. simplify the expectation;
4. multiply by the motif count in the full graph;
5. compare the symbolic expression against `p1_local.py` at random angles.

### Stage C — fixed-depth numerical analysis

For `p=1,2,...`, separate two tasks:

- expected penalized MIS objective;
- exact success probability of reaching an independent set of target size.

The expectation is local and can be computed term by term. Exact global success probability is much harder and generally requires a full tensor-network contraction, logical compression, or very small surrogate instances.

### Stage D — ansatz comparison

Compare at least:

1. unconstrained QAOA with an `X` mixer and several penalty values;
2. feasibility-preserving MIS QAOA with a conditional bit-flip mixer;
3. multi-angle QAOA with parameters tied by node/edge type;
4. cycle-aware logical QAOA on the SAT-variable representation;
5. recursive QAOA that fixes one whole variable cycle at a time.

### Stage E — controls

Each factoring graph should be compared against:

- the same graph with occurrence order changed;
- degree- and triangle-preserving rewired graphs;
- random satisfiable 3-SAT reductions with similar counts;
- the direct Max-3SAT QAOA formulation;
- classical CP-SAT, SAT/MaxSAT, greedy, local-search, and message-passing baselines.

## 5. Metrics to save for every run

At minimum:

```text
instance id and random seed
ansatz and depth p
all angles and initialization method
penalty lambda
expectation value
feasibility probability
best sampled independent-set size
probability of target size
number of objective evaluations
wall-clock time
simulator/backend and numerical tolerances
```

For a single-run target probability `P_target`, report repetitions to 99% success as

```text
TTS_0.99 = ceil(log(0.01) / log(1 - P_target)).
```

Do not infer factoring performance from approximation ratio alone.

## 6. Which package is used for what?

- **NetworkX:** graph construction, attributes, neighborhoods, motif extraction.
- **PySAT:** verify satisfiability and recover a factor witness.
- **OR-Tools CP-SAT:** exact/anytime classical MIS baseline.
- **NumPy/SciPy:** exact small-light-cone simulation and angle optimization.
- **SymPy:** symbolic `p=1` expressions after the numerical pipeline is validated.
- **PennyLane:** convenient implementation of unconstrained and constrained MIS QAOA variants.
- **quimb + cotengra:** tensor-network contraction when local statevectors become too large.
- **pytest:** regression tests for every reduction and simulator change.

Use one quantum framework at first. PennyLane is included because it provides MIS cost/mixer helpers and a tensor-network backend. Add Qiskit later only when hardware execution or Qiskit-specific transpilation becomes part of the research question.

## 7. Immediate milestones

A good first sequence is:

1. reproduce the exact graph counts for factor widths 2–8;
2. verify the SAT-to-MIS witness on every instance;
3. derive and test the complete `p=1` formula;
4. compare the three occurrence orders included here;
5. implement rooted-motif caching;
6. extend the local evaluator to `p=2` using an explicit gate-level causal cone;
7. only then begin constrained, multi-angle, and recursive variants.

## Caveats

- Full factoring instances begin at hundreds of graph qubits; dense simulation is not appropriate.
- The current `p1_local.py` is specifically a one-layer evaluator. Extending it by simply taking a larger induced neighborhood is not a substitute for constructing the exact gate-level causal cone.
- The generated CNF pads short clauses by literal duplication. Those are separate occurrence vertices in the graph, as required by the reduction.
- The original reduction is a simple-graph construction; a SAT variable occurring once would create a degenerate 2-cycle. The starter rejects that case explicitly. The factoring instances of interest have larger occurrence counts.
