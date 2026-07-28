# Long-running cuOpt jobs

**One cuOpt job at a time.** Wait for a terminal status before starting
the next solve.

## Why

Each solve holds a GPU slot on the host. Overlapping jobs queue or fail
with confusing errors. The user asked for one optimization — finish it.

## Rules

1. **Single in-flight solve** — wait for completion before another gRPC or
   REST submission.
2. **Set `time_limit`** — default can be long; cap for interactive work
   (e.g. 600–1800 s for MILP).
3. **Poll sequentially when supported** — one solve at a time is enough.
4. **Report mode and status** — for async, include job ID and `JobStatus`;
   for the legacy fallback, include solver status and
   `cancellation=unavailable`.

## Python (gRPC)

When available, follow `references/async-grpc-python.md`. If a wait times out
with a non-terminal status, keep polling the same job; do not submit a
duplicate. Before replacing it, `delete()` the old job (current nightlies
cancel queued/running jobs as part of delete) or `cancel()` first if you need
an inspectable `CANCELLED` record.

With the legacy remote fallback, there is no job ID or cancellation API. Set
a finite solver time limit and wait for `Problem.solve()` to return. Never
start a replacement while the prior solve may still be running. If the solve
may exceed tool wait limits, use the background pattern in
`references/remote-execution-fallback.md`.

## REST / VRP

Submit one job; poll until completed, failed, or timeout. Wait for that
job to finish before submitting another.

## When the user wants faster iteration

- Reduce problem size for a smoke iteration, or tighten `time_limit`, rather
  than starting a parallel second job.
- For async MIP, use `incumbents()` or `start_incumbent_stream()` for best-so-far.
- Keep using cuOpt for the real solve — slowness is a tuning problem,
  separate from infrastructure gate failures.
