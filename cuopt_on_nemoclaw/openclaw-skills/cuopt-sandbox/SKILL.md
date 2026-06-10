---
name: cuopt-sandbox
description: STOP before schedule/heuristic output OR claiming files/shell are unavailable. If only tool_search/tool_describe/tool_call are visible, run tool_search (read/shell) first — see always-tool-discovery. Then read cuopt-first; probe_cuopt.py; cuopt-remote-env + smoke with CUOPT_REMOTE_* before any model. One cuOpt job at a time — poll until time_limit returns a status; never submit a second solve while the first is in flight. Triggers: schedule, league, CSV, minimize, assign, MILP, routing, optimal, feasible, time_limit, job still running. No ortools/heuristics. cudaErrorInsufficientDriver without Using remote GPU backend = missing env vars.
---

# NVIDIA cuOpt (Sandbox)

Solve optimization problems using NVIDIA cuOpt from inside the sandbox.
This skill covers **sandbox-specific** setup — networking, venv, and connectivity.

> **Read `cuopt-first` before this section if you have not already.** It
> defines what you must **not** output (heuristic schedules, greedy
> assigners, feasibility verdicts) before the probe → env → smoke gates
> below complete.

## Zero optimization output before Gate 3

Do not send the user any of the following until the LP smoke test
passes with `Using remote GPU backend` (see Four gates below):

- A season schedule, slot assignment, or roster
- "Here's a heuristic / greedy / draft plan"
- "Feasible" / "infeasible" / "capacity is sufficient" as the answer
- Python that assigns games, routes, or resources **outside** cuOpt's API
- An apology for not using cuOpt — prevent the miss instead

Reading uploaded files to identify columns and constraints is fine.
**Emitting an optimization result is not**, until cuOpt solves the model.

> **In this sandbox, LP/MILP must be solved through the remote cuOpt service
> on the host, not the local CUDA runtime.** There is no GPU inside the
> sandbox. If you see `cudaErrorInsufficientDriver` **without**
> `Using remote GPU backend` in the same run, you accidentally invoked a
> local solve — set `CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` to use the
> remote service instead. If you **do** see `Using remote GPU backend`
> followed by `cudaErrorNoDevice` or `Remote LP solve failed`, the client
> path is correct and the **host cuOpt service** has no usable GPU — report
> that to the operator; do not fall back to heuristics or hand search.
>
> **Full env-var checklist and error table:** read the `cuopt-remote-env`
> skill — it is mandatory for every gRPC Python LP/MILP/QP solve in this
> sandbox.

## Finding the shell, file, and editing tools

**If your tool list shows only `tool_search`, `tool_describe`, and
`tool_call`, you still have `read`, `write`, and `exec` — run
`tool_search` first.** Full walkthrough: `always-tool-discovery` skill.
Do **not** tell the user you cannot read files or ask them to paste
`ls`/`cat` output.

Minimal pattern (read a CSV or run probe):

```json
{"name": "tool_search", "arguments": {"query": "read"}}
{"name": "tool_describe", "arguments": {"name": "read"}}
{"name": "tool_call", "arguments": {"name": "read", "arguments": {"path": "/sandbox/teams.csv"}}}
```

For shell/probe, use `"query": "shell"` → `exec` →
`{"command": "bash -lc 'python3 /sandbox/probe_cuopt.py'"}`.

Every command below assumes this catalog path when real tools are not
directly listed. Report a setup problem only if `tool_search` with
`{"query": ""}` returns nothing beyond the three meta-tools.

Concrete one-shot for the cuOpt capability probe (the very first
thing this skill expects you to run):

```json
{"name": "tool_search", "arguments": {"query": "shell"}}
{"name": "tool_describe", "arguments": {"name": "exec"}}
{"name": "tool_call", "arguments": {
  "name": "exec",
  "arguments": {"command": "bash -lc 'python3 /sandbox/probe_cuopt.py'"}
}}
```

If you finished reading this section without running that probe once,
you have not yet done the work this skill exists for. Run it.

## Always use cuOpt when it is available

If the user's task is an LP, MILP, QP, or vehicle-routing problem **and**
the capability check below shows the required cuOpt service is reachable,
you MUST solve it with cuOpt. This applies even when:

- The problem has only 2–3 variables and could be solved by hand or by
  inspecting corner points of the feasible region.
- The user asked you to "make up", "invent", or "come up with" an example.
- A textbook approach (graphing, exhaustive enumeration, simplex by hand)
  would also yield the answer.
- The problem appears pedagogical or "obvious".

The sandbox exists to demonstrate cuOpt; bypassing it for size or
pedagogy defeats the purpose. Always:

1. Formulate the problem (variables, constraints, objective) — see the
   `*-formulation` sibling skills for the relevant problem class.
2. Build and submit it through the matching `cuopt-*-api-*` skill.
3. Report cuOpt's status, objective value, and variable values.
4. Only then, if helpful, walk through the math/intuition.

**Narrow exceptions** (do not invent others):

- The capability check shows the required service is unavailable → follow
  the decline rule in the next section. Do not silently fall back to a
  by-hand solve.
