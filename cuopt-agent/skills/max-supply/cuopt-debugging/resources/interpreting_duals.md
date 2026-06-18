# Interpreting Dual Values, Reduced Costs, and Slack

`diagnostic_snippets.md` shows how to *read* `DualValue`, `ReducedCost`, and `Slack` off a solved
problem. This explains what they *mean* for the decision — turning solver output into "which
constraint is the binding bottleneck, what relaxing it is worth, and which unused option is the
closest near-miss."

> **Continuous models, linear constraints.** Duals and reduced costs exist for **continuous**
> (LP / QP) solutions off **linear** constraints. Two cases return none: an **integer model
> (MILP)** — **including the max-supply model** — has no usable duals, and a **quadratic
> _constraint_** makes cuOpt NaN-fill every dual (a quadratic _objective_ is fine — it is a
> quadratic _constraint_ that breaks them). `DualValue` / `ReducedCost` are not meaningful in
> either case. For a MILP, get the marginal value by **differencing adjacent solves** (re-solve
> with the bound relaxed by one unit and compare objectives), or read duals from the **LP
> relaxation**.

## Constraint dual value — the marginal value of relaxing a limit

A constraint's `DualValue` is the **sensitivity** of the optimum to that constraint: the change in
the optimal objective per unit relaxation of its right-hand side, holding everything else fixed —
the marginal value of one more unit of that limit.

- A **binding** constraint (`Slack ≈ 0`) carries a nonzero dual — it is actively limiting
  the objective. A **slack** constraint (`Slack > 0`) prices to ~0: relaxing it changes
  nothing, because it is not the bottleneck.
- **Rank the binding constraints by `|DualValue|`** → the largest is the highest-leverage limit to
  renegotiate: "relax this by one unit and the objective improves by `DualValue`."

```python
# Which constraints bind, and what each is worth (LP / QP only):
binding = [(c.ConstraintName, c.DualValue) for c in problem.getConstraints() if abs(c.Slack) < 1e-6]
for name, dual in sorted(binding, key=lambda kv: -abs(kv[1])):
    print(f"{name}: dual {dual:+.4g}  (objective change per unit relaxed)")
```

In the max-supply shape the constraints that typically bind are the **resource-hour capacities**
and the **per-period supply limits** — the dual tells you which machine-hour (e.g. a tight
`RES2` period) or which material is the binding bottleneck, and what one more hour or unit of supply
is worth in finished-goods terms. (Read it from the LP relaxation, since the model itself is a MILP.)

## Reduced cost — how far an unused option is from entering

A variable resting at a bound (often `0`) carries a `ReducedCost`: how much its objective
coefficient must improve before it would enter the optimal solution. It is the **near-miss** signal.

- A variable with `Value > 0` is already in the mix; its reduced cost is ~0.
- Among the variables left at `0`, the one with the **smallest `|ReducedCost|`** is closest to
  becoming worthwhile — the option to watch if a cost or yield shifts slightly.

```python
# Unused options ranked by how close they are to entering (LP / QP only):
near = [(v.VariableName, v.ReducedCost) for v in problem.getVariables()
        if abs(v.Value) < 1e-6 and abs(v.ReducedCost) > 1e-9]
for name, rc in sorted(near, key=lambda kv: abs(kv[1])):
    print(f"{name}: reduced cost {rc:+.4g}  (improve its coefficient by ~{abs(rc):.4g} to use it)")
```

## The decision read

Two questions answered straight from the duals:

- **Where to invest / what to renegotiate** — the binding constraint with the largest dual.
  Lift that limit and you gain the most per unit.
- **The closest near-miss** — the unused option with the smallest reduced cost. The first thing that
  would enter the plan if the economics shift.

Report both in decision language, not raw numbers: "the *RES2 machine-hour cap* is the binding
bottleneck — each extra hour is worth ~`X` finished units; *material Y* is the closest unused option,
~`Z` away from being worth procuring."

## Sign conventions

`DualValue` / `ReducedCost` signs depend on the constraint sense and the objective direction. Read
the **magnitude** for leverage ("how much per unit") and the **constraint sense** for direction
(relaxing a `<=` capacity raises a maximize objective). When unsure, confirm with a one-unit
re-solve: on an LP / QP the objective difference matches the dual to solver tolerance.
