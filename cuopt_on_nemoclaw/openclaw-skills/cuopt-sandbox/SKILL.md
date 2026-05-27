---
name: cuopt-sandbox
description: Read FIRST whenever a request involves linear programming (LP), mixed-integer linear programming (MILP), quadratic programming (QP), or vehicle routing (VRP, TSP, PDP) — including small / pedagogical / made-up problems ("invent an LP example", "show me a small MILP", "find optimal X under constraints", "minimize cost", "plan deliveries", "schedule with constraints"). In this sandbox, cuOpt is the default solver and must be used whenever it is available; this skill points at the per-task skills (cuopt-user-rules, cuopt-numerical-optimization-api-python, cuopt-routing-api-python, numerical-optimization-formulation, etc.) and covers sandbox-specific setup (venv at /sandbox/.openclaw-data/cuopt, host.openshell.internal networking, REST 5000 / gRPC 5001).
---

# NVIDIA cuOpt (Sandbox)

Solve optimization problems using NVIDIA cuOpt from inside the sandbox.
This skill covers **sandbox-specific** setup — networking, venv, and connectivity.

> **In this sandbox, LP/MILP must be solved through the remote cuOpt service
> on the host, not the local CUDA runtime.** There is no GPU inside the
> sandbox. If you see `cudaErrorInsufficientDriver` or similar CUDA errors,
> you accidentally invoked a local solve — set `CUOPT_REMOTE_HOST` and
> `CUOPT_REMOTE_PORT` to use the remote service instead.

## Finding the shell, file, and editing tools (NemoClaw catalog)

This sandbox runs under NemoClaw, which by default exposes only three
meta-tools to the model — `tool_search`, `tool_describe`, `tool_call` —
and hides every real tool (`exec`, `read`, `write`, `edit`, `process`,
…) behind that catalog. If your tool list shows only those three, the
real tools are not missing; they are reachable via the catalog.

Use them in this order:

1. `tool_search` with `{query: ""}` and `{limit: 20}` lists the catalog;
   `{query: "shell"}` or `{query: "file"}` narrows by topic.
2. `tool_describe` with `{name: "<tool>"}` returns the parameter schema.
   Call this once before the first invocation of any new tool.
3. `tool_call` with `{name: "<tool>", arguments: {…}}` runs it.

The capabilities the rest of this skill assumes:

| Capability | Search term | Tool name | Typical args |
|---|---|---|---|
| Run any shell command (ls, source, python3, …) | `shell` / `exec` | `exec` | `{command: "ls -1 …"}` |
| Read a known file path | `read` | `read` | `{path: "/sandbox/…"}` |
| Write / edit a file | `write` / `edit` | `write` / `edit` | see `tool_describe` |

Every shell example below — `ls -1 /sandbox/.openclaw/skills/`, sourcing
the venv, `python3 /sandbox/probe_cuopt.py`, the LP smoke test — is
dispatched as `tool_call` with `name: "exec"` and
`arguments: {command: "<the command>"}`.

If `tool_search` with an empty query returns only the three catalog
tools themselves, no real tools were registered for this session — that
is a gateway setup problem, not a discovery problem; report it to the
operator. If your tool list already includes `exec` / `read` / etc.
directly, the compact catalog is disabled; call those tools directly and
ignore this section.

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
2. Pick the remote interface from the table (rest, gRPC, or both) that
   matches your problem class. **Use it first.**
   - Routing (VRP, TSP, PDP) → REST. Open `cuopt-server-api-python` and
     reuse a starter from its `assets/vrp_*/` cookbook.
   - LP / MILP / QP → **prefer gRPC** via Python SDK or `cuopt_cli`
     whenever the probe shows gRPC available. Fall back to REST via
     `cuopt_sh` / `cuopt_sh_client` only when gRPC is not. Both route to
     the same host service, but gRPC is the native path for these
     problem classes (binary protocol, lower per-call overhead, better
     streaming behavior). A previous session decision to use REST does
     not justify reusing it after a re-probe reveals gRPC.
3. The **only** legitimate evidence that cuOpt is unavailable for your
   task is a fresh `probe_cuopt.py` result whose `available:` line is
   `none`, *or* the matching column in the capability table marks the
   required interface as "Decline". The following do **not** count and
   never permit skipping cuOpt:
   - a failed `import cuopt` / `from cuopt import routing` / any
     `ModuleNotFoundError` in the current interpreter
   - the problem being small, toy-sized, pedagogical, or "obvious"
   - a probe result from earlier in the session that wasn't `rest grpc`
     (re-probe — the operator may have started a service since)
   - a guess that "cuOpt won't help here"
   - a hand solution being faster to type
   If you have any of these and no fresh `none` probe, you are still
   required to use cuOpt. The sandbox has no GPU, so once you do reach
   the "local cuOpt is the only candidate" branch (a real `none`
   probe), it will almost certainly fail anyway — proceed to step 4.
