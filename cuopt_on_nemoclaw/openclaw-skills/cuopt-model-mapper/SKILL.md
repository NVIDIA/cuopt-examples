---
name: cuopt-model-mapper
summary: Convert an interpreted optimization problem directly into cuOpt-native model construction for the fast path, asking only the minimum clarifying questions needed for a valid solve.
description: Use after optimization intent and basic data interpretation are established, when the goal is to solve quickly by mapping data directly into cuOpt rather than building a replayable intermediate artifact.
origin: skill-evolution
---

# cuOpt Model Mapper

Use this skill in the **fast path** after the request has already been identified as an optimization problem and the data has been interpreted enough to support model construction.

This skill takes the working interpretation of the problem and maps it directly into cuOpt-native model objects.

## Purpose

The fast path should avoid unnecessary architecture.

This skill exists to:
- build directly in cuOpt
- avoid a heavyweight intermediate model
- ask only the smallest number of blocking questions
- solve and return the result quickly

This skill is **not** for replayable/auditable artifact design. That belongs to a different path.

## Preconditions

Use this skill only when the following are already mostly clear:
- the request is genuinely an optimization problem
- the problem family is identified as LP / MILP / QP / routing
- the uploaded data has been inspected enough to infer likely roles
- only a small number of unresolved modeling questions remain

If those conditions are not met, first use:
- `optimization-intent-router`
- `optimization-mode-router` if execution mode may matter for replayability, audit, export, or reuse
- `tabular-optimization-ingestion`

## Core rule

For the fast path, map directly from the interpreted data into cuOpt structures.
Do not introduce a replayable intermediate artifact unless the user asks for replayability, auditability, export, or reuse.

## Workflow

### 1. Confirm the minimum viable formulation
Before building, confirm internally:
- what the decisions are
- what the objective is
- what the hard constraints are
- whether integrality is required
- whether the problem is numerical optimization or routing

Use the unresolved blocker list from ingestion as the starting point; do not reopen broad exploratory questioning unless the current interpretation is clearly inconsistent.

If one non-retrievable modeling choice would change the meaning of the solve, ask exactly one concise blocking question.

Examples:
- **"Do these production quantities need to be whole numbers?"**
- **"Must all demand be met, or can unmet demand be allowed with a penalty?"**
- **"Are these time windows mandatory, or just preferred?"**

### 2. Choose the cuOpt path

#### If LP / MILP
- hand off through `numerical-optimization-formulation` for formulation discipline
- use `cuopt-numerical-optimization-api-python` (or `cuopt-numerical-optimization-api-cli` for MPS inputs)
- preserve direct mappings from source data into variables, coefficients, RHS values, bounds, and objective terms

#### If QP
- hand off through `numerical-optimization-formulation` for formulation discipline
- use `cuopt-numerical-optimization-api-python`
- preserve direct mappings from source data into variables, quadratic objective terms, RHS values, and bounds

#### If routing
- hand off through `routing-formulation`
- use `cuopt-routing-api-python`
- map source data directly into locations, demands, vehicles, travel metrics, time windows, and pickup-delivery relationships

### 3. Preserve source-to-model traceability lightly
Even in fast mode, keep enough working traceability to avoid confusion during the same interaction.

At minimum, be able to state:
- which tables/columns drove the objective
- which tables/columns drove major constraints
- what each decision variable represents

Do this without building a full replayable artifact.

### 4. Solve with cuOpt
- use cuOpt whenever available and appropriate for the identified problem family
- verify solver status
- verify that the result is sensible against the modeled constraints

### 5. Explain results in user language
Return:
- recommended decisions
- objective value
- what the objective means in business terms
- any important bottlenecks or binding tradeoffs
- key assumptions that materially affect the answer

## Direct mapping guidance

### Numerical optimization mapping
Typical direct mappings include:
- per-row profit/cost columns → objective coefficients
- per-row resource consumption columns → constraint coefficients
- capacity table values → RHS limits
- min/max fields → variable bounds or additional constraints
- yes/no/open-close decisions → binary variables
- count decisions → integer variables

### Routing mapping
Typical direct mappings include:
- customer/location rows → stops
- coordinate or matrix tables → travel metric inputs
- demand fields → stop demand
- vehicle table → fleet definition
- depot fields → start/end nodes
- time window columns → service time constraints
- pickup/delivery ids → paired stop relationships

## Examples

### Example 1: direct LP/MILP mapping
Interpreted problem:
- one row per product
- `profit` column is objective coefficient
- `labor_hours` and `steel_units` are resource coefficients
- a separate capacity table provides RHS limits

Fast-path mapping:
- create one decision variable per product
- maximize total profit
- add one constraint per capacity/resource
- if products must be whole units, use integer variables

### Example 2: direct routing mapping
Interpreted problem:
- one row per customer stop
- vehicle table defines fleet
- travel-time matrix defines movement cost
- customer demand and time-window fields are available

Fast-path mapping:
- map stops, fleet, and travel data directly into cuOpt routing inputs
- ask only the final blocker question if needed, such as whether time windows are hard constraints
- solve and explain route recommendations

### Example 3: do not overbuild
Interpreted problem:
- user wants a one-off answer from uploaded data
- no replay, export, or audit requirement is mentioned

Correct behavior:
- map directly into cuOpt
- do not stop to build a replayable structured artifact
- keep only enough traceability to explain the result clearly in the current interaction

## Integrality rule

Do not default to continuous variables when the decisions represent discrete units, counts, assignments, vehicles, workers, items, or yes/no choices.

Ask if unclear, but if the problem statement strongly implies discreteness, model it as MILP rather than LP.

## Fast-path guardrails

- Do not build a heavyweight intermediate representation for one-off solves.
- Do not skip a critical clarifying question if it changes the model meaning.
- Do not ask a long questionnaire when one focused question will unblock the solve.
- Do not use cuOpt for tasks that are really descriptive analytics.
- Do not force routing when the problem is actually allocation without path construction.
- Do not force QP when the objective is linear.

## Result reporting requirements

Always report at least:
- solver status
- objective value
- brief explanation of what the objective means
- recommended decisions
- any assumptions or caveats that materially affect the result

If relevant, also mention which constraint or resource appears to be most limiting.

## Handoff guidance

- For LP / MILP:
  - use `numerical-optimization-formulation`
  - then use `cuopt-numerical-optimization-api-python` (or `cuopt-numerical-optimization-api-cli` for MPS inputs)
  - follow `cuopt-user-rules`
  - in sandbox contexts, follow `cuopt-sandbox` first when required

- For QP:
  - use `numerical-optimization-formulation`
  - then use `cuopt-numerical-optimization-api-python`
  - follow `cuopt-user-rules`
  - in sandbox contexts, follow `cuopt-sandbox` first when required

- For routing:
  - use `routing-formulation`
  - then use `cuopt-routing-api-python`
  - follow `cuopt-user-rules`
  - in sandbox contexts, follow `cuopt-sandbox` first when required

## Success criterion

This skill succeeds when the agent can go from:
- interpreted data
- plus zero or a few blocking clarifications

to:
- direct cuOpt model construction
- a validated solve
- and a clear business-facing answer

without introducing unnecessary replay/audit machinery.