- The user **explicitly** asks for a by-hand walkthrough, "without using
  cuOpt", "show the math", "explain the algorithm", or similar — comply,
  but state once that cuOpt would be the production answer.

When in doubt, run cuOpt.

## Evidence standard — no cuOpt, no verdict

Do not tell the user a schedule/plan is **infeasible**, **impossible**,
or **cannot be satisfied** unless cuOpt returned an explicit solver
status (`Infeasible`, `InfeasibleOrUnbounded`, etc.) for a model you
actually submitted.

The following are **not** acceptable substitutes for a cuOpt infeasibility
proof:

- Backtracking, branch-and-bound, or exhaustive search you wrote yourself.
- `ortools`, `pulp`, or any other non-cuOpt solver.
- Hand reasoning ("the constraints clearly conflict").
- A heuristic that failed to find a feasible assignment.

If cuOpt has not yet run successfully on the real model, say **"I have
not yet solved this with cuOpt"** — not "it's infeasible". If you ran a
non-cuOpt exploratory search, label it explicitly as a **non-authoritative
heuristic** with caveats and still pursue the cuOpt path.

## Remote-first — never try a local solve before the remote service

There is no GPU in this sandbox. Every cuOpt Python entry point that
touches CUDA (`from cuopt import routing`, `cuopt.linear_programming`
local solves, anything that initializes `rmm` or `cudf`) **will fail at
import or first-use** with `cudaErrorInsufficientDriver`,
`RMM`/`CUDA driver` errors, or similar. This is expected, not a bug to
work around — the sandbox image deliberately omits the driver because
solves are routed to a host-side cuOpt service over the wire.

**Mandatory order of attempts for any cuOpt-supported task:**

1. Run the capability probe (`probe_cuopt.py` — see "Capability check"
   below). Read `available:` line. **If the most recent probe in this
   session did NOT return `rest grpc`, you MUST re-run the probe before
   this task — the operator may have started a service since the last
   check, and a stale "REST only" or "gRPC only" reading will pin you to
   a suboptimal path. Only the full `rest grpc` result is durable enough
   to reuse for the rest of the session.**
   **Gate 1 only proves the endpoint is reachable — not that solves work.**
2. **Stop and answer the post-probe checklist** (see "Four gates before
   modeling" below). Pick the interface, name the sibling skill you will
   read next, and confirm the problem family (MILP vs routing vs LP).
   **Do not write model code until you have written down those three
   answers.**
3. **Set remote env vars and run the smoke test** (Gates 2–3). For LP /
   MILP / QP: read `cuopt-remote-env`, export `CUOPT_REMOTE_HOST` /
   `CUOPT_REMOTE_PORT` in the same `bash -lc` line as Python, run the
   minimal LP smoke test, confirm `Using remote GPU backend` + `Optimal`.
   For routing when REST is available: minimal health/submit from the VRP
   cookbook with explicit `host.openshell.internal:5000`.
   **`cudaErrorInsufficientDriver` without `Using remote GPU backend`
   means env vars were not set — retry Gate 2; do NOT declare cuOpt
   blocked or offer prep work as a substitute.**
4. Read the sibling skills named in step 2 (`numerical-optimization-formulation`
   + `cuopt-numerical-optimization-api-python` for MILP/scheduling, etc.).
   **Only now** formulate and submit the real problem.
5. The **only** legitimate evidence that cuOpt is unavailable for your
   task is a fresh `probe_cuopt.py` result whose `available:` line is
   `none`, *or* the matching column in the capability table marks the
   required interface as "Decline", *or* the smoke test fails with a
   server-side error after env/venv are confirmed correct. The following
   do **not** count and never permit skipping cuOpt:
   - a failed `import cuopt` / `from cuopt import routing` / any
     `ModuleNotFoundError` in the current interpreter
   - any **other** Python solver library being missing
     (`ortools`, `pulp`, `scipy.optimize`, `cvxpy`, `pyomo`, `mip`, …).
     Those are **not cuOpt**, and their absence has nothing to do with
     whether the cuOpt service is reachable. If you typed
     `from ortools…` (or any of the above) and got `ModuleNotFoundError`,
     do not propose installing them, do not write your own backtracking /
     branch-and-bound / simplex search — run the cuOpt probe.
   - the problem being small, toy-sized, pedagogical, or "obvious"
   - a probe result from earlier in the session that wasn't `rest grpc`
     (re-probe — the operator may have started a service since)
   - a guess that "cuOpt won't help here"
   - a hand solution being faster to type
   If you have any of these and no fresh `none` probe, you are still
   required to use cuOpt. The sandbox has no GPU, so once you do reach
   the "local cuOpt is the only candidate" branch (a real `none`
   probe), it will almost certainly fail anyway — proceed to step 6.
6. **If every cuOpt path fails**, stop. Explain to the user exactly
   which probe / interface / payload failed and what's needed (operator
   action, network policy, etc.). **Do not** silently fall back to
   brute force, hand calculation, exhaustive search, a non-cuOpt
   solver, or "I solved it another way" — those are all violations of
   "always use cuOpt when it's available". Returning a correct answer
   from a non-cuOpt method is still a failure of this skill.

