---
name: cuopt-remote-env
description: STOP if you see cudaErrorInsufficientDriver, "CUDA driver version is insufficient", RMM/CUDA init errors, ImportError/from cuopt import milp/wrong Python API path, or a failed cuOpt smoke test — BEFORE declaring cuOpt blocked, offering "prep work while cuOpt gets fixed", or pivoting to heuristics/backtracking. In the NemoClaw sandbox there is NO local GPU; every Python LP/MILP/QP solve defaults to LOCAL CUDA unless you export CUOPT_REMOTE_HOST and CUOPT_REMOTE_PORT before the Python process starts. LP/MILP/QP use cuopt.linear_programming.problem.Problem (MILP = INTEGER vars, not cuopt.milp). The probe (probe_cuopt.py) does NOT set these vars for you. Passing Gate 1 (grpc reachable) is NOT proof remote Python is configured. You MUST export CUOPT_REMOTE_HOST=host.openshell.internal and CUOPT_REMOTE_PORT=5001 inside bash -lc, run the LP smoke test, and confirm "Using remote GPU backend" in output before any real model or any "cuOpt unavailable" claim. Also triggers on remote execution env vars, gRPC Python API, local solve mistaken for server failure.
---

# cuOpt Remote Execution Environment (NemoClaw Sandbox)

**There is no GPU in this sandbox.** The Python SDK's default for
`Problem.solve()` is a **local CUDA solve**. Local CUDA **always fails
here** — usually as `cudaErrorInsufficientDriver` or "CUDA driver
version is insufficient for CUDA runtime version".

That error almost always means **you forgot the remote env vars**, not
that cuOpt or OpenShell is broken.

## The rule in one sentence

**Before any `p.solve()` / LP / MILP / QP Python call: export
`CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` in the same shell that
starts Python, then confirm `Using remote GPU backend` in the log.**

The connectivity probe (`probe_cuopt.py`) **does not** set these for
you. It only checks that the gRPC port answers.

## Python imports — copy exactly (LP / MILP / QP)

**There is no `from cuopt import milp`.** MILP scheduling uses the same
module as LP:

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, INTEGER, MINIMIZE, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings
```

If an import fails, run this **before** declaring the API broken:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 -c "from cuopt.linear_programming.problem import Problem, INTEGER; print(\"api_ok\")"'
```

Full fragments + MILP smoke: **`cuopt-python-api`**.

## Mandatory exports (LP / MILP / QP via Python SDK or `cuopt_cli`)

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

| Variable | Value | Never use |
|---|---|---|
| `CUOPT_REMOTE_HOST` | `host.openshell.internal` | `localhost`, `127.0.0.1`, `0.0.0.0` |
| `CUOPT_REMOTE_PORT` | `5001` | `5000` (that's REST) |

Env vars must be set **in the same process tree** as the Python
interpreter. Exporting them in a prior `tool_call exec` does not carry
over to the next one. Inline them in every solve command:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

Use `bash -lc` (login shell) so the cuOpt venv and paths are active.
Bare `bash -c`, `sh -c`, or non-login `tool_call exec` shells often
skip `/sandbox/.bash_profile` and leave the venv inactive.

## Gate checklist — complete before ANY real solve

Copy this checklist into your reasoning and fill it in:

| Step | Done? | Evidence |
|---|---|---|
| Probe returned `grpc` or `rest grpc` | ☐ | `available:` line from `probe_cuopt.py` |
| Wrote solver script to a **file** (not inline heredoc) | ☐ | `/sandbox/solve.py` for real models; use pre-installed `/sandbox/smoke_lp.py` for Gate 3 |
| Ran with `bash -lc` + venv activate + **`export CUOPT_REMOTE_*`** | ☐ | command includes both exports |
| Log contains **`Using remote GPU backend`** | ☐ | paste the line |
| Smoke LP returned **`Optimal`** | ☐ | status + objective |

**Only after all five rows are checked** may you build the user's real
model or tell the user cuOpt is server-side broken.

If row 4 is missing and you see `cudaErrorInsufficientDriver` → go
back to row 3 (env vars), **not** to prep work or heuristics.

## Error → meaning → action

| What you see | What it means | What to do |
|---|---|---|
| `cudaErrorInsufficientDriver` / "driver version is insufficient" **without** `Using remote GPU backend` | **Local solve** — env vars missing or wrong shell | Set `CUOPT_REMOTE_*`, use `bash -lc`, rerun smoke test |
| No `Using remote GPU backend`, no CUDA error yet | Env vars not picked up | Same fix — exports must be in the same `bash -lc` line as `python3` |
| `Using remote GPU backend` + `Optimal` | Remote path works | Proceed to real model (`cuopt-sandbox` Gate 4) |
| `Using remote GPU backend` + `cudaErrorNoDevice` / `Remote … failed` | Client OK; **host** GPU broken | Operator fixes host service — still not a local-env problem |
| Probe `available: grpc` only | Port reachable | **Not sufficient** — still run smoke test **with env vars** |

## REST path (VRP / routing) — different vars

Routing uses REST, not `CUOPT_REMOTE_*`. Pass host/port explicitly:

```python
CuOptServiceSelfHostClient(ip="host.openshell.internal", port="5000")
```

See `cuopt-sandbox` for routing. This skill applies to **gRPC Python
LP/MILP/QP** solves.

## Anti-pattern — "blocked, let me do prep work" (from real sessions)

> The probe reached gRPC. The smoke test failed with
> `cudaErrorInsufficientDriver`. So I should not claim a valid optimized
> schedule from cuOpt. Best next step: fix/enable the cuOpt runtime, or
> I can do prep work — validate data, summarize rules, draft the model.

**Wrong.** You have not tested remote execution yet. The smoke test
failed because it was a **local** solve. Fix:

1. Export `CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT`.
2. Rerun smoke test.
3. Only if smoke fails **with** `Using remote GPU backend` in the log
   is there a real server-side blocker.

Offering prep work / capacity analysis / model drafting as a substitute
for step 1–2 is **not allowed** when the probe shows gRPC available.
Prep work is fine **in parallel after** remote smoke passes, or when
the user explicitly asks for it — not as a bypass for missing env vars.

## Anti-pattern — "I'll set env vars later"

> The probe confirms gRPC. I'll draft the MILP first and set remote env
> vars when I'm ready to solve.

Wrong. Set env vars **before the first smoke test**, not after the full
model is written. The smoke test exists precisely to catch missing env
vars before you invest in formulation.

## Pre-installed smoke test (Gate 3)

Run `/sandbox/smoke_lp.py` — **do not rewrite it**. It is uploaded by
`nemoclaw_cuopt_setup.sh` with the correct imports and a tiny LP model.

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

Expected: log line `Using remote GPU backend`, then `status=Optimal objective=10.0 …`.

For MILP scheduling tasks, also run `/sandbox/smoke_milp.py` with the
same env vars. For routing, run `/sandbox/smoke_vrp.py` (REST, no
`CUOPT_REMOTE_*`). See `cuopt-python-api`.

## Related skills

- `cuopt-python-api` — import lines; anti-pattern for `cuopt.milp`
- `cuopt-sandbox` — full gate sequence (probe → env → smoke → model)
- `always-tool-discovery` — how to reach `exec`/`read` when tools are hidden
