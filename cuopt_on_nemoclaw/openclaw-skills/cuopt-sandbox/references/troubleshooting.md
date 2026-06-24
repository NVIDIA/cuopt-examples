# Troubleshooting

## Symptom → fix

| Symptom | Likely cause | Action |
|---|---|---|
| `cudaErrorInsufficientDriver`, no remote log | Missing `CUOPT_REMOTE_*` | `references/remote-env-and-smoke.md` |
| `ModuleNotFoundError: cuopt.milp` | Wrong import | `references/python-imports.md` |
| Probe empty `available:` | Host cuOpt down | Report to user; retry cuOpt when service is up |
| VRP fails, LP works | Used gRPC for routing | `references/routing-rest-only.md` |
| Second solve hangs / errors | Overlapping jobs | `references/long-running-jobs.md` |
| `~` path not found | Sandbox path resolution | Use `/sandbox/...` |

## Script hygiene

- Put solve logic in `/sandbox/solve.py` (or named script), not inline
  one-liners for real models.
- Use `bash -lc` with venv + exports in one command.
- For gate checks, run pre-installed `/sandbox/smoke_*.py` unchanged.

## When cuOpt returns infeasible / timeout

Report the solver status honestly. You may suggest model relaxations or
clarifying questions — keep the answer grounded in cuOpt status.

## Operator vs agent

| Agent fixes | Operator / host |
|---|---|
| Env vars, imports, script layout | GPU driver on host |
| Wrong port (5000 vs 5001) | cuOpt services not running |
| Formulation errors | Network to `host.openshell.internal` |

## Guardrail skill

Bundled `cuopt-setup` in `nemoclaw_cuopt_setup.sh` points here for
session start — read this skill (`cuopt-sandbox`) for full gate order.
