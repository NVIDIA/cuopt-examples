---
name: cuopt
description: Use NVIDIA cuOpt to solve vehicle routing (VRP/CVRPTW) and linear programming (LP/MIP) optimization problems. Use when the user asks to optimize routes, solve a routing problem, minimize cost, plan deliveries, solve an LP, or use cuOpt.
---

# NVIDIA cuOpt (Sandbox)

Solve optimization problems using NVIDIA cuOpt from inside the sandbox.
This skill covers **sandbox-specific** setup — networking, venv, and connectivity.

> **In this sandbox, LP/MILP must be solved through the remote cuOpt service
> on the host, not the local CUDA runtime.** There is no GPU inside the
> sandbox. If you see `cudaErrorInsufficientDriver` or similar CUDA errors,
> you accidentally invoked a local solve — set `CUOPT_REMOTE_HOST` and
> `CUOPT_REMOTE_PORT` to use the remote service instead.

For **how to use cuOpt** (formulation, Python API, CLI, MPS format, routing, etc.),
read the upstream skills at:
<https://github.com/NVIDIA/cuopt/tree/main/skills>

Key upstream skills:
- `cuopt-lp-milp-api-python` — LP/MILP with the Python SDK (Problem class, examples, status checking)
- `cuopt-lp-milp-api-cli` — LP/MILP via `cuopt_cli` with MPS files
- `cuopt-routing-api-python` — Vehicle routing (VRP, TSP, PDP) with Python
- `lp-milp-formulation` — How to go from problem text to formulation
- `cuopt-user-rules` — Behavior rules: clarify before coding, verify results

## Environment

The cuOpt client and SDK are installed in a Python virtual environment at `/sandbox/cuopt`.
Activate it before any cuOpt work:

```bash
source /sandbox/cuopt/bin/activate
```

If the venv doesn't exist, create it:

```bash
python3 -m venv /sandbox/cuopt
source /sandbox/cuopt/bin/activate
pip install cuopt-sh-client cuopt-cu12==26.04 grpcio --extra-index-url=https://pypi.nvidia.com
```

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

## Connectivity Checks — Do This First

**Always verify connectivity before solving.** The host may be running one or
both cuOpt services. Either service alone is sufficient for LP/MILP — use
whichever is available. If both are up, either path works.

Follow this checklist:

1. **Activate the venv**: `source /sandbox/cuopt/bin/activate`
2. **Probe gRPC (port 5001)**:
   ```bash
   python3 /sandbox/probe_grpc.py
   ```
   Expected: `server is reachable (host.openshell.internal:5001)`.
   If reachable, you can use the **Python SDK** or **`cuopt_cli`** (set
   `CUOPT_REMOTE_HOST` / `CUOPT_REMOTE_PORT`).
3. **Probe REST (port 5000)**:
   ```bash
   curl -sf http://host.openshell.internal:5000/cuopt/health
   ```
   Expected: JSON like `{"status":"RUNNING",...}`.
   If reachable, you can use **`cuopt_sh`** CLI or **`cuopt_sh_client`** Python client.
4. **If neither is reachable** — do not proceed. The cuOpt server is not
   running on the host. Ask the operator to start it.

**Valid configurations:**
- gRPC only (5001) — use Python SDK or `cuopt_cli`
- REST only (5000) — use `cuopt_sh -t LP file.mps` or `client.get_LP_solve("file.mps")`
- Both — use any tool; gRPC tools and REST tools both work for LP/MILP

When checking gRPC, look for `Using remote GPU backend` in solve output to
confirm the solve actually ran on the host.

## Using cuopt_cli (LP/MILP from MPS files)

`cuopt_cli` is a native binary that solves LP/MILP from MPS files. For remote
execution from the sandbox, set these environment variables:

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
cuopt_cli problem.mps
```

For MPS format, options, and examples, see the upstream skill `cuopt-lp-milp-api-cli`.

## Using the Python SDK (LP/MILP) — requires gRPC

The Python SDK solves remotely via the gRPC server (port 5001). If gRPC is
not available, use the REST path instead (`cuopt_sh` or `get_LP_solve()`).
Set the environment variables before running:

```bash
export CUOPT_REMOTE_HOST=host.openshell.internal
export CUOPT_REMOTE_PORT=5001
```

Quick working example (expected: Optimal, objective = 10, x = 2, y = 2):

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

p = Problem("QuickLP")
x = p.addVariable(lb=0, vtype=CONTINUOUS, name="x")
y = p.addVariable(lb=0, vtype=CONTINUOUS, name="y")
p.addConstraint(x + y <= 4, name="total")
p.addConstraint(x <= 2, name="cap_x")
p.addConstraint(y <= 3, name="cap_y")
p.setObjective(3*x + 2*y, sense=MAXIMIZE)
p.solve(SolverSettings())
print(p.Status.name, p.ObjValue, x.getValue(), y.getValue())
```

