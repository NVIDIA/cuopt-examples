# Legacy remote execution fallback (async client unavailable)

Use this path only when the installed cuOpt does not provide:

```python
from cuopt.grpc.linear_programming import Client
```

Check first:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 -c "from cuopt.grpc.linear_programming import Client"'
```

If the import succeeds, use `references/async-grpc-python.md`. If it fails
with `ImportError` or `ModuleNotFoundError`, use the legacy env-var remote
execution path:

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/solve.py'
```

Put nontrivial model logic in `/sandbox/<job>.py` first, then run it with a
short shell command like above. Probe/smoke success does not guarantee your
solve script exported the env vars in the same Python process.

The exports must exist **before Python starts** and in the same command.
Never use `localhost`; port `5001` is gRPC.

## Solve and read results

`solve.py` builds the normal `Problem`, sets a finite time limit, and calls:

```python
settings = SolverSettings()
settings.set_parameter("time_limit", 600)
problem.solve(settings)  # blocking remote call; populates variable values
print(problem.Status.name, problem.ObjValue)
for var in problem.getVariables():
    print(var.getVariableName(), var.getValue())
```

On this fallback path, `problem.solve()` copies solved values onto each
variable. Read them with `var.getValue()` (or `var.Value` when present).

Do not assume gRPC helpers exist on this path: no `client.result()`,
`problem.solution`, or `primal_values`. `getIncumbentValues()` is for MIP
incumbent callbacks during solve, not post-solve extraction.

If extraction fails on your build, inspect before guessing:

```python
import inspect
print(inspect.signature(problem.solve))
print([a for a in dir(problem) if "sol" in a.lower()])
print([a for a in dir(problem.getVariables()[0]) if "val" in a.lower()])
```

## Blocking behavior and tool timeouts

`Problem.solve()` is **blocking** from the client side. The Python process
must stay alive until the call returns and any output files are written.

A local tool or shell wrapper timeout does **not** mean the remote solve
failed. Before rerunning, check in order:

1. Does the expected result file already exist?
2. Is there a PID file, and is that process still running?
3. What does the log tail show?

Never launch a duplicate solve while a prior background process may still be
running.

## Long solves: background pattern

Use foreground execution for smoke tests and solves that comfortably fit
within tool wait limits. Background when runtime is uncertain or the script
must write artifacts after solve:

```bash
nohup bash -lc '
  source /sandbox/.openclaw-data/cuopt/bin/activate
  export CUOPT_REMOTE_HOST=host.openshell.internal
  export CUOPT_REMOTE_PORT=5001
  python3 /sandbox/my_job.py
' > /sandbox/my_job.log 2>&1 < /dev/null &
echo $! > /sandbox/my_job.pid
```

Check progress:

```bash
PID=$(cat /sandbox/my_job.pid)
ps -p "$PID" -o pid=,stat=,etime=,cmd=
tail -n 50 /sandbox/my_job.log
ls -l /sandbox/my_job.csv
```

Artifact convention: `<job>.py`, `<job>.pid`, `<job>.log`, `<job>.csv`.
Have the script print a terminal status line (`STATUS Optimal`, etc.) and
exit nonzero on failure.

## Cancellation limitation

Remote execution does not expose a job ID and cannot cancel the submitted
server job. Therefore:

- Prefer the async client whenever its import succeeds.
- Set a finite solver `time_limit` before `Problem.solve()`.
- Run one solve at a time and wait for it to return.
- Do not submit a revised model while the prior solve may still be running.
- If cancellation or model replacement is required, report that the installed
  cuOpt build lacks the cancelable API and ask the operator to upgrade to a
  build that provides `cuopt.grpc.linear_programming.Client`.
