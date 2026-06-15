---
name: cuopt-sandbox
version: "26.06.01"
description: Run cuOpt in the NemoClaw sandbox — probe/smoke gates, remote gRPC env, then vendored cuOpt skills.
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
remote env vars, and handoff to vendored formulation/API skills.

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
| 0 | Probe → remote env → smoke | `references/remote-env-and-smoke.md` |
| 1 | Formulate | vendored `*-formulation` skills |
| 2 | Solve (one job, terminal status) | `references/long-running-jobs.md` |

Inspecting uploaded data for columns and constraints is fine; emit a
completed plan only after smoke succeeds.

## Quick reference

**Imports (LP/MILP/QP):**

```python
from cuopt.linear_programming.problem import Problem, INTEGER, MINIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings
```

**Interfaces:** LP/MILP/QP → gRPC `:5001` + `CUOPT_REMOTE_*`; routing → REST
`:5000`. See `references/interfaces.md`, `references/routing-rest-only.md`.

## Reference index

| Topic | File |
|---|---|
| Activation / skill order | `references/activation.md` |
| Intent / paraphrases | `references/intent-and-triggers.md` |
| Gates / common mistakes | `references/gates-and-first-actions.md` |
| Env vars + smoke | `references/remote-env-and-smoke.md` |
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
