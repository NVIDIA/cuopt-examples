---
name: cuopt-debugging
description: Troubleshoot cuOpt LP/MILP problems including errors, wrong results, infeasible solutions, performance issues, and status codes. Use when the user says something isn't working, gets unexpected results, or needs help diagnosing issues.
---

# cuOpt Debugging Skill

Diagnose and fix issues with cuOpt LP/MILP solutions, errors, and performance.

## Before You Start: Required Questions

**Ask these to understand the problem:**

1. **What's the symptom?**
   - Error message?
   - Wrong/unexpected results?
   - Empty solution?
   - Performance too slow?

2. **What's the status?**
   - `problem.Status.name` — what value does it show?

3. **Can you share?**
   - The error message (exact text)
   - The code that produces it
   - Problem size (variables, constraints)

## Quick Diagnosis by Symptom

### "Solution is empty/None but status looks OK"

**Most common cause: Wrong status string case**

```python
# ❌ WRONG - "OPTIMAL" never matches, silently fails
if problem.Status.name == "OPTIMAL":
    print(problem.ObjValue)  # Never runs!

# ✅ CORRECT - use PascalCase
if problem.Status.name in ["Optimal", "FeasibleFound"]:
    print(problem.ObjValue)
```

**Diagnostic code:**
```python
print(f"Actual status: '{problem.Status.name}'")
print(f"Matches 'Optimal': {problem.Status.name == 'Optimal'}")
print(f"Matches 'OPTIMAL': {problem.Status.name == 'OPTIMAL'}")
```

### "Objective value is wrong/zero"

**Check if variables are actually used:**
```python
for var in problem.getVariables():
    print(f"{var.VariableName} = {var.Value}")
print(f"Objective: {problem.ObjValue}")

# Or with direct variable references
for var in [x, y, z]:
    print(f"{var.VariableName}: {var.getValue()}")
```

**Common causes:**
- Constraints too restrictive (all zeros is feasible)
- Objective coefficients have wrong sign
- Wrong variable in objective

### "Infeasible" status

**For LP/MILP:**
```python
if problem.Status.name in ["PrimalInfeasible", "Infeasible"]:
    print("Problem has no feasible solution")
    # Review constraints for conflicts
    for c in problem.getConstraints():
        print(f"{c.ConstraintName}")
```

**Common causes:**
- Conflicting constraints (x <= 5 AND x >= 10)
- Bounds too tight
- Missing a "slack" variable for soft constraints

### "Integer variable has fractional value"

```python
# Check how variable was defined
int_var = problem.addVariable(
    lb=0, ub=10,
    vtype=INTEGER,  # Must be INTEGER, not CONTINUOUS
    name="count"
)

# Also check if status is actually optimal
if problem.Status.name == "FeasibleFound":
    print("Warning: not fully optimal, may have fractional intermediate values")
```

### "Unbounded" status

**Problem has no finite optimum:**
```python
if problem.Status.name in ["DualInfeasible", "Unbounded"]:
    print("Problem is unbounded - objective can improve infinitely")
```

**Common causes:**
- Missing variable upper/lower bounds
- Constraint direction wrong (>= instead of <=)
- Missing constraints

### "Maximum recursion depth exceeded" when building expressions

Building large objectives or constraints with many chained `+` operations can hit Python recursion limits. Use **LinearExpression** instead:

```python
from cuopt.linear_programming.problem import LinearExpression

# Instead of: expr = c1*v1 + c2*v2 + ... + cn*vn (many terms)
vars_list = [v1, v2, v3, ...]
coeffs_list = [c1, c2, c3, ...]
expr = LinearExpression(vars_list, coeffs_list, constant=0.0)
problem.setObjective(expr, sense=MINIMIZE)
```

See the LP/MILP "Building large expressions" section and reference models in the project for examples.

### OutOfMemoryError

**Check problem size:**
```python
print(f"Variables: {len(problem.getVariables())}")
print(f"Constraints: {len(problem.getConstraints())}")
```

**Mitigations:**
- Reduce problem size
- Use sparse constraint matrix
- Set time limit to get partial solution

## Status Code Reference

### LP Status Values
| Status | Meaning |
|--------|---------|
| `Optimal` | Found optimal solution |
| `PrimalFeasible` | Found feasible but may not be optimal |
| `PrimalInfeasible` | No feasible solution exists |
| `DualInfeasible` | Problem is unbounded |
| `TimeLimit` | Stopped due to time limit |
| `IterationLimit` | Stopped due to iteration limit |
| `NumericalError` | Numerical issues encountered |
| `NoTermination` | Solver didn't converge |

### MILP Status Values
| Status | Meaning |
|--------|---------|
| `Optimal` | Found optimal solution |
| `FeasibleFound` | Found feasible, within gap tolerance |
| `Infeasible` | No feasible solution exists |
| `Unbounded` | Problem is unbounded |
| `TimeLimit` | Stopped due to time limit |
| `NoTermination` | No solution found yet |

## Performance Debugging

### Slow LP/MILP Solve

```python
settings = SolverSettings()
settings.set_parameter("log_to_console", 1)  # See progress
settings.set_parameter("time_limit", 60)      # Don't wait forever

# For MILP, accept good-enough solution
settings.set_parameter("mip_relative_gap", 0.05)  # 5% gap
```

### Check Solve Time

```python
problem.solve(settings)
print(f"Solve time: {problem.SolveTime:.2f} seconds")
```

## Diagnostic Checklist

```
□ Status checked with correct case (PascalCase)?
□ All variables have correct vtype (INTEGER vs CONTINUOUS)?
□ Constraint directions correct (<= vs >= vs ==)?
□ Objective sense correct (MINIMIZE vs MAXIMIZE)?
□ Variable bounds specified where needed?
```

## Diagnostic Code Snippets

See [resources/diagnostic_snippets.md](resources/diagnostic_snippets.md) for copy-paste diagnostic code:
- Status checking
- Variable inspection
- Constraint analysis
- Memory and performance checks

## Interpreting Dual Values & Reduced Costs

When an LP/QP solve returns dual values and you need the *decision* read — which constraint is the binding bottleneck, what relaxing it is worth, and which unused option is the closest near-miss — see [resources/interpreting_duals.md](resources/interpreting_duals.md). (Integer models / MILP — and quadratic *constraints* — return no usable duals; that reference covers the fallback.)

## When to Escalate

File a GitHub issue if:
- Reproducible bug with minimal example
- Include: cuOpt version, CUDA version, error message, minimal repro code
