# Remote env vars and smoke tests

There is **no GPU in this sandbox.** `Problem.solve()` defaults to local
CUDA, which fails with `cudaErrorInsufficientDriver` unless remote env vars
are set **before Python starts**.

The probe (`probe_cuopt.py`) does **not** set env vars — it only checks
reachability.

## Mandatory exports (gRPC LP / MILP / QP)

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

| Variable | Use this value | Wrong for gRPC |
|---|---|---|
| `CUOPT_REMOTE_HOST` | `host.openshell.internal` | `localhost`, `127.0.0.1` |
| `CUOPT_REMOTE_PORT` | `5001` | `5000` (REST) |

Inline in every solve command (exports do not carry across separate
`tool_call exec` invocations):

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

Use `bash -lc` so the venv activates.

## Pre-installed smoke scripts (run as-is for gate checks)

| Script | When |
|---|---|
| `/sandbox/smoke_lp.py` | Gate 3 — all gRPC LP/MILP/QP |
| `/sandbox/smoke_milp.py` | Extra check for scheduling / INTEGER |
| `/sandbox/smoke_vrp.py` | Routing only — REST, no `CUOPT_REMOTE_*` |

Expected LP/MILP: log line `Using remote GPU backend`, then
`status=Optimal …`.

## Gate checklist

| Step | Evidence |
|---|---|
| Probe returned `grpc` or `rest grpc` | `available:` from probe |
| Solver script in a **file** | `/sandbox/solve.py` or smoke script |
| `bash -lc` + venv + `export CUOPT_REMOTE_*` | in same command as `python3` |
| Log contains `Using remote GPU backend` | paste the line |
| Smoke returned terminal status | e.g. `status=Optimal` |

## Error → action

| Symptom | Meaning | Fix |
|---|---|---|
| `cudaErrorInsufficientDriver` without `Using remote GPU backend` | Local solve — env vars missing | Set `CUOPT_REMOTE_*`, `bash -lc`, retry |
| No remote backend log, no CUDA error | Env vars not in same shell | Inline exports in `bash -lc` |
| `Using remote GPU backend` + `Optimal` | Remote path works | Build real model |
| `Using remote GPU backend` + `cudaErrorNoDevice` | Host GPU broken | Operator action |
| Probe `available: grpc` only | Port reachable | Still need env + smoke |

## Common mistakes (and the fix)

| Mistake | Fix |
|---|---|
| Treat `cudaErrorInsufficientDriver` (no remote log) as "cuOpt blocked" | Set `CUOPT_REMOTE_*` in the same `bash -lc` command and retry smoke |
| Plan to "set env vars later" | Export before the first smoke test |
| Use REST env vars for LP/MILP | gRPC uses `CUOPT_REMOTE_*` on port 5001; routing uses REST on 5000 — see `references/routing-rest-only.md` |