A 422 / 400 from the REST server is **not a fall-back trigger** — it
means your payload was wrong. Read the response, fix the named field
(see `cuopt-server-api-python`'s "On a 422" recipe and `assets/`
cookbook for known-good shapes), and retry. Two consecutive failures
on the same field → re-read the cookbook entry that uses that field.

For **how to use cuOpt** (formulation, Python API, CLI, MPS format, routing, etc.),
read the sibling skills installed alongside this one in
`/sandbox/.openclaw/skills/`. Names follow stable suffix patterns
upstream, so prefer pattern-based discovery over memorizing exact names:

- `cuopt-first` — **Read before anything else for optimization tasks:**
  no heuristic/schedule output before probe → env → smoke
- `cuopt-user-rules` — Read FIRST: behavior rules, clarify before coding, verify results
- `cuopt-remote-env` — **Mandatory before any gRPC Python LP/MILP/QP solve:**
  `CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT`, smoke test, cudaError diagnostics
- `always-tool-discovery` — **Every session:** `tool_search` → `read`/`exec` when catalog is compact
- Any `*-formulation` skill — How to go from problem text to formulation
  (LP / MILP / QP, vehicle routing, etc.)
- Any `cuopt-*-api-python` skill — Solve through the Python SDK
  (numerical optimization / LP / MILP / QP, routing, server client)
- Any `cuopt-*-api-cli` skill — Solve via `cuopt_cli` with MPS files
- `cuopt-server-common` and `cuopt-server-api-python` — REST/gRPC server
  concepts and Python client (server skills are not pattern-merged)
- `skill-evolution` — Detect generalizable learnings during a long-running session

Concrete formulation skill currently installed upstream:
`numerical-optimization-formulation` (LP, MILP, and QP concepts in one
skill). Reachable through the `*-formulation` pattern above. List the
directory to see what's actually installed:

```bash
ls -1 /sandbox/.openclaw/skills/
```

These are vendored from <https://github.com/NVIDIA/cuopt/tree/release/26.06/skills> at
sandbox-setup time so the agent can read them locally — the sandbox cannot
reach `github.com` directly. To refresh, ask the operator to re-run
`./nemoclaw_cuopt_setup.sh install-skill <sandbox>` on the host.

## Environment

The cuOpt client and SDK are installed in a Python virtual environment at
`/sandbox/.openclaw-data/cuopt` (the default NemoClaw filesystem policy
marks `/sandbox` itself as read-only, so the venv lives in the writable
subtree under `/sandbox/.openclaw-data/`).

The sandbox's `/sandbox/.bash_profile` auto-activates the venv and sets
`CUOPT_SERVER`. It fires for **login shells only** — `bash -l`,
`bash -lc '…'`. Non-login interactive shells (the default behind
`openshell sandbox connect` / `nemoclaw connect`) and non-login
non-interactive shells (`bash -c '…'`, `sh -c '…'`, the default behind
many `tool_call exec` paths) do **not** source `.bash_profile`, so the
venv will *not* be active there.

This is a NemoClaw constraint, not a cuOpt choice: `/sandbox/.bashrc`
(the file non-login interactive bash would normally source) is sealed
root-owned mode 444 *and* Landlock-protected (see
`04-landlock-readonly.sh` check 2 — even root processes can't write to
it after the sandbox starts), so we can't put activation there.

Three ways to get a venv-active shell:

```bash
# After `nemoclaw connect <sandbox>` (non-login), inside the sandbox shell,
# either source .bash_profile in place:
source /sandbox/.bash_profile
# or replace the current shell with a login shell:
exec bash -l

# From the host: one-shot login-shell command for any single task.
openshell sandbox exec --name <sandbox-name> -- bash -lc 'python3 …'
```

Prefer the `bash -lc '…'` wrapper for anything dispatched through
`tool_call exec` — it picks up `CUOPT_SERVER`, the `cuopt_sh` alias, and
the venv `PATH` in one shot.

If the venv doesn't exist, ask the operator to run the host-side setup
script (`./nemoclaw_cuopt_setup.sh add <sandbox-name>`); the sandbox user
cannot recreate it directly because the packages live under the
`openclaw-sandbox` network policy and the venv path must match the
operator's configuration.

## Networking — CRITICAL

> **Always use `host.openshell.internal` as the server address.**
> Do NOT use `localhost`, `127.0.0.1`, or `0.0.0.0` — these resolve inside
> the sandbox container and will be **blocked** (403 Forbidden or timeout).

Two server interfaces are available on the host:

| Interface | Port | Protocol | Use for |
|-----------|------|----------|---------|
| REST      | 5000 | HTTP     | `cuopt_sh` CLI, `cuopt_sh_client` Python client, health checks |
| gRPC      | 5001 | HTTP/2   | `cuopt_cli` remote execution, Python SDK remote solves |

The `CUOPT_SERVER` environment variable (set in `.bash_profile` for login
shells) contains the REST `host:port` value.

## Capability check — run this FIRST

