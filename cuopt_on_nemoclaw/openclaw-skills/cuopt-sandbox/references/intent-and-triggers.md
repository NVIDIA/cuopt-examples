# When to use cuOpt (intent, not exact wording)

Skills match **meaning**, not exact phrases. Do not require the user to
say "minimize", "optimal", or "build a schedule."

## Sandbox default

In this environment, **cuOpt is the solver for constructive planning
under constraints** — producing an assignment, schedule, roster, route,
or allocation that satisfies rules from uploaded data.

Use cuOpt when **both** are true:

1. **Constructive task** — the user wants you to **produce** a plan
   (assign, schedule, route, allocate, slot, place, match, fill a
   calendar, line up games/shifts/jobs, etc.)
2. **Constraint-bearing data** — CSVs or tables with capacities, slots,
   unavailability, demands, limits, pairing rules, or similar

If (1) and (2) hold → read **`optimization-from-data-orchestrator`**
and **`cuopt-sandbox`**, run gates, then formulate and solve. Wording
varies; the pattern does not.

## Language clusters (examples only — not exhaustive)

Any paraphrase in these families counts:

| Intent family | Example phrasings (same intent) |
|---|---|
| Schedule / timetable | "build a season schedule", "plan the season", "set up game times", "put these on the calendar", "when should each game happen" |
| Assign / allocate | "assign games to slots", "allocate shifts", "place jobs on machines", "who works when" |
| Route / visit | "plan deliveries", "best routes for trucks", "visit all stops" |
| Optimize explicitly | "minimize cost", "maximize profit", "best plan", "optimal mix" |
| Feasible / valid plan | "a valid schedule", "feasible assignment", "make it work under these rules", "respect all constraints" |

**Paraphrase rule:** If a reasonable planner would read the request as
"turn this data into a constraint-respecting plan," treat it as cuOpt —
even without optimize/minimize/best.

## Feasibility, minimize, and optimal (same solver here)

In this sandbox, these are **not different tiers**:

| User framing | Meaning | Action |
|---|---|---|
| Feasible / valid / make it work | Hard constraints must hold | MILP/LP/QP/routing with constraints; cuOpt finds a satisfying solution |
| Minimize / maximize / best / optimal | Hard constraints + objective | Same path; add or emphasize objective |
| No objective stated | Constraints only (+ optional default objective) | Model constraints; ask **one** objective question or state a default; still cuOpt |

**Wrong split:** "feasibility → greedy Python, optimization → cuOpt."
Feasibility under discrete rules **is** a MILP (or routing) problem;
cuOpt handles it.

## When cuOpt does **not** apply

Skip cuOpt (read/summarize/analyze only) when the user wants:

- column summaries, counts, charts, filters
- "what does this data contain?"
- explanation of an existing plan they already have
- forecasting or analytics without choosing a new plan

**Clarifier when unsure:** "Do you want a summary of the data, or a new
plan that satisfies these constraints?" — one question, not a questionnaire.

## Infrastructure triggers (always this skill)

Regardless of task wording, also read `cuopt-sandbox` when you see:

- `ImportError` / wrong cuOpt import path
- `cudaErrorInsufficientDriver` during solve
