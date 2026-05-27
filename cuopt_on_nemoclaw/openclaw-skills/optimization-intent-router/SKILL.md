---
name: optimization-intent-router
summary: Detect when a user question should be treated as an optimization problem and route it toward LP, MILP, QP, routing, or non-optimization handling.
description: Use when a user provides data and asks a natural-language business or planning question that may require optimization rather than simple analytics.
origin: skill-evolution
---

# Optimization Intent Router

Use this skill when a user asks a question in natural language and it is not yet clear whether the request should be handled as:

- a numerical optimization problem (LP / MILP / QP)
- a routing problem (VRP / TSP / PDP)
- or a non-optimization task such as analytics, filtering, aggregation, forecasting, or explanation

This skill exists to decide whether cuOpt should be involved at all, and if so, which downstream formulation path should be used.

The classification from this skill is provisional. A later data-ingestion step may refine or correct the problem family if the uploaded tables clearly support a different interpretation.

## Purpose

The user often does not say:
- "this is an LP"
- "this is a MILP"
- "this is a routing problem"

Instead they ask questions like:
- "What’s the best production plan?"
- "How should we allocate inventory?"
- "What’s the optimal sales mix?"
- "How many trucks should go to each depot?"
- "Can you minimize delivery cost?"

Your job is to recognize when the request is really asking for an optimization model.

## Core rule

Route to optimization only when the user is asking for the **best / optimal / minimum / maximum / least-cost / highest-profit** plan, allocation, assignment, schedule, route, or mix **subject to constraints or tradeoffs**.

If the user is only asking for:
- descriptive statistics
- filtering
- counting
- sorting
- charting
- SQL-style aggregation
- explanation of existing data

then do **not** force the request into optimization.

## Signals that this is an optimization task

Strong signals:
- words like **optimize**, **optimal**, **best**, **maximize**, **minimize**
- resource tradeoffs: capacity, budget, time, labor, inventory, demand, hours, materials
- decision language: how much, how many, which, assign, allocate, route, schedule, choose
- explicit constraints: at most, at least, must, cannot exceed, within budget, limited by
- competing objectives: profit vs capacity, cost vs service, coverage vs distance

Weaker but meaningful signals:
- "What should we do?"
- "What is the best plan?"
- "How should we allocate this?"
- "How can we reduce cost while meeting demand?"

When weaker signals appear, inspect whether there are real constraints and decisions. If yes, treat it as optimization.

## Route classification

### Route to LP
Use LP when:
- the objective is linear
- the constraints are linear
- decision variables can be continuous or fractional

Common examples:
- product mix
- production planning
- blending
- budget allocation
- transportation flow without integrality requirements

### Route to MILP
Use MILP when:
- the model is otherwise linear
- but some decisions must be integer or binary

Common signals:
- units must be whole numbers
- yes/no decisions
- open/close decisions
- assign-or-not decisions
- minimum lot sizes
- discrete staffing or vehicle counts

Common examples:
- facility opening
- workforce scheduling with headcounts
- assignment with binary decisions
- product counts that must be whole

### Route to QP
Use QP when:
- the objective contains squared terms or interactions
- the user wants quadratic minimization under linear constraints

Common signals:
- variance minimization
- least squares
- portfolio optimization with covariance / risk terms
- quadratic penalty terms

If the user is maximizing a quadratic expression, note that the modeling path may require reformulation as a minimization of the negated objective.

### Route to routing
Use routing when the decisions are fundamentally about movement through locations.

Common signals:
- deliveries
- pickups and dropoffs
- stops
- depots
- vehicles
- routes
- travel time / distance / cost matrices
- time windows
- capacities on vehicles
- pickup-delivery pairing

Common routing types:
- TSP: one route, visit locations
- VRP: multiple vehicles, capacities and/or time limits
- PDP: paired pickups and deliveries

### Route to non-optimization handling
Do **not** route to cuOpt when the user is asking for:
- summaries
- analytics
- cleaning
- forecasting without optimization
- dashboards / charts
- explanation of data patterns
- SQL / filtering tasks

## Ambiguity handling

If it is unclear whether the request is optimization or analytics, ask a concise clarifier such as:

- **"Are you asking for a summary of the data, or the best decision under constraints?"**
- **"Do you want analytics from the data, or should I optimize a plan from it?"**

If it is clearly optimization but unclear which family applies, ask the minimum clarifier needed.

Examples:
- **"Do these quantities need to be whole numbers, or can fractional values be allowed?"**
- **"Is this about assigning routes/vehicles to locations, or just allocating quantities across products/resources?"**
- **"Is the objective linear, or does it include variance / squared penalties / interaction terms?"**

## Required output of this skill

Before handing off, produce an internal working conclusion with at least:
- `is_optimization`: yes / no
- `problem_family`: lp | milp | qp | routing | unknown
- `why`: short explanation grounded in the user’s wording and available data
- `missing_information`: only the minimum unresolved items

## Handoff guidance

- If `problem_family = lp | milp`:
  - hand off to `numerical-optimization-formulation`
  - then to `cuopt-numerical-optimization-api-python` (or
    `cuopt-numerical-optimization-api-cli` for MPS inputs)

- If `problem_family = qp`:
  - hand off to `numerical-optimization-formulation`
  - then to `cuopt-numerical-optimization-api-python`

- If `problem_family = routing`:
  - hand off to `routing-formulation`
  - then to `cuopt-routing-api-python`

- If `is_optimization = yes` and there is a meaningful signal that replayability, audit, export, or reuse may matter:
  - use `optimization-mode-router` before deep data interpretation or model construction

- If `is_optimization = no`:
  - do not invoke cuOpt just because the data could in theory be optimized

## Examples

### Example 1: product mix question
User says:
> "I uploaded a product table and a capacity table. What’s the best production plan?"

Interpretation:
- this is optimization
- likely LP or MILP
- the user is asking for the best decision under resource constraints

### Example 2: routing question
User says:
> "I uploaded depots, customers, and a travel-time matrix. What’s the cheapest delivery plan?"

Interpretation:
- this is optimization
- specifically routing
- path construction and travel costs are central to the decision

### Example 3: analytics question
User says:
> "I uploaded sales.csv. Which product had the highest revenue last month?"

Interpretation:
- this is not optimization
- it is descriptive analysis over existing data
- do not route to cuOpt

## Behavioral guardrails

- Do not label a request as optimization only because it contains numbers.
- Do not force a routing interpretation when the task is really allocation or assignment without path planning.
- Do not force LP/MILP when the question is clearly descriptive analytics.
- Prefer one short clarifying question over building the wrong model.
- When the user asks for the best decision under constraints, prefer optimization even if they do not use formal mathematical language.