**Do not substitute `import cuopt` for the probe.** In this sandbox a
failed `import cuopt` (or `from cuopt import routing`, or
`from cuopt.linear_programming...`) only tells you the *local* runtime
can't initialize — almost always because there is no GPU here, and the
service runs on the host. It says **nothing** about whether the
host-side cuOpt service is reachable. The only authoritative
capability signal is what `probe_cuopt.py` prints on its `available:`
line. If the probe says `rest`, `grpc`, or `rest grpc`, cuOpt is
available and you must use it — regardless of what a local import
does. If you catch yourself reasoning "I tried `import cuopt`, it
failed, so I'll solve this by hand", stop and run the probe.

Before doing any cuOpt work, probe what the host is actually serving.
**The probe needs the cuOpt venv** for `grpcio`; non-login shells
(`bash -c '…'`, plain `sh -c '…'`) do not source `.bash_profile`, so
either wrap the call in `bash -lc '…'` or source the venv explicitly:

```bash
source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 /sandbox/probe_cuopt.py
```

The last line tells you what's available. Map it to the request you were
asked to handle:

| `available:` line | You may use | Decline (politely, with reason) |
|---|---|---|
| `rest grpc` | everything below | nothing |
| `rest` only | LP / MILP via Python SDK or `cuopt_sh` / `cuopt_sh_client`; vehicle routing (VRP, TSP, PDP) | LP / MILP via `cuopt_cli`; QP |
| `grpc` only | LP / MILP via Python SDK or `cuopt_cli`; QP | vehicle routing (VRP, TSP, PDP); `cuopt_sh*` tools |
| `none` | nothing — refuse | every cuOpt task |

