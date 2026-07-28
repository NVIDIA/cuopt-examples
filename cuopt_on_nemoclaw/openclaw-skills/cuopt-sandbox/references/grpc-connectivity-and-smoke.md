# gRPC connectivity and smoke tests

There is **no GPU in this sandbox.** LP/MILP/QP execution uses gRPC on the
host. Prefer the cancelable Python job API when importable:

```python
from cuopt.grpc.linear_programming import Client

client = Client("host.openshell.internal", 5001, tls=False)
```

The probe (`probe_cuopt.py`) reports both endpoint reachability and
`python_async_grpc: available|unavailable`. Use
`host.openshell.internal`, not `localhost` / `127.0.0.1`, and port `5001`,
not REST port `5000`.

| Probe capability | Execution |
|---|---|
| `python_async_grpc: available` | Required: `references/async-grpc-python.md` |
| `python_async_grpc: unavailable` | Legacy fallback: `references/remote-execution-fallback.md` |

## Pre-installed smoke scripts

Activate the venv and run the scripts unchanged:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

| Script | When |
|---|---|
| `/sandbox/smoke_lp.py` | Gate 3 — all gRPC LP/MILP/QP |
| `/sandbox/smoke_milp.py` | Extra check for scheduling / INTEGER |
| `/sandbox/smoke_vrp.py` | Routing only — REST |

Expected LP/MILP output identifies the selected path:

- Async: `execution_mode=async-grpc job_status=COMPLETED …`
- Legacy fallback: `execution_mode=remote-execution cancellation=unavailable`
  followed by `status=Optimal …`

## Gate checklist

| Step | Evidence |
|---|---|
| Probe returned `grpc` or `rest grpc` | `available:` from probe |
| Solver script in a **file** | `/sandbox/solve.py` or smoke script |
| Execution capability selected | `python_async_grpc:` from probe |
| Smoke identifies execution mode | `execution_mode=...` |
| Smoke returned success | async `COMPLETED` or fallback solver status |

## Common errors

| Symptom | Action |
|---|---|
| Async client import fails | Use legacy remote fallback; upgrade cuOpt if cancellation is needed |
| Client connection fails | Probe, then use `host.openshell.internal:5001` |
| `FAILED` / `CANCELLED` | Report status, job ID, and `GrpcError`; inspect logs |
| `cudaErrorInsufficientDriver` | Neither async client nor correctly exported remote fallback was used |
| `from cuopt.grpc import Client` fails | Import from `cuopt.grpc.linear_programming` |
| Client connects to `localhost` | Use `host.openshell.internal` |
| Streams are deleted early | Join streams, collect result/logs, then delete |
| LP/MILP uses REST | Use gRPC port 5001; routing uses REST port 5000 |
