---
name: optimization-from-data-orchestrator
summary: Coordinate the fast-path workflow for turning uploaded data and a natural-language question into the right optimization interpretation, clarification, cuOpt solve, and user-facing answer.
description: Use when a user uploads or provides data and asks a question that may be answered by optimization. This skill sequences optimization-intent-router, optimization-mode-router, tabular-optimization-ingestion, formulation skills, and cuOpt model-building skills.
origin: skill-evolution
---

# Optimization From Data Orchestrator

Top-level coordinator for the fast path when a user provides data and asks a question that may be optimization. Sequences the supporting skills so the agent does not jump straight from uploaded data into a solver call.

## When to use

All three must hold:
- the user has provided or is expected to provide data
- the question may be asking for the best / optimal / minimum / maximum decision under constraints
- the request is not yet so fully specified that you can call the solver directly

Skip this skill when the user is clearly asking for non-optimization analytics, the optimization problem is already fully specified mathematically, or the user has already chosen a dedicated replayable/auditable path.

## Sequence

**Step 0 (NemoClaw sandbox only — do not skip):** `cuopt-first` →
probe → `cuopt-remote-env` → smoke test. **No user-visible schedule,
assignment, heuristic plan, or feasibility verdict before step 0
completes.** Data files may be read for column/constraint discovery only.

Run these in order, but skip any step already settled from context. Default to fast mode; surface replayable/auditable mode only on a real signal (reruns, audit, export, recurring planning).

1. **`optimization-intent-router`** — decide whether this is optimization at all and which family (LP / MILP / QP / routing). If non-optimization, stop the optimization flow.
2. **`optimization-mode-router`** — *only if* there is a signal that replayability, audit, export, or recurring runs may matter. Otherwise stay in fast mode silently.
3. **`tabular-optimization-ingestion`** — identify row grain and table roles, infer likely objective and constraint fields, refine the family classification if the data clearly supports a different one, and surface any blockers. **Output interpretation only — not a schedule or heuristic solve.**
4. **`cuopt-model-mapper`** — ask at most the final blocking clarification, then map directly into cuOpt and solve.

Family-specific handoffs after step 4:
- LP / MILP / QP → `numerical-optimization-formulation` then `cuopt-numerical-optimization-api-python` (or `cuopt-numerical-optimization-api-cli` for MPS inputs)
- Routing → `routing-formulation` then `cuopt-routing-api-python`

## Guardrails

- **In NemoClaw sandbox:** run `cuopt-first` step 0 (probe → env → smoke)
  before any optimization **answer** — ingestion steps do not authorize
  heuristic schedules or feasibility substitutes.
- Do not skip intent classification and jump directly to cuOpt from raw data
  **without** step 0 infrastructure gates — but step 0 is fast and mandatory.
- Do not ask a long questionnaire before inspecting the uploaded data.
- Do not trigger replayable/auditable mode by default — only when the user signals reuse, audit, export, or recurring runs.
- Do not let ingestion become solver construction; the steps stay distinct.
- Do not use cuOpt for descriptive analytics tasks.
- **Do not produce a heuristic/greedy/backtracking schedule during steps
  1–3** as a stand-in for cuOpt; the first solver that emits assignments
  must be cuOpt after step 0 passes.