When a request lands in the "Decline" column, do **not** open the matching
sibling skill and try anyway. Tell the user which service is needed and
point at `cuopt-examples/cuopt_on_nemoclaw/SETUP.md` ("Starting the cuOpt
server"). Example:

> The cuOpt REST server (port 5000) isn't reachable, so I can't solve
> vehicle-routing problems in this sandbox. Ask the operator to start it
> (see SETUP.md, "Starting the cuOpt server"), then try again.

The probe also prints the exact endpoint reached, e.g.
`grpc:      host.openshell.internal:5001`. Use that endpoint for the
session — set `CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT` for gRPC, or pass
`ip=` / `port=` to `CuOptServiceSelfHostClient` for REST.

For machine-parseable output use `--json`:

```bash
source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 /sandbox/probe_cuopt.py --json
```

## Four gates before modeling

The probe, **remote env vars**, the smoke test, and the sibling-skill
read are **four separate gates**. Passing one does not skip the others.
A common failure mode is probing successfully (`available: grpc`), running
a smoke test **without** `CUOPT_REMOTE_*` exports, getting
`cudaErrorInsufficientDriver`, and incorrectly declaring cuOpt blocked
or offering "prep work" — see `cuopt-remote-env` for the full error table.

**Gate 1 — Endpoint reachable (probe).** Run `probe_cuopt.py`. Record:

| Question | Your answer (write it out before proceeding) |
|---|---|
| `available:` line | `rest` / `grpc` / `rest grpc` / `none` |
| Problem class for this task | LP / MILP / QP / routing |
| Interface you will use | gRPC Python SDK / REST / `cuopt_cli` |
| Sibling skill to read next | e.g. `cuopt-numerical-optimization-api-python` |

**`available: grpc` means the TCP port answered — not that env vars are
set, not that remote solves succeed, and not that you may skip the
smoke test or read `cuopt-remote-env`.** The probe does not export
`CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT` for you.

**Gate 2 — Remote env vars set (mandatory for gRPC Python LP/MILP/QP).**
Read `cuopt-remote-env` and complete its checklist before any
`p.solve()`. Minimum:

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

These must appear in the **same** `bash -lc '…'` command as `python3`,
not in a prior shell invocation. Skip this gate → local CUDA →
`cudaErrorInsufficientDriver` → **not** a server failure.

**Gate 3 — Remote solve works (smoke test with Gate 2 env vars).**
Run the minimal LP in "Quick connectivity smoke test". Expected:
`Using remote GPU backend` + `Optimal`.

| Smoke outcome | Meaning | Next action |
|---|---|---|
| `Optimal` + `Using remote GPU backend` | Path works | Proceed to Gate 4 |
| `cudaErrorInsufficientDriver` **without** remote backend log | Gate 2 skipped | Read `cuopt-remote-env`; set exports; retry |
| Shell/heredoc/`File name too long`/`SyntaxError` | Script packaging bug | Write script to file; retry with env vars |
| No `Using remote GPU backend`, no CUDA error | Env vars not in same shell | Inline exports in `bash -lc`; retry |
| `Using remote GPU backend` then `cudaErrorNoDevice` | Host GPU broken | Operator action; **not** missing env vars |
| Connection refused on probe | Service down | Operator starts service |

**Do not tell the user cuOpt is unavailable, and do not offer prep-work
substitutes (data validation, capacity checks, model drafting), until
Gate 3 passes OR smoke fails with `Using remote GPU backend` already
in the log** (proving the client path is correct and the fault is
server-side).

**Gate 4 — Read the right skills.** Open the formulation + API skills
from the table before writing solver code. **Read `cuopt-python-api`
first** and copy its import lines — do not guess `from cuopt import milp`.
For scheduling / assignment / league timetable problems, that is almost always MILP via
`numerical-optimization-formulation` +
`cuopt-numerical-optimization-api-python` — **not** vehicle routing
unless the user explicitly gave locations, vehicles, and a travel matrix.

Only after Gates 1–4 pass may you build the real model.

### Problem family quick routing

| User language | Problem class | Skills to read | Interface (typical) |
|---|---|---|---|
| Schedule, timetable, league, roster, assign slots/shifts/games | MILP (assignment/scheduling) | `numerical-optimization-formulation`, `cuopt-numerical-optimization-api-python` | gRPC Python SDK |
| Product mix, blend, allocate budget | LP or MILP | same | gRPC |
| Deliveries, routes, trucks, TSP, VRP, PDP | Routing | `routing-formulation`, `cuopt-server-api-python` | REST |
| Minimize cost / maximize profit with linear constraints | LP / MILP / QP per formulation skill | formulation + `cuopt-numerical-optimization-api-python` | gRPC |

When unsure between MILP scheduling and VRP: if the decisions are
*who plays whom when* or *which resource gets which task*, it's MILP.
If the decisions are *which stops each vehicle visits in what order*,
it's routing.

**Anti-pattern — probe then heuristic (from real sessions):**

> I probed cuOpt first and found gRPC available. My first Python script
> failed with a shell error, so I tried backtracking to test feasibility
> structure and concluded the schedule is likely infeasible.

Wrong on four counts: (1) probe passing is Gate 1 only — smoke test
(Gate 2) was skipped; (2) a shell/heredoc failure is not a solver
failure — retry with a file-based script; (3) backtracking is not an
acceptable substitute for cuOpt when the service is reachable; (4)
infeasibility requires a cuOpt solver status, not a heuristic search.

**Anti-pattern — cudaErrorInsufficientDriver → "cuOpt blocked" → prep work:**

> Smoke test failed with `cudaErrorInsufficientDriver`. I should not
> claim a valid schedule from cuOpt. Let me do prep work — validate
> data, summarize rules, draft the model — while the runtime gets fixed.

Wrong: Gate 2 (`CUOPT_REMOTE_*`) was skipped, so the smoke test hit
**local CUDA**, not the gRPC server. Read `cuopt-remote-env`, set env
vars, rerun smoke. Do not offer prep work as a bypass for missing env
vars when `available: grpc`.

## How to invoke each interface — sandbox-specific delta

For complete API docs, modeling patterns, and examples, read the upstream
sibling skills listed at the top of this file. Below is only what's
*different* about this sandbox.

### gRPC path (Python SDK and `cuopt_cli`)

**Read `cuopt-remote-env` first** — it is the canonical checklist for
`CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT`, the smoke test command, and
the error→action table. Summary:

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

before the Python or CLI process starts, in the same `bash -lc` line as
`python3`. Success marker: `Using remote GPU backend` in the log.

For modeling, status checking, and examples → the matching upstream
skill in `/sandbox/.openclaw/skills/` — typically a `cuopt-*-api-python`
skill (LP / MILP / QP), `cuopt-routing-api-python`, or a `cuopt-*-api-cli`
skill.

### REST path (`cuopt_sh`, `cuopt_sh_client`)

REST runs at `host.openshell.internal:5000`. Pass `ip` and `port` (string)
explicitly when constructing the client; the constructor's defaults assume
`localhost`, which is blocked from the sandbox.

```python
from cuopt_sh_client import CuOptServiceSelfHostClient
client = CuOptServiceSelfHostClient(ip="host.openshell.internal", port="5000")
```

Or with `cuopt_sh`:

```bash
cuopt_sh -t LP /path/to/problem.mps -i host.openshell.internal -p 5000
```

For request shape, polling, and routing examples →
`cuopt-server-api-python`, `cuopt-server-common`, and `cuopt-routing-api-python`
in `/sandbox/.openclaw/skills/`.

### Vehicle routing (VRP, TSP, PDP) — REST only in this sandbox

Routing **must** go through the REST path. The `cuopt.routing` Python
module initializes CUDA/RMM at import time and there is no GPU in this
sandbox, so `from cuopt import routing` fails. This is by design — see
"Remote-first" above.

Concrete steps:

1. Open `cuopt-server-api-python` and read its "VRP payload cookbook"
   table.
2. Pick the cookbook entry whose feature set is closest to the user's
   data — e.g. `vrp_time_windows/` if the user gave time windows,
   `vrp_capacities/` for demand+capacity, `vrp_pickup_delivery/` for
   paired pickups/deliveries. Each entry is at
   `/sandbox/.openclaw/skills/cuopt-server-api-python/assets/<name>/`
   and contains a runnable `payload.json`, `README.md`, and `run.sh`.
3. Adapt the `payload.json` to the user's data, keeping the field
   shapes intact.
4. Submit with `cuopt_sh` (CLI, easiest) or `cuopt_sh_client` (Python).
   Both honor `CUOPT_SERVER` (already set by `.bashrc` to
   `host.openshell.internal:5000`).
5. On a 422, follow the cookbook's "On a 422" recipe — read the `loc`
   path from the response and fix that field. Do not retry blindly;
   do not bail to brute force.

#### Default routing-data assumptions (do not ask)

When user-supplied routing data is incomplete in any of the ways below,
apply these defaults silently rather than asking. Symmetric costs and
zero diagonals are the conventional defaults for VRP/TSP/PDP; asking the
user to re-state them every time is friction without value.

- **Cost and time matrices are symmetric by default.** If the user
  provides a cost or time for one direction of a location pair (A→B)
  but not the reverse (B→A), assume the reverse equals the forward
  value. Mirror sparse one-direction entries into a full square matrix
  before submitting the payload.
- **Diagonal entries are zero.** Cost and time from a location to itself
  is 0. Do not ask whether to include the diagonal or what its value
  should be.
- **Explicit asymmetric values always win.** If the user provides both
  A→B = 10 and B→A = 12, use both as-is. Symmetry is only the default
  for *missing* entries; it is never an override for entries the user
  actually gave.

Only ask for clarification when the gap is genuinely ambiguous in a way
these defaults can't cover, e.g.:

- No cost or time data of any kind was provided — need a source
  (user-supplied matrix? straight-line distance from coordinates?
  haversine on lat/lon? external distance API?).
- Multi-modal cost (e.g. distance vs travel time vs toll) where the
  formulation needs one but the user supplied another.
- Costs/times for some pairs only, with neither direction provided for
  others — explicitly confirm whether the missing pairs are unreachable
  or simply unmeasured.

The `cuopt-routing-api-python` skill describes the GPU-backed Python API
and is **not** the right reference inside this sandbox — use the REST path
instead.

## Long-running solves — one job, poll to completion

cuOpt MILP / VRP solves can take tens of seconds to several minutes.
Under NemoClaw's `exec` tool, any command that exceeds `yieldMs` is
moved to a background process; the agent then has to poll it via the
`process` tool to retrieve the final result. **That polling is your job
to do silently — it is not a checkpoint that requires user input.**

### One job at a time — never submit while one is in flight

When you submit a solve (gRPC `Problem.solve()`, REST
`get_optimized_routes()`, `cuopt_sh`, etc.), **do not start another
solve until the current one returns a terminal response.**

| In flight | Allowed | **Not allowed** |
|---|---|---|
| Python process still running / `reqId` not finished | Poll same process or repoll same `reqId` | New `python3 /sandbox/solve.py`, new REST POST, new gRPC solve |
| Exec backgrounded, no exit yet | `tool_call process` on **that** handle | Kill + resubmit, "try simpler model" as a second job |
| Waiting on REST `reqId` | `client.repoll(reqId)` | Submit a fresh payload while the first job runs |

**Why:** cancelling or abandoning job A does not free the GPU — the
server keeps solving until **A's** `time_limit` expires. Job B then
runs concurrently, wastes GPU, and you lose A's final status/incumbent.

### `time_limit` means you always get a response

If you set `time_limit` (Python:
`settings.set_parameter("time_limit", N)`; REST:
`solver_config.time_limit`), cuOpt **will stop and return within that
window** — even when the problem does not converge to optimality.

You are waiting for a **terminal solver status**, not necessarily
`Optimal`:

| Status (examples) | Meaning |
|---|---|
| `Optimal` | Proven optimal (within tolerances) |
| `FeasibleFound` / `PrimalFeasible` | Feasible solution, may not be optimal |
| `TimeLimit` / time-limit reached | Best effort within budget — **still a valid response** |
| `Infeasible` | No feasible solution |

Silence or a hung client past ~2 × `time_limit` is a **bug or poll
failure**, not "MILP might run forever". Keep polling the **same**
submission; do not open a second one because the first "seems slow".

Three failure modes to avoid — all surface as "it's taking a while, I'll
do something else":

1. **Interrupting the user** — pausing to ask "should I keep
   waiting?" / "should I take the current incumbent?". Wastes the
   user's turn; addressed by the rules below.
2. **Cancelling the solve** — killing the Python process, terminating
   the `tool_call process` handle, or calling `CancelJob` on the gRPC
   server. **This is worse**, because it does not actually stop the
   work — the server-side solve keeps consuming GPU until its own
   `time_limit` fires, and there is no recovery path back to that
   `job_id` from a new client (see
   `cpp/docs/grpc-job-management-proposal.md` in nvidia-cuopt for the
   in-flight design that would fix this; today no `ListJobs` RPC
   exists). A cancel-and-retry loop just queues a *second* concurrent
   solve on the same GPU while the first one runs to completion
   unobserved.
3. **Submitting a second job** — starting a new solve because the first
   "hasn't returned yet". The first job is still running server-side;
   you now have two GPU jobs and no clean result from either.

Concrete rules:

- If you started a cuOpt solve and it is still running, your only valid
  next actions are: (a) `tool_call process` to poll, or (b) wait and
  poll again — **on that same job**. **Never** submit a second solve
  in parallel. **Do not** return to the user with "should I keep
  waiting?", "should I take the current incumbent?", or "let me know if
  you want me to continue". The user already asked for the solution;
  pausing to re-confirm wastes their time and frequently means the
  solver finishes in the gap and the user has to type "yes finish" to
  unblock work that already completed.
- cuOpt's MILP solver respects `SolverSettings.time_limit` (default in
  this sandbox: 120s unless you override). The solver will stop
  itself and return a status within that budget — convergence to
  `Optimal` is not required. You do not need to "decide when to stop"
  — `time_limit` decided that already. Poll until the process exits or
  you hit a generous wall clock (e.g. 2 × the configured solver time
  limit), then report the **terminal status** (including
  `FeasibleFound` / time-limit stops).