If configured correctly you will see `Using remote GPU backend` in the output.

For full API usage, modeling patterns, and examples, see the upstream skill
`cuopt-lp-milp-api-python`.

## Using the REST interface (cuopt_sh / cuopt_sh_client)

The REST interface on port 5000 supports LP/MILP and routing. Use it when
gRPC is unavailable, or when you prefer the REST path.

### LP/MILP via REST — CLI

```bash
cuopt_sh -t LP /path/to/problem.mps -i host.openshell.internal -p 5000
```

### LP/MILP via REST — Python

`get_LP_solve()` accepts these inputs:
- **MPS file path** (string ending in `.mps`) — the client parses it and sends JSON
- **`DataModel`** from `cuopt_mps_parser` — already parsed, sent as JSON
- **dict** — raw JSON problem data

Do **not** pass a `Problem` object from `cuopt.linear_programming.problem` —
that is the Python SDK class (gRPC path), not the REST client's `DataModel`.

```python
from cuopt_sh_client import CuOptServiceSelfHostClient

client = CuOptServiceSelfHostClient(
    ip="host.openshell.internal", port="5000"
)

# Simplest: pass an MPS file path directly
result = client.get_LP_solve("problem.mps")
print(result)
```

### Routing via REST — Python

```python
from cuopt_sh_client import CuOptServiceSelfHostClient

client = CuOptServiceSelfHostClient(
    ip="host.openshell.internal", port="5000"
)
solution = client.get_optimized_routes(data)
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `cudaErrorInsufficientDriver` or CUDA errors | Accidentally invoked local solve instead of remote service | Set `CUOPT_REMOTE_HOST=host.openshell.internal` and `CUOPT_REMOTE_PORT=5001` before solving |
| `403 Forbidden` | Wrong address or sandbox policy missing port | Use `host.openshell.internal`, not `localhost`. If address is correct, ask operator to run `nemoclaw_cuopt_setup.sh apply-policy` |
| `Connection refused` on `:5000` | REST service not running or host firewall blocking the port | Check if REST is needed; gRPC alone (5001) is sufficient for LP/MILP. If REST is needed, ask operator to start it |
| `server is not reachable` from `probe_grpc.py` | gRPC service not running, port 5001 not in sandbox policy, or host firewall | Verify gRPC server is running on host; ask operator to check policy and firewall |
| Connection timeout / hang | Server not running or host firewall blocking Docker | Ask operator to verify from host: `ss -tlnp \| grep 500` |
| Timeout through `10.200.0.1:3128` | Sandbox proxy cannot reach the destination | Ask operator to verify sandbox network policy includes the cuOpt ports |
| `ModuleNotFoundError` | Venv not activated | Run `source /sandbox/cuopt/bin/activate` |
| No `Using remote GPU backend` in output | Remote env vars not set or not picked up | Ensure `CUOPT_REMOTE_HOST` and `CUOPT_REMOTE_PORT` are exported before the Python process starts |

---

<!-- ============================================================
     TEMPORARY SDK REFERENCE — remove this section once upstream
     skills (cuopt-lp-milp-api-python, cuopt-lp-milp-api-cli) are
     updated with the same content.
     ============================================================ -->

## cuOpt Python SDK Quick Reference (LP/MILP)

> **This section is a temporary local copy of SDK patterns that belong in the
> upstream skills. It will be removed once the upstream skills are updated.**

### Imports

```python
from cuopt.linear_programming.problem import (
    Problem, CONTINUOUS, INTEGER, MINIMIZE, MAXIMIZE, LinearExpression,
)
from cuopt.linear_programming.solver_settings import SolverSettings
```

### Expression Style

cuOpt uses **operator overloading** for building constraints and objectives.
Do NOT pass coefficient dictionaries — `Variable` objects are not hashable.

```python
# ✅ CORRECT — operator overloading
problem.addConstraint(2*x + 3*y <= 120, name="resource")
problem.setObjective(40*x + 30*y, sense=MAXIMIZE)

# ❌ WRONG — dict-style coefficients (will fail)
problem.setObjective({x: 40, y: 30}, sense=MAXIMIZE)
```

For large numbers of terms, use `LinearExpression` to avoid recursion limits:

```python
expr = LinearExpression(vars_list, coeffs_list, constant=0.0)
problem.addConstraint(expr <= 100)
```

### Reading Results

After `problem.solve()`, results live on the **Problem object**, not a separate
solution object:

```python
problem.solve(settings)

