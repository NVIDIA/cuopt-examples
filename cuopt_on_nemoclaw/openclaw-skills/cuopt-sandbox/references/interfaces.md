# gRPC and REST invocation

## gRPC (LP / MILP / QP)

Python API with remote backend:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/solve.py'
```

Skill: `cuopt-numerical-optimization-api-python` (vendored upstream).

MPS files: `cuopt-numerical-optimization-api-cli` or host CLI if exposed.

## REST (VRP)

Port 5000, JSON payloads. Skill: `cuopt-server-api-python`.

Smoke reference: `/sandbox/smoke_vrp.py`.

## Choosing an interface

| Problem | Interface | Skill chain |
|---|---|---|
| LP, MILP, QP | gRPC + Python | `numerical-optimization-formulation` → `cuopt-numerical-optimization-api-python` |
| VRP, TSP, PDP | REST | `routing-formulation` → `cuopt-routing-api-python` → `cuopt-server-api-python` |

Default for MILP scheduling in this sandbox: **gRPC Python** on port 5001.
Use REST only when the user explicitly wants the server JSON workflow.

## Evidence to report

- Probe `available:` line
- Smoke: `Using remote GPU backend` + status
- Solve: `Problem.Status.name`, objective, key assignment vars