- If a feasible incumbent is visible in partial output but the solver
  has not exited, that is **not** a finished solve. Keep polling. Only
  report `Optimal` / `FeasibleFound` / `Infeasible` etc. once the
  Python process actually exits and you can read `Problem.Status.name`
  from the final output (or from a file the script wrote on exit).
- **"Report early" and "cancel" are different actions.** Reporting
  early means surfacing the current incumbent in chat *while the
  solver keeps running*; cancelling means killing the Python process,
  ending the `tool_call process` handle, sending SIGTERM, or calling
  `CancelJob` on the gRPC service. The rules below permit the former
  in narrow cases; they **do not permit cancelling a running solve
  just because it feels slow**.
- The only legitimate reasons to **report early** are: (1) the process
  is genuinely hung (no output movement for > 2 × `time_limit`, no
  completion); (2) the user explicitly asked you to stop or take what
  you have now; (3) the wall-clock budget for the *whole task* (not
  the solver) is about to expire. If you do report early, **keep the
  solver running** unless one of the cancellation reasons below also
  holds — the incumbent may improve while you write the message.
- The only legitimate reasons to **cancel** a running solve are: (1)
  the user explicitly said "cancel" / "kill it" / "stop"; (2) the
  process is genuinely hung *and* you have already tried to read its
  output once without success. "It's taking longer than I expected",
  "I want to try a smaller time limit", and "the user might want a
  different formulation" are **not** cancel reasons — let the current
  `time_limit` fire, then iterate on the result. Cancelling and
  resubmitting "with a smaller time limit" is almost always wrong:
  the original solve does not actually stop, so you are now running
  two solves on one GPU.
