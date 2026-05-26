---
name: tabular-optimization-ingestion
summary: Inspect uploaded or provided tabular data, infer likely optimization structure, and identify the smallest set of clarifications needed before building a cuOpt model.
description: Use when a user provides CSV, Excel, JSON-like tables, or similar structured data and asks a question that may become an LP, MILP, QP, or routing problem.
origin: skill-evolution
---

# Tabular Optimization Ingestion

Use this skill when the user provides raw or semi-structured data and asks a question that may require optimization.

The purpose of this skill is to bridge the gap between messy uploaded data and solver-ready model construction.

This skill does **not** solve the optimization problem itself. It inspects the data, infers likely modeling roles, and identifies what still needs clarification.

This skill refines the optimization interpretation using the uploaded data; it does not replace the earlier intent decision unless the data clearly contradicts it.

## Purpose

Users do not upload:
- objective vectors
- sparse matrices
- explicit decision variable definitions

They upload things like:
- products.csv
- capacity.xlsx
- orders.json
- travel_times.csv
- dealers.csv
- depots.csv

This skill turns raw tables into a candidate optimization interpretation.

## What this skill should produce

After inspection, produce a compact working interpretation containing:
- likely problem type: LP / MILP / QP / routing / unclear
- likely entities: products, resources, orders, locations, vehicles, customers, depots, time periods, etc.
- likely objective fields: profit, cost, margin, time, risk, distance, penalty
- likely constraint fields: capacity, demand, budget, inventory, hours, availability, limits, min/max bounds
- likely decision grain: per product, per route, per order, per plant, per vehicle-stop, etc.
- minimum unresolved ambiguities that require a user clarification

## Ingestion workflow

### 1. Identify table shape and grain
For each uploaded source, determine:
- what one row appears to represent
- whether the table is entity-level, transaction-level, matrix-like, or parameter-like

Examples:
- one row per product
- one row per plant
- one row per customer order
- one row per location pair
- one row per vehicle
- one row per time period

Always state the candidate row meaning before modeling from it.

### 2. Identify likely optimization roles by column meaning
Inspect column names and values for roles such as:

Objective-like fields:
- profit
- revenue
- margin
- cost
- travel_time
- distance
- risk
- penalty

Constraint-like fields:
- capacity
- demand
- available_hours
- budget
- max_load
- min_order
- inventory
- time_window_start
- time_window_end

Identifier / relationship fields:
- product_id
- plant_id
- order_id
- customer_id
- vehicle_id
- depot_id
- location_id
- origin / destination
- pickup / delivery

### 3. Infer candidate decision structure
Infer what the model is probably deciding.

Examples:
- units to produce by product
- units to ship from origin to destination
- whether to open a facility
- which vehicle serves which stops
- route sequence through locations
- allocation of budget across campaigns

Do not overcommit when the data supports multiple plausible decisions. Note the candidates and ask one focused question if needed.

### 4. Match the data pattern to a problem family
Use common table patterns:

#### LP / MILP patterns
Typical signs:
- product/resource tables
- profit and resource consumption by product
- capacity tables
- demand tables
- assignment tables
- open/close or yes/no columns implying integrality

#### QP patterns
Typical signs:
- covariance matrix
- risk matrix
- variance terms
- squared error context
- portfolio weights or regression-style structure

#### Routing patterns
Typical signs:
- locations / coordinates
- travel time or distance matrix
- depot + customer tables
- vehicle tables
- demands and capacities
- time windows
- pickup and delivery pairs

### 5. Identify only the critical ambiguities
Before handing off, identify the smallest set of unanswered questions that block valid model construction.

Examples:
- Are demands mandatory or forecast-only?
- Must decisions be integers?
- Are these time windows hard constraints?
- Is this travel matrix symmetric?
- Can unmet demand be allowed with penalty?
- Is profit net profit or revenue only?

Do **not** ask broad generic questions if the data already strongly suggests the answer.

## Preferred output format

Summarize findings compactly:

- **Candidate problem family:** ...
- **Row meanings:** ...
- **Likely decision:** ...
- **Likely objective:** ...
- **Likely constraints:** ...
- **Unresolved blockers:** ...

This summary should be short enough that a downstream formulation skill can use it directly.

## Column-role heuristics

