# gRPC and REST invocation

## gRPC (LP / MILP / QP)

Prefer the Python API with an explicit, cancelable server job:

```python
from cuopt.grpc.linear_programming import Client

client = Client("host.openshell.internal", 5001, tls=False)
```

See `references/async-grpc-python.md` for the submit/wait/result/delete
lifecycle. Build the model using the vendored
`cuopt-numerical-optimization-api-python` skill.

If that import is unavailable in the installed cuOpt build, use
`references/remote-execution-fallback.md`. Do not choose the fallback when
the async client is available.

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
- Smoke: `execution_mode` + successful status
- Async solve: job ID, `JobStatus`, termination, objective, key variables
- Legacy fallback: solver status, objective, key variables, and
  `cancellation=unavailable`