- If you must report a partial result, label it explicitly:
  "intermediate incumbent, solver still running" — and keep polling
  while you compose the message; do not pause for confirmation, and do
  not cancel after sending.

Antipatterns to avoid (both from real sessions):

**Forced-choice pause** —

> Still running, but it's on track.  
> If you want the fastest path, I can stop at the current feasible
> solution and give you that immediately. If you want the
> better-quality schedule, I should let cuOpt finish.  
> Recommendation: let it finish.

This is a forced-choice pause. The agent already knows the right
answer ("let it finish"); it should just keep polling and return when
the solve actually completes. The user does not need to confirm a
recommendation the agent itself already made.

**Cancel-and-retry** —

> The MILP has been running for about 3 minutes and the gRPC call
> hasn't returned. I'll cancel this attempt and re-submit with a
> shorter `time_limit` and a simpler formulation so we get *something*
> back quickly.

This is wrong on three counts: (1) the original solve does not
actually stop when the local Python process is killed — the
server-side GPU keeps working until *its* `time_limit` fires;
(2) the original `job_id` is now unrecoverable, so any improving
incumbent the server eventually produces is lost; (3) the "retry"
queues a second concurrent solve on the same GPU, racing the
unobserved first one. The correct action is to keep polling, let the
configured `time_limit` decide when to stop, and report whatever
status the solver returns.

## Script execution hygiene

For any solver script longer than a one-liner, write it to a file first
and run that file. Inline heredocs and `python3 -c "..."` strings interact
badly with the `tool_call → exec → shell → Python` quoting chain — quotes
collapse across layer boundaries, and each broken inline script costs a
full sandbox round-trip before the failure is even visible.

**A shell/script packaging failure is never evidence that cuOpt failed
and never a reason to pivot to backtracking, `ortools`, or hand search.**
If your first cuOpt attempt dies with `File name too long`, `SyntaxError`,
`source: not found`, or a mangled heredoc, fix the execution path and
retry — starting with the smoke test if you haven't passed Gate 3 yet.

Recommended pattern:

```bash
cat > /sandbox/solve.py <<'PY'
# … solver code …
PY
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/solve.py'
```

Use `bash -lc` (not bare `sh`) for any command that calls `source`; the
default shell behind `tool_call exec` can be `dash`, which doesn't have
`source`. The same applies to anything that relies on bash-only syntax
(arrays, `[[ ... ]]`, `<<<`, etc.).

Failure symptoms that mean script construction is broken — **not** cuOpt.
If you see any of these, stop debugging the solver and switch to the
file pattern above. **Do not abandon the cuOpt path.**

- `source: not found` → wrap with `bash -lc '...'`.
- `File name too long` → heredoc/command string blew past shell limits;
  write the script to `/sandbox/solve.py` with `write`/`edit` and run
  that file instead.
- `SyntaxError` on a Python line containing an unquoted URL, path, or
  shell metacharacter → quoting collapsed somewhere across the layers.
