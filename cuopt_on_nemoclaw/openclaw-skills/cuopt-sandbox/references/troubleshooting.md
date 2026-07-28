# Troubleshooting

## Symptom → fix

| Symptom | Likely cause | Action |
|---|---|---|
| `cudaErrorInsufficientDriver` | Local solve; remote fallback exports missing | Use async client or `references/remote-execution-fallback.md` |
| `ImportError: cuopt.grpc.linear_programming` | Installed build lacks async API | Use legacy remote fallback; upgrade cuOpt if cancellation is needed |
| `Problem` has no `get_variable_names` | Used a `DataModel` method on `Problem` | Use `[v.getVariableName() for v in problem.getVariables()]` |
| `ModuleNotFoundError: cuopt.milp` | Wrong import | `references/python-imports.md` |
| Probe empty `available:` | Host cuOpt down | Report to user; retry cuOpt when service is up |
| VRP fails, LP works | Used gRPC for routing | `references/routing-rest-only.md` |
| Second solve hangs / errors | Overlapping jobs | `references/long-running-jobs.md` |
| Active job remains after cleanup | Cleanup never ran, or an older build lacked delete-cancel | Call `delete(job_id)` (cancels then removes state on current nightlies), or `cancel` then `delete` if you need an inspectable `CANCELLED` record |
| Tool wrapper timed out on fallback solve | Blocking `Problem.solve()` outlived exec wait | Check `.pid`, `.log`, result CSV before rerun; see `remote-execution-fallback.md` |
| Wrong or empty variable values after fallback solve | Used async gRPC extraction on fallback path | After `problem.solve()`, read `var.getValue()` from each variable |
| `~` path not found | Sandbox path resolution | Use `/sandbox/...` |

## Script hygiene

- Put solve logic in `/sandbox/solve.py` (or named script), not inline
  one-liners for real models.
- Use `bash -lc` to activate the venv. For the legacy fallback, export
  `CUOPT_REMOTE_*` before Python starts in that same shell.
- For gate checks, run pre-installed `/sandbox/smoke_*.py` unchanged.

## When cuOpt returns infeasible / timeout

Report the solver status honestly. Before building a large MILP, compare
required assignments per entity against the maximum allowed by time buckets,
weekly caps, and total slot capacity — simple arithmetic often catches
impossible requests faster than the solver.

On infeasibility, relax pacing, fairness, or rematch-spacing constraints
before relaxing physical feasibility: court/slot capacity, team overlap,
coach overlap, and hard unavailability.

## Operator vs agent

| Agent fixes | Operator / host |
|---|---|
| Execution selection, endpoint, imports, script layout | GPU driver on host |
| Wrong port (5000 vs 5001) | cuOpt services not running |
| Formulation errors | Network to `host.openshell.internal` |

## Guardrail skill

Bundled `cuopt-setup` in `nemoclaw_cuopt_setup.sh` points here for
session start — read this skill (`cuopt-sandbox`) for full gate order.
