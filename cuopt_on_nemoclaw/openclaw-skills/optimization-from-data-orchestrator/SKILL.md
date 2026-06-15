---
name: optimization-from-data-orchestrator
version: "26.06.01"
description: Coordinate uploaded data plus a natural-language question into interpretation, clarification, cuOpt solve, and a user-facing answer.
license: Apache-2.0
metadata:
  author: NVIDIA cuOpt Team
  tags:
    - cuopt
    - nemoclaw
    - orchestration
origin: skill-evolution
---

# Optimization From Data Orchestrator

Top-level coordinator when a user provides tabular data and wants a
constructive plan (schedule, assign, allocate, route — any wording).

**NemoClaw:** read `cuopt-sandbox/references/activation.md` for skill
order and cuOpt-before-heuristic rules.

## When to use

**Both** must hold:

- tabular data provided or expected (CSV, etc.)
- user wants a **plan from that data** (any phrasing; minimize/optimal not required)

Skip for **analytics-only** requests (summarize, chart, filter), fully
pre-specified math outside this flow, or explicit replayable/auditable path.

## Sequence

**Step 0 (NemoClaw — do not skip):** See `cuopt-sandbox` — probe → env →
smoke. No schedule/heuristic output before smoke passes.

1. **`optimization-intent-router`** — optimization family (LP/MILP/QP/routing)
2. **`optimization-mode-router`** — only if replay/audit/export signals
3. **`tabular-optimization-ingestion`** — table roles (interpretation only)
4. **`cuopt-model-mapper`** — clarify if needed, map to cuOpt, solve

Handoffs after step 4:

- LP / MILP / QP → `numerical-optimization-formulation` → `cuopt-numerical-optimization-api-python`
- Routing → `routing-formulation` → `cuopt-routing-api-python`

## Guardrails

- First solver that emits assignments/schedules must be **cuOpt** after step 0
- Ingestion steps do not authorize heuristic or greedy stand-ins
- Do not skip intent classification; do not use cuOpt for pure analytics
- One focused clarification beats a long questionnaire