- `NameError` on a token that should obviously be a string literal
  (e.g. `Path(/sandbox)` missing the quotes around `/sandbox`) → same
  root cause; the outer layer ate your Python quotes.

If you see `STATUS None` / `OBJECTIVE None` from a solve that otherwise
ran to completion, that's a **different** failure mode — a response-shape
mismatch in your parser. Open the matching cookbook entry under
`/sandbox/.openclaw/skills/cuopt-server-api-python/assets/` and copy its
extraction code rather than extrapolating from a different problem class:

| Problem class | Cookbook entry | Response shape |
|---|---|---|
| LP | `lp_basic/client.py` | `result['response'].get('primal_solution')` — direct |
| MILP | `milp_basic/client.py` | `result['response'].get('primal_solution')` — direct |
| Routing (VRP/TSP/PDP) | `vrp_*/client.py` | `result['response']['solver_response']['status']` — nested under `solver_response` |

The LP/MILP and routing shapes are different. Do not assume one based on
having read the other.

## Quick connectivity smoke tests

**Gate 3 — mandatory before any real LP/MILP/QP model.** Requires Gate 2
env vars (`cuopt-remote-env`). Run the **pre-installed** scripts at
`/sandbox/` — do not rewrite them (correct imports are already inside):

| Script | Use |
|---|---|
| `smoke_lp.py` | Gate 3 for all gRPC LP/MILP/QP work |
| `smoke_milp.py` | Extra check for scheduling / assignment (INTEGER path) |
| `smoke_vrp.py` | Routing only — REST, no `CUOPT_REMOTE_*` |

**LP (Gate 3):**

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  export CUOPT_REMOTE_HOST=host.openshell.internal && \
  export CUOPT_REMOTE_PORT=5001 && \
  python3 /sandbox/smoke_lp.py'
```

Expected: `Using remote GPU backend`, then `status=Optimal objective=10.0 …`.

**MILP (scheduling tasks):** same env vars, `python3 /sandbox/smoke_milp.py`.

**VRP:** `python3 /sandbox/smoke_vrp.py` — expects `status=0 solution_cost=…`.

Write **real models** to `/sandbox/solve.py`; use the smoke scripts only
for connectivity checks.

If this fails, do not move on to a real problem — diagnose using the
smoke-outcome table in "Four gates before modeling" and `cuopt-remote-env`.
Do **not** pivot to heuristic search or declare cuOpt blocked unless
`Using remote GPU backend` was already present in the failing run.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `cudaErrorInsufficientDriver` without `Using remote GPU backend` | Accidentally invoked local solve instead of remote service | Set `CUOPT_REMOTE_HOST=host.openshell.internal` and `CUOPT_REMOTE_PORT=5001` before solving; use `bash -lc` |
| `Using remote GPU backend` then `cudaErrorNoDevice` / `Remote LP solve failed` | Client path OK; host cuOpt gRPC service has no visible GPU | Operator fixes host GPU / container runtime. Do **not** fall back to heuristics — report blocker and stop |
| `from cuopt import routing` fails with CUDA / RMM init error | There is no GPU in this sandbox; routing has no remote-aware Python wrapper | Use REST instead: see "Vehicle routing (VRP, TSP, PDP) — REST only in this sandbox" above and `cuopt-server-api-python`'s `assets/vrp_*/` cookbook. Do **not** fall back to brute force or non-cuOpt methods |
| `403 Forbidden` | Wrong address or sandbox policy missing port | Use `host.openshell.internal`, not `localhost`. If address is correct, ask operator to run `nemoclaw_cuopt_setup.sh apply-policy` |
| `Connection refused` on `:5000` | REST service not running or host firewall blocking the port | Check if REST is needed; gRPC alone (5001) is sufficient for LP/MILP. If REST is needed, ask operator to start it |
| `available: none` from `probe_cuopt.py` | No cuOpt service running on host, ports not in sandbox policy, or host firewall | Ask operator to start a cuOpt server (`SETUP.md` > Starting the cuOpt server) and re-run `nemoclaw_cuopt_setup.sh apply-policy`; verify host firewall opens 5000 / 5001 |
| Connection timeout / hang | Server not running or host firewall blocking Docker | Ask operator to verify from host: `ss -tlnp \| grep 500` |
| Timeout through `10.200.0.1:3128` | Sandbox proxy cannot reach the destination | Ask operator to verify sandbox network policy includes the cuOpt ports |
| `ModuleNotFoundError` | Venv not activated — common in non-login shells (`bash -c '…'`) because `.bash_profile` only fires for login shells | Wrap the call in `bash -lc '…'` (preferred) or `source /sandbox/.openclaw-data/cuopt/bin/activate` before the python invocation |
| `ModuleNotFoundError: No module named 'cuopt.milp'` or `from cuopt import milp` fails | **Wrong import path** — MILP is not a separate package | Use `from cuopt.linear_programming.problem import Problem, INTEGER` — see `cuopt-python-api`; run its verify one-liner before pivoting |
| No `Using remote GPU backend` in output | Remote env vars not set or not picked up | Ensure `CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` are exported before the Python process starts |