Use these heuristics carefully. They guide interpretation but do not prove it.

### Cost / objective heuristics
- `cost`, `unit_cost`, `shipping_cost`, `expense` → likely minimization coefficient
- `profit`, `margin`, `contribution` → likely maximization coefficient
- `distance`, `travel_time`, `duration` → likely routing objective term or service constraint
- `risk`, `variance`, `covariance` → likely QP signal

### Capacity / demand heuristics
- `capacity`, `available`, `limit`, `max_*` → upper bound / resource constraint
- `demand`, `required`, `need` → demand fulfillment or service requirement
- `min_*`, `minimum_*` → lower bound or service rule

### Integrality heuristics
Treat MILP as likely when the data or request suggests:
- whole units
- counts of vehicles, workers, facilities, shifts, items
- yes/no choices
- on/off decisions
- assignment indicators

### Routing heuristics
Treat routing as likely when the core question depends on **path construction**, not merely allocation.

Signs include:
- stop sequence matters
- travel between locations matters
- vehicles start/end at depots
- travel matrix or coordinates are present
- pickup and delivery relationships appear

### Cross-row coupling heuristics

Duplicate values in a foreign-key column across rows of a parent table usually signal a **shared agent or resource** — one entity serving multiple parents. Shared resources need a mutual-exclusion constraint that no other column states.

- `coach_id`, `driver_id`, `instructor_id`, `nurse_id`, `operator_id` → shared agent; can serve only one parent at a time
- `machine_id`, `bay_id`, `tool_id` → shared resource; can host only one job at a time
- any FK column where `distinct_values < row_count` → check whether simultaneous assignment is allowed

A `*_unavailability` (or `*_availability`) table documents *known absences*; duplicated FK values document *implicit conflicts*. Treat both as constraint sources. Concrete check: for every FK-looking column in a parent table, compare distinct value count to row count, and surface the column when `distinct < rows`.

## Examples

### Example 1: product mix tables
Files include:
- `products.csv` with columns like `product`, `profit`, `labor_hours`, `steel_units`
- `capacity.csv` with columns like `resource`, `available`

Likely interpretation:
- one row in `products.csv` = one product
- one row in `capacity.csv` = one resource limit
- decision = how much of each product to produce
- objective = maximize profit
- constraints = labor and steel capacities

### Example 2: routing tables
Files include:
- `customers.csv` with `customer_id`, `demand`, `time_window_start`, `time_window_end`
- `vehicles.csv` with `vehicle_id`, `capacity`
- `travel_times.csv` with origin/destination or matrix-style travel times

Likely interpretation:
- customer rows are stops with demand and optional time windows
- vehicle rows define fleet capacity
- travel table defines movement cost/time
- likely problem family = routing

### Example 3: historical transaction table
File includes:
- `sales_history.csv` with `order_id`, `date`, `region`, `revenue`, `units_sold`

Likely interpretation:
- this may be analytics, not optimization, unless the user asks for a future decision under constraints
- do not invent decision variables from history alone without a decision-focused question

## Guardrails

- Do not assume every table with `cost` and `capacity` is automatically a valid optimization model.
- Do not mistake transaction history for decision variables without evidence.
- Do not treat forecast data as hard constraints unless the user implies that.
- Do not infer QP unless there is a real quadratic signal.
- Do not infer routing unless movement between locations is central to the decision.
- Prefer one precise clarification over a long list of speculative questions.

## Handoff guidance

- If the data suggests LP / MILP:
  - hand off to `lp-milp-formulation`
  - then to `cuopt-lp-milp-api-python` (or `cuopt-lp-milp-api-cli` for MPS inputs)

- If the data suggests QP:
  - hand off to `qp-formulation`
  - then to `cuopt-qp-api-python`

- If the data suggests routing:
  - hand off to `routing-formulation`
  - then to `cuopt-routing-api-python`

- If mode selection is still needed because replayability, audit, export, or reuse may matter:
  - use `optimization-mode-router` before deep model construction

- If optimization intent itself is still uncertain:
  - use `optimization-intent-router`

## Success criterion

This skill succeeds when the downstream model-building step can proceed with either:
- no clarification, or
- one or a few narrowly targeted clarifying questions

It fails when it produces a vague restatement of the table without narrowing the modeling interpretation.
