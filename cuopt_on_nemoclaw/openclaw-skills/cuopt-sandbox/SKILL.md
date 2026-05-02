---
name: cuopt-sandbox
description: Read FIRST whenever a request involves linear programming (LP), mixed-integer linear programming (MILP), quadratic programming (QP), or vehicle routing (VRP, TSP, PDP) — including small / pedagogical / made-up problems ("invent an LP example", "show me a small MILP", "find optimal X under constraints", "minimize cost", "plan deliveries", "schedule with constraints"). In this sandbox, cuOpt is the default solver and must be used whenever it is available; this skill points at the per-task skills (cuopt-user-rules, cuopt-lp-milp-api-python, cuopt-routing-api-python, lp-milp-formulation, etc.) and covers sandbox-specific setup (venv at /sandbox/.openclaw-data/cuopt, host.openshell.internal networking, REST 5000 / gRPC 5001).
---

# NVIDIA cuOpt (Sandbox)

Solve optimization problems using NVIDIA cuOpt from inside the sandbox.
This skill covers **sandbox-specific** setup — networking, venv, and connectivity.

> **In this sandbox, LP/MILP must be solved through the remote cuOpt service
> on the host, not the local CUDA runtime.** There is no GPU inside the
> sandbox. If you see `cudaErrorInsufficientDriver` or similar CUDA errors,
> you accidentally invoked a local solve — set `CUOPT_REMOTE_HOST` and
> `CUOPT_REMOTE_PORT` to use the remote service instead.

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

For **how to use cuOpt** (formulation, Python API, CLI, MPS format, routing, etc.),
read the sibling skills installed alongside this one in
`/sandbox/.openclaw-data/skills/`. Names follow stable suffix patterns
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

The exact names depend on the upstream cuOpt release. For example,
LP / MILP / QP may appear as `lp-milp-formulation` + `qp-formulation`
(older layout) or as a single `numerical-optimization-formulation`
(newer layout) — both are reachable through the `*-formulation`
pattern above. List the directory to see what's actually installed:

```bash
ls -1 /sandbox/.openclaw-data/skills/
```

These are vendored from <https://github.com/NVIDIA/cuopt/tree/main/skills> at
sandbox-setup time so the agent can read them locally — the sandbox cannot
reach `github.com` directly. To refresh, ask the operator to re-run
`./nemoclaw_cuopt_setup.sh install-skill <sandbox>` on the host.

## Environment

The cuOpt client and SDK are installed in a Python virtual environment at
`/sandbox/.openclaw-data/cuopt` (the default NemoClaw filesystem policy
marks `/sandbox` itself as read-only, so the venv lives in the writable
subtree under `/sandbox/.openclaw-data/`).

The sandbox's `/sandbox/.bashrc` auto-activates the venv and sets
`CUOPT_SERVER`, so in most interactive sessions no manual activation is
needed. To activate explicitly (scripts, non-interactive shells):

```bash
source /sandbox/.openclaw-data/cuopt/bin/activate
```

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

The `CUOPT_SERVER` environment variable (if set in `.bashrc`) contains the
REST `host:port` value.

## Capability check — run this FIRST

Before doing any cuOpt work, probe what the host is actually serving.
**The probe needs the cuOpt venv** for `grpcio`; if your shell is
non-interactive `~/.bashrc` may not have auto-activated it, so source
the venv explicitly:

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
skill in `/sandbox/.openclaw-data/skills/` — typically a `cuopt-*-api-python`
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
in `/sandbox/.openclaw-data/skills/`.

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
| `403 Forbidden` | Wrong address or sandbox policy missing port | Use `host.openshell.internal`, not `localhost`. If address is correct, ask operator to run `nemoclaw_cuopt_setup.sh apply-policy` |
| `Connection refused` on `:5000` | REST service not running or host firewall blocking the port | Check if REST is needed; gRPC alone (5001) is sufficient for LP/MILP. If REST is needed, ask operator to start it |
| `available: none` from `probe_cuopt.py` | No cuOpt service running on host, ports not in sandbox policy, or host firewall | Ask operator to start a cuOpt server (`SETUP.md` > Starting the cuOpt server) and re-run `nemoclaw_cuopt_setup.sh apply-policy`; verify host firewall opens 5000 / 5001 |
| Connection timeout / hang | Server not running or host firewall blocking Docker | Ask operator to verify from host: `ss -tlnp \| grep 500` |
| Timeout through `10.200.0.1:3128` | Sandbox proxy cannot reach the destination | Ask operator to verify sandbox network policy includes the cuOpt ports |
| `ModuleNotFoundError` | Venv not activated | Run `source /sandbox/.openclaw-data/cuopt/bin/activate` |
| No `Using remote GPU backend` in output | Remote env vars not set or not picked up | Ensure `CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` are exported before the Python process starts |
