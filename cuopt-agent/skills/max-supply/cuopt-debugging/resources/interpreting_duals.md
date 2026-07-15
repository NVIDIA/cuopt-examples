# Interpreting Dual Values, Reduced Costs, and Slack

`diagnostic_snippets.md` shows how to *read* `DualValue`, `ReducedCost`, and `Slack` off a solved
problem. This page explains what they *mean* for the decision — turning solver output into "which
constraint is the binding bottleneck, what relaxing it is worth, and which unused option is the
closest near-miss."

> **Continuous models, linear constraints.** Duals and reduced costs exist for **continuous**
> (LP / QP) solutions off **linear** constraints — an **integer model (MILP)**, **including the
> max-supply model**, returns none. The full availability rule (including the
> quadratic-constraint case) is in the `cuopt-numerical-optimization-api` skill under *Dual
> Values*. At runtime, key off the returned values: finite duals are provided, NaN-filled are
> not. For a MILP, get the value of one more unit by **differencing adjacent solves** (re-solve
> with the bound relaxed by one unit and compare objectives); duals of the **LP relaxation**
> are a quicker guide, but the integer optimum can respond differently — differencing is the
> ground truth.

## Constraint dual value — the marginal value of relaxing a limit

A constraint's `DualValue` is the **sensitivity** of the optimum to that constraint: the marginal
rate at which the objective improves as that limit relaxes, holding everything else fixed. It is a
derivative, not a per-unit forecast — over a finite step (even one unit) the solution can
restructure and the rate change along the way, and under **degeneracy** (common in practice) the
rate is one-sided, so read it as a direction (see *When a dual is soft*). For the actual value of a
finite relaxation, difference two solves.

- The implication runs **one way**: a **slack** constraint (`Slack > 0`) always prices to ~0 —
  relaxing it changes nothing, because it is not the bottleneck. But `Slack ≈ 0` does **not**
  guarantee a nonzero dual: a binding constraint can still price to 0 (a form of degeneracy — see
  *When a dual is soft*).
- **Rank the binding constraints by `|DualValue|`** → a shortlist of the highest-leverage limits to
  renegotiate. Treat it as a shortlist, not a verdict: under degeneracy the dual solution itself is
  non-unique, so even the ordering can shift between equally optimal solves — confirm the top
  lever with a differencing re-solve (see *When a dual is soft*). One catch: a dual is
  objective-units **per unit of that constraint**, so the raw ranking only makes sense across
  constraints in **comparable units**
  (hours vs hours). To rank a machine-hour cap against a material-tonnage limit, put them on a
  common scale first — e.g. multiply each dual by a realistic relaxation step, or compare the value
  of a 1% relaxation (`|DualValue| × 0.01 × |RHS|`).

```python
# Which constraints bind, and each one's returned dual (LP / QP only).
# The |dual| ranking is meaningful within comparable-unit constraints:
binding = [(c.ConstraintName, c.DualValue) for c in problem.getConstraints() if abs(c.Slack) < 1e-6]
for name, dual in sorted(binding, key=lambda kv: -abs(kv[1])):
    print(f"{name}: dual {dual:+.4g}  (marginal rate as this limit relaxes)")
```

In the max-supply model — this agent's multi-period supply-chain planning example — the
constraints that typically bind are the **resource-hour capacities**
and the **per-period supply limits** — the dual prices each one: the marginal rate, in
finished-goods terms, at which a tight resource period (e.g. `RES2`) or a material's supply limit
pays off as it relaxes. Hour-caps rank against hour-caps and supply limits against supply limits;
across the two, convert to a common scale first. (The model itself is a MILP, so read this from the LP relaxation
as a guide and difference two MILP solves for the real number.)

## Reduced cost — how far an unused option is from being worth using

A variable resting at a bound (often `0`) carries a `ReducedCost` — a one-way threshold on its
objective coefficient: improve the coefficient by **less** than `|ReducedCost|` and leaving the
variable at its bound stays optimal; improve it by more and using the variable **can** start to
pay off. (The returned value certifies the first direction, not the second — degeneracy again.)
It is the **near-miss** signal.