4. **If every cuOpt path fails**, stop. Explain to the user exactly
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

- `cuopt-user-rules` — Read FIRST: behavior rules, clarify before coding, verify results
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

## How to invoke each interface — sandbox-specific delta

For complete API docs, modeling patterns, and examples, read the upstream
sibling skills listed at the top of this file. Below is only what's
*different* about this sandbox.

### gRPC path (Python SDK and `cuopt_cli`)

The Python SDK and `cuopt_cli` solve through the gRPC server. Set:

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

before the Python or CLI process starts. If you see `Using remote GPU
backend` in the solver output, the remote path engaged. If you see
`cudaErrorInsufficientDriver` instead, the env vars didn't take effect and
the client tried to solve locally — there is no GPU here, so it fails.

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

## Script execution hygiene

For any solver script longer than a one-liner, write it to a file first
and run that file. Inline heredocs and `python3 -c "..."` strings interact
badly with the `tool_call → exec → shell → Python` quoting chain — quotes
collapse across layer boundaries, and each broken inline script costs a
full sandbox round-trip before the failure is even visible.

Recommended pattern:

```bash
cat > /sandbox/solve.py <<'PY'
# … solver code …
PY
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && python3 /sandbox/solve.py'
```

Use `bash -lc` (not bare `sh`) for any command that calls `source`; the
default shell behind `tool_call exec` can be `dash`, which doesn't have
`source`. The same applies to anything that relies on bash-only syntax
(arrays, `[[ ... ]]`, `<<<`, etc.).

Failure symptoms that mean script construction is broken — **not** cuOpt.
If you see any of these, stop debugging the solver and switch to the
file pattern above:

- `source: not found` → wrap with `bash -lc '...'`.
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

## Quick connectivity smoke test (LP)

After the connectivity probes pass, run this minimal LP to verify the full
remote-solve path works end to end. Expected: `Optimal`, objective `10`,
`x = 2`, `y = 2`, with `Using remote GPU backend` in the solver log.

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

p = Problem("smoke")
x = p.addVariable(lb=0, vtype=CONTINUOUS, name="x")
y = p.addVariable(lb=0, vtype=CONTINUOUS, name="y")
p.addConstraint(x + y <= 4)
p.addConstraint(x <= 2)
p.addConstraint(y <= 3)
p.setObjective(3*x + 2*y, sense=MAXIMIZE)
p.solve(SolverSettings())
print(p.Status.name, p.ObjValue, x.getValue(), y.getValue())
```

If this fails, do not move on to a real problem — fix connectivity first
(see Troubleshooting below).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `cudaErrorInsufficientDriver` or CUDA errors | Accidentally invoked local solve instead of remote service | Set `CUOPT_REMOTE_HOST=host.openshell.internal` and `CUOPT_REMOTE_PORT=5001` before solving |
| `from cuopt import routing` fails with CUDA / RMM init error | There is no GPU in this sandbox; routing has no remote-aware Python wrapper | Use REST instead: see "Vehicle routing (VRP, TSP, PDP) — REST only in this sandbox" above and `cuopt-server-api-python`'s `assets/vrp_*/` cookbook. Do **not** fall back to brute force or non-cuOpt methods |
| `403 Forbidden` | Wrong address or sandbox policy missing port | Use `host.openshell.internal`, not `localhost`. If address is correct, ask operator to run `nemoclaw_cuopt_setup.sh apply-policy` |
| `Connection refused` on `:5000` | REST service not running or host firewall blocking the port | Check if REST is needed; gRPC alone (5001) is sufficient for LP/MILP. If REST is needed, ask operator to start it |
| `available: none` from `probe_cuopt.py` | No cuOpt service running on host, ports not in sandbox policy, or host firewall | Ask operator to start a cuOpt server (`SETUP.md` > Starting the cuOpt server) and re-run `nemoclaw_cuopt_setup.sh apply-policy`; verify host firewall opens 5000 / 5001 |
| Connection timeout / hang | Server not running or host firewall blocking Docker | Ask operator to verify from host: `ss -tlnp \| grep 500` |
| Timeout through `10.200.0.1:3128` | Sandbox proxy cannot reach the destination | Ask operator to verify sandbox network policy includes the cuOpt ports |
| `ModuleNotFoundError` | Venv not activated — common in non-login shells (`bash -c '…'`) because `.bash_profile` only fires for login shells | Wrap the call in `bash -lc '…'` (preferred) or `source /sandbox/.openclaw-data/cuopt/bin/activate` before the python invocation |
| No `Using remote GPU backend` in output | Remote env vars not set or not picked up | Ensure `CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` are exported before the Python process starts |
