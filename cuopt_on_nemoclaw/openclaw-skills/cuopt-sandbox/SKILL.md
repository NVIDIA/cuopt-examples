---
name: cuopt-sandbox
version: "26.08.00"
description: Run cuOpt in the NemoClaw sandbox — probe/smoke gates, prefer cancelable Python gRPC jobs, use legacy remote execution only when that API is unavailable, then vendored cuOpt skills.
license: Apache-2.0
metadata:
  author: NVIDIA cuOpt Team
  tags:
    - cuopt
    - nemoclaw
    - sandbox
---

# cuOpt in the NemoClaw sandbox

Infrastructure for solving with cuOpt inside NemoClaw: probe/smoke gates,
capability-based gRPC execution, and handoff to vendored formulation/API skills.

## When to use

- Constructive planning from uploaded constraint data (schedule, assign,
  route, roster — any wording). See `references/intent-and-triggers.md`.
- CSV upload + plan → `optimization-from-data-orchestrator` + `references/activation.md`.
- `ImportError` / `cudaErrorInsufficientDriver`.

## Mandatory order

Complete before any assignment output, feasibility verdict, or custom
solver code:

| Step | Action | Reference |
|---|---|---|
| 0 | Probe capability → gRPC smoke | `references/grpc-connectivity-and-smoke.md` |
| 1 | Formulate | vendored `*-formulation` skills |
| 2 | Solve (one job, terminal status) | `references/long-running-jobs.md` |

Inspecting uploaded data for columns and constraints is fine; emit a
completed plan only after smoke succeeds.

## Quick reference

**Imports (LP/MILP/QP):**

```python
from cuopt.linear_programming.problem import Problem, INTEGER, MINIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings
# When available (preferred):
from cuopt.grpc.linear_programming import Client, GrpcError, JobStatus
```

**Interfaces:** LP/MILP/QP → prefer async Python gRPC client on `:5001`,
otherwise use the legacy remote fallback; routing → REST `:5000`. See
`references/async-grpc-python.md`, `references/remote-execution-fallback.md`,
`references/interfaces.md`, and `references/routing-rest-only.md`.

## Reference index

| Topic | File |
|---|---|
| Activation / skill order | `references/activation.md` |
| Intent / paraphrases | `references/intent-and-triggers.md` |
| Gates / common mistakes | `references/gates-and-first-actions.md` |
| Async Python gRPC jobs | `references/async-grpc-python.md` |
| Legacy remote fallback | `references/remote-execution-fallback.md` |
| Connectivity + smoke | `references/grpc-connectivity-and-smoke.md` |
| Python imports | `references/python-imports.md` |
| gRPC vs REST | `references/interfaces.md` |
| Routing REST | `references/routing-rest-only.md` |
| Paths + probe | `references/environment-and-networking.md` |
| Long-running jobs | `references/long-running-jobs.md` |
| Troubleshooting | `references/troubleshooting.md` |

## Orchestration skills (local)

After gates: `optimization-from-data-orchestrator` → `optimization-intent-router`
→ `tabular-optimization-ingestion` → `cuopt-model-mapper` (and
`optimization-mode-router` when replay/audit signals appear).

## Vendored upstream skills

Installed under `/sandbox/.openclaw/skills/` by `install-skill`:
`numerical-optimization-formulation`, `cuopt-numerical-optimization-api-python`,
`routing-formulation`, `cuopt-routing-api-python`, `cuopt-server-api-python`,
`cuopt-user-rules`, etc.

For LP/MILP/QP, use upstream skills to build the model. Execute with this
skill's async `Client` lifecycle when importable; only then fall back to the
legacy remote `Problem.solve()` path, which cannot cancel submitted work.