- A variable strictly **between** its bounds prices to ~0. One pressed against an *upper* bound can
  carry a nonzero reduced cost with `Value > 0` — there its **magnitude** is the marginal value of
  raising that bound; read the direction as for any bound relaxation (see *Sign conventions*).
- A variable **at its bound** can also price to ~0 — degeneracy again: an alternative optimum uses
  it with no coefficient change at all (the mirror of a binding constraint with a zero dual).
- Among the variables left at `0` with a clearly nonzero reduced cost, the one with the
  **smallest `|ReducedCost|`** is closest to becoming worthwhile — the option to watch if a cost
  or yield shifts slightly. Same units catch as the dual ranking: a reduced cost is
  objective-units per unit of *that variable*, so sort only
  variables in comparable units against each other — or compare each `|ReducedCost|` as a fraction
  of its own objective coefficient ("needs a 3% price move" vs "needs a 40% one").

```python
# Unused options ranked by how close they are to paying off (LP / QP only).
# Compare |reduced cost| within comparable-unit variables:
near = [(v.VariableName, v.ReducedCost) for v in problem.getVariables() if abs(v.Value) < 1e-6]
for name, rc in sorted(near, key=lambda kv: abs(kv[1])):
    note = ("already interchangeable — degenerate" if abs(rc) < 1e-9
            else f"~{abs(rc):.4g} coefficient improvement before it pays off")
    print(f"{name}: reduced cost {rc:+.4g}  ({note})")
```

## The decision read

Two questions the duals point to — confirm any number you quote with a differencing re-solve:

- **Where to invest / what to renegotiate** — the binding constraint with the largest dual among
  comparable-unit limits (or after the common-scale conversion above): the first lever to test
  for relaxing.
- **The closest near-miss** — the unused option with the smallest reduced cost, compared in like
  units or as a fraction of its own coefficient. The first thing that would enter the plan if the
  economics shift.

Report both in decision language, not raw numbers: "the *RES2 machine-hour cap* is the binding
bottleneck — each extra hour is worth ~`X` finished units; *material Y* is the closest unused option,
~`Z` away from being worth procuring."

## When a dual is soft (degeneracy)

A simplex dual is exact for the basis the solver returned, but at a **degenerate** optimum — many
constraints binding at once (a lot of `Slack ≈ 0`) — that basis is one of several, so the dual is
one-sided and non-unique. It reads most precise exactly where it is least reliable, the common case
on large LPs.

Which solver ran matters too: cuOpt **often returns no basis at all** — the first-order **PDLP**
path (common on large LPs, and one arm of the concurrent default) produces duals only to the
convergence tolerance, and the same holds for any **barrier** / interior-point solve without
crossover. Basis-free duals get the same treatment: leverage and direction, not exact rates, and
at-bound reduced costs are not the crisp zero / nonzero split a simplex basis gives.

- Use the **ranking** of binding constraints (within comparable units) as a shortlist and a single
  dual as a *direction* ("this is the lever to renegotiate"), not a hard per-unit rate — the dual
  solution is non-unique under degeneracy, so even the ordering can shift between equally optimal
  solves. Confirm the lever you act on with a differencing re-solve.
- Quote a finite change only from a differencing re-solve: the dual is the rate at the current
  optimum, and the realized change over a step can differ from `dual × step` (the active set can
  change along the way, degenerate or not).

## Sign conventions

`DualValue` / `ReducedCost` signs depend on the constraint sense and the objective direction. Read
the **magnitude** for leverage ("how much per unit") and the **constraint sense** for direction
(relaxing a `<=` capacity raises a maximize objective). When unsure, re-solve with the bound
slightly relaxed: the sign of the objective change gives the direction, and the difference itself
is the number to quote for a finite step (see *When a dual is soft*).