# Status (PascalCase, not ALL_CAPS)
print(problem.Status.name)   # e.g. "Optimal", "FeasibleFound"

# Objective value
print(problem.ObjValue)

# Variable values
print(x.getValue())
print(y.getValue())
```

**LP status values:** `Optimal`, `NoTermination`, `NumericalError`,
`PrimalInfeasible`, `DualInfeasible`, `IterationLimit`, `TimeLimit`,
`PrimalFeasible`

**MILP status values:** `Optimal`, `FeasibleFound`, `Infeasible`,
`Unbounded`, `TimeLimit`, `NoTermination`

### Complete Working Example (Smoke Test)

This LP is a known-good test for the sandbox environment. Expected result:
Optimal, objective = 10, x = 2, y = 2.

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, MAXIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

problem = Problem("SmokeTest")

x = problem.addVariable(lb=0, vtype=CONTINUOUS, name="x")
y = problem.addVariable(lb=0, vtype=CONTINUOUS, name="y")

problem.addConstraint(x + y <= 4, name="total")
problem.addConstraint(x <= 2, name="cap_x")
problem.addConstraint(y <= 3, name="cap_y")

problem.setObjective(3*x + 2*y, sense=MAXIMIZE)

settings = SolverSettings()
problem.solve(settings)

print(f"Status:    {problem.Status.name}")   # Optimal
print(f"Objective: {problem.ObjValue}")      # 10.0
print(f"x = {x.getValue()}")                 # 2.0
print(f"y = {y.getValue()}")                 # 2.0
```

If running remotely, you should see `Using remote GPU backend` in the solver
log output — that confirms the solve ran on the host, not locally.

### MILP Example (Integer Variables)

```python
from cuopt.linear_programming.problem import Problem, CONTINUOUS, INTEGER, MINIMIZE
from cuopt.linear_programming.solver_settings import SolverSettings

problem = Problem("FacilityLocation")

# Binary variable: lb=0, ub=1, vtype=INTEGER
open_fac = problem.addVariable(lb=0, ub=1, vtype=INTEGER, name="open")
production = problem.addVariable(lb=0, vtype=CONTINUOUS, name="prod")

problem.addConstraint(production <= 1000 * open_fac, name="link")
problem.setObjective(500*open_fac + 2*production, sense=MINIMIZE)

settings = SolverSettings()
settings.set_parameter("time_limit", 120)
settings.set_parameter("mip_relative_gap", 0.01)

problem.solve(settings)

if problem.Status.name in ["Optimal", "FeasibleFound"]:
    print(f"Open: {open_fac.getValue() > 0.5}")
    print(f"Production: {production.getValue()}")
    print(f"Cost: {problem.ObjValue}")
```

### Common Mistakes

| Mistake | What happens | Fix |
|---------|-------------|-----|
| Dict-style coefficients `{x: 3}` | `TypeError: unhashable type` | Use operator overloading: `3*x` |
| `problem.Status.name == "OPTIMAL"` | Never matches (silent failure) | Use PascalCase: `"Optimal"` |
| Calling `getObjectiveValue()` | `AttributeError` | Use `problem.ObjValue` |
| Calling `solution.get_primal_solution()` | Wrong API layer | Use `x.getValue()` on each variable |
| Chained `+` with many vars | `RecursionError` | Use `LinearExpression(vars, coeffs)` |

### cuopt_cli with MPS Files

```bash
# Basic solve
cuopt_cli problem.mps

# With options
cuopt_cli problem.mps --time-limit 120 --mip-relative-tolerance 0.01

# Remote execution (from sandbox)
CUOPT_REMOTE_HOST=host.openshell.internal CUOPT_REMOTE_PORT=5001 cuopt_cli problem.mps
```

### MPS Format Quick Reference

```
NAME          <problem name>
ROWS
 N <obj>                    ← objective row (N = no constraint)
 L <name>                   ← ≤ constraint
 G <name>                   ← ≥ constraint
 E <name>                   ← = constraint
COLUMNS
 <var> <row> <value>        ← coefficient for variable in row
RHS
 <id> <row> <value>         ← right-hand side constants
BOUNDS                       ← optional (defaults: 0 ≤ x < ∞)
 LO <id> <var> <value>      ← lower bound
 UP <id> <var> <value>      ← upper bound
 FX <id> <var> <value>      ← fixed value
 FR <id> <var>              ← free variable (−∞ to +∞)
ENDATA
```

MPS **minimizes** by default. To maximize, negate objective coefficients and
negate the final objective value.
