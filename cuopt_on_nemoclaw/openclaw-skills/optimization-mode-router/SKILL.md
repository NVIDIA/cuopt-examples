---
name: optimization-mode-router
summary: Decide whether to default to fast direct-to-cuOpt mode or ask whether the user wants replayable/auditable mode for reruns, review, export, or audit.
description: Use when a user asks a question that may be answered by solving an optimization problem from uploaded or provided data, and you need to decide whether to proceed directly to cuOpt or preserve a structured reusable model artifact.
---

# Optimization Mode Router

Use this skill when a user asks a question that may be answered by solving an optimization problem from uploaded or provided data, and you need to decide whether to:

- proceed with a **fast direct-to-cuOpt solve**, or
- offer a **replayable/auditable path** that preserves a structured model artifact for later reruns, review, export, or audit.

This skill is about **mode selection**, not full formulation. Its purpose is to keep the common path fast while surfacing stronger reproducibility only when it is actually useful.

## Read this when

Read this skill when all of the following are true:

1. The user appears to be asking a question that could become an LP, MILP, QP, or routing problem.
2. The user has provided data, or is expected to provide data.
3. You need to decide whether to:
   - go straight to a direct cuOpt solve, or
   - preserve a replayable/auditable artifact as part of the workflow.

## Do not use this skill for

- Pure formulation work after the execution mode has already been chosen.
- Pure cuOpt API usage when the user has already clearly chosen fast vs replayable mode.
- Non-optimization analytics questions.

## Default behavior

- Default to **Fast mode**.
- Do **not** ask about replayability/auditability unless there is a real signal that it matters.
- Avoid turning a straightforward optimization request into a heavy upfront questionnaire.

## Two modes

### Fast mode
Use Fast mode when the user appears to want the quickest route to an answer.

Behavior:
- inspect the provided data
- identify whether the request is LP, MILP, QP, or routing
- ask only the minimum necessary clarifying questions
- build the model directly in cuOpt
- solve and explain the result
- do not preserve a replayable model artifact unless requested

### Replayable / Auditable mode
Use this mode when the user wants reuse, traceability, or formal review.

Behavior:
- capture explicit assumptions
- record data-to-model mappings
- preserve a structured model specification or equivalent reusable artifact
- solve with cuOpt
- return both the answer and reusable/reviewable model metadata

## When to ask the mode-selection question

Ask the user to choose between Fast mode and Replayable/Auditable mode if any of the following are true:

1. The user explicitly asks for any of these:
   - save the model
   - rerun on new data
   - replay later
   - recurring or scheduled runs
   - audit trail
   - export the model
   - document assumptions
   - review the formulation
   - show how the data maps into the model

2. The request appears operational or recurring rather than one-off:
   - daily / weekly / monthly planning
   - production workflow
   - repeated scenario analysis
   - future datasets are expected

3. The user indicates a need for traceability or justification:
   - compliance
   - internal or external review
   - reproducibility
   - explicit explanation of assumptions or mappings

## When not to ask

Do **not** ask the mode-selection question when the request is clearly:
- one-off
- exploratory
- ad hoc
- speed-oriented

In those cases, proceed in **Fast mode** unless the user later asks for replayability, audit, export, or model persistence.

## Recommended user-facing phrasing

Preferred short form:

**Should I treat this as a one-off solve, or make it replayable/auditable too?**

Alternative longer form:

**I can do this in two ways: Fast mode for the quickest answer, or Replayable mode that also keeps a structured spec for reruns, audit, and reuse. Which do you want?**

## Decision rule

- If there is **no meaningful signal** for replayability/auditability → use **Fast mode** silently.
- If there **is** a meaningful signal → ask the mode-selection clarifier early.
- If the user chooses replayable/auditable mode → preserve the structured artifact and proceed.
- If the user chooses fast mode → proceed directly to cuOpt.

## Handoff guidance

After selecting a mode, hand off based on problem type:

- If the request is LP / MILP:
  - use `lp-milp-formulation`
  - then use `cuopt-lp-milp-api-python` (or `cuopt-lp-milp-api-cli` for MPS inputs)
  - in sandbox contexts, follow `cuopt-sandbox` first when required

- If the request is QP:
  - use `qp-formulation`
  - then use `cuopt-qp-api-python`
  - in sandbox contexts, follow `cuopt-sandbox` first when required

- If the request is routing (VRP / TSP / PDP):
  - use `routing-formulation`
  - then use `cuopt-routing-api-python`
  - in sandbox contexts, follow `cuopt-sandbox` first when required

- If the user is asking about server usage or deployment rather than solving a model directly:
  - use `cuopt-server-common` or `cuopt-server-api-python` as appropriate

- In all cuOpt user tasks:
  - follow `cuopt-user-rules`

## Operational notes

- This skill is about **execution mode selection**, not full mathematical modeling.
- Keep the user experience lightweight by default.
- Prefer direct-to-cuOpt for one-off work.
- Use replayable/auditable mode only when the user’s needs justify the extra structure.
