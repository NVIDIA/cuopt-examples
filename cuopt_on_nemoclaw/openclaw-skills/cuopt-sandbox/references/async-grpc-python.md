# Async Python gRPC client (LP / MILP / QP)

Use the embedded C++ client bindings for LP, MILP, and QP jobs. This is
the preferred LP/MILP/QP execution path whenever its import succeeds.

## Imports and connection

```python
from cuopt.grpc.linear_programming import Client, GrpcError, JobStatus
from cuopt.linear_programming.solver_settings import SolverSettings

client = Client("host.openshell.internal", 5001, tls=False)
```

Import from `cuopt.grpc.linear_programming`, not `cuopt.grpc`. Use
`host.openshell.internal`, not `localhost` (which is the sandbox).
The host service is plain TCP, so `tls=False` avoids accidental
`CUOPT_TLS_*` environment configuration.

## Required job lifecycle

Run solves from a real Python file and give each solve a durable run directory.
Immediately after `submit()`, atomically persist enough metadata to reconcile
the remote job after a local wrapper timeout:

- job ID and server endpoint
- input files and model/problem name
- variable naming scheme and solver settings
- expected local result path

```python
import csv
import json
from pathlib import Path

settings = SolverSettings()
settings.set_parameter("time_limit", 600)
names = [
    variable.getVariableName()
    for variable in problem.getVariables()
]

run_dir = Path("/sandbox/cuopt-runs/current")
run_dir.mkdir(parents=True, exist_ok=True)
manifest_path = run_dir / "manifest.json"
result_path = run_dir / "solution.csv"

job_id = client.submit(problem, settings)
manifest = {
    "job_id": job_id,
    "endpoint": "host.openshell.internal:5001",
    "input_files": ["/sandbox/input.csv"],
    "problem_name": "current",
    "variable_naming": "document the model's naming scheme here",
    "solver_settings": {"time_limit": 600},
    "result_path": str(result_path),
    "result_verified": False,
    "cleanup_pending": True,
}
manifest_tmp = manifest_path.with_suffix(".tmp")
manifest_tmp.write_text(json.dumps(manifest, indent=2) + "\n")
manifest_tmp.replace(manifest_path)
print(f"job_id={job_id}", flush=True)

terminal = client.wait(job_id, timeout=660)
if terminal != JobStatus.COMPLETED:
    raise RuntimeError(f"cuOpt job ended with {terminal.name}")

solution = client.result(job_id, names)
if solution is None:
    raise RuntimeError("cuOpt job completed without a result")

variables = solution.get_vars()
result_tmp = result_path.with_suffix(".tmp")
with result_tmp.open("w", newline="") as output:
    writer = csv.writer(output)
    writer.writerow(["variable", "value"])
    writer.writerows(variables.items())
result_tmp.replace(result_path)

# Validate the local artifact before making the remote result deletable.
if not result_path.is_file() or len(variables) != len(names):
    raise RuntimeError("local solution artifact validation failed")
manifest["result_verified"] = True
manifest_tmp.write_text(json.dumps(manifest, indent=2) + "\n")
manifest_tmp.replace(manifest_path)

print("termination=", solution.get_termination_reason())
print("objective=", solution.get_primal_objective())
print("variables=", variables)
```

Rules:

1. Set a solver `time_limit`, then give `wait()` a slightly larger timeout.
2. Persist and print the job ID immediately so a submitted job remains
   discoverable even if the local execution wrapper exits.
3. Treat only `JobStatus.COMPLETED` as result-bearing. Terminal statuses are
   `COMPLETED`, `FAILED`, `CANCELLED`, and `NOT_FOUND`.
4. `result()` returns `None` while a job is not ready and raises `GrpcError`
   for failed, cancelled, missing, or deleted jobs.
5. Pass the full ordered variable-name list corresponding one-to-one with
   `problem.getVariables()` to `result()` so `get_vars()` is keyed correctly.
   A partial list raises `ValueError` in current versions, while reordered
   names silently mislabel values. Filter the returned mapping only after
   retrieval. Each variable exposes `getVariableName()`.
6. `delete()` cancels a queued or running job (same stop behavior as
   `cancel()`), then removes server-side state for that `job_id`. Use
   `cancel()` when you need the job to remain inspectable as `CANCELLED`;
   use `delete()` when you are done and want capacity freed.
7. Do not delete a completed job until its decoded result is saved and
   validated locally. If diagnosis or later retrieval is required, keep the
   terminal job and report its job ID.

## Reconcile after local timeout or interruption

A local tool or wrapper timeout says nothing about the remote job state. Load
the manifest and call `client.status(job_id)` before taking further action:

- `QUEUED` or `PROCESSING`: keep polling that job.
- `COMPLETED`: fetch, save, and validate its result.
- `FAILED` or `CANCELLED`: report the status and diagnostics before deciding
  whether a replacement is appropriate.
- `NOT_FOUND`: report that reconciliation failed; do not imply the solve
  itself failed.

Never resubmit blindly while an earlier job may still exist. Prefer status and
result retrieval for the known job ID over launching a replacement.

## Cancellation and advanced operations

Current nightlies treat delete as cancel-plus-cleanup:

- `client.cancel(job_id)` — stop a queued/running job; leave it inspectable
  as `CANCELLED`.
- `client.delete(job_id)` — stop a queued/running job if needed, then remove
  all server-side state for that `job_id`.

When replacing a model, `delete()` the old job (or `cancel()` then `delete()`
if you want an explicit cancelled record first), then submit the replacement.
Never leave stale jobs consuming host capacity.

For normal completion, make cleanup an explicit final phase after local result
verification. Set `cleanup_pending` to `False` in the manifest only after
`client.delete(job_id)` succeeds. Do not put cancellation or deletion in a
broad `finally` block: local wrapper interruption must not erase the evidence
needed to reconcile a still-running or completed remote job.

The client also exposes `status`, log retrieval/streaming, and MIP incumbent
retrieval/streaming. Join any stream before deleting its job. Use the official
cuOpt Python gRPC documentation for those APIs rather than reproducing their
full signatures in this sandbox-specific skill.

## Errors

Catch `GrpcError` around connection and job operations. Report the exception,
the server endpoint, and the job ID (if submission succeeded). Do not fall
back to local CUDA or another solver.

If this module cannot be imported, use
`references/remote-execution-fallback.md`. That legacy fallback hides the
server job lifecycle and cannot cancel a submitted job, so never choose it
when the async client is available.
