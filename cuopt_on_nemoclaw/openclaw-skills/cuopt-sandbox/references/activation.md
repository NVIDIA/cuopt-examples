# Skill activation and routing (NemoClaw sandbox)

OpenClaw matches skills from **`name`** and frontmatter **`description`**
in `<available_skills>`. Behavioral rules live here and in sibling skills
— not stuffed into `description`.

## Skill order for CSV upload + plan request

When the user uploads tabular files and asks for a schedule, assignment,
roster, allocation, or route (any wording):

1. **`optimization-from-data-orchestrator`** — workflow sequence
2. **`cuopt-sandbox`** — probe/smoke gates, capability-based Python gRPC
3. Downstream: intent-router → ingestion → model-mapper → vendored API skills

Also loaded every session: bundled **`cuopt-setup`** guardrail (absolute paths).

## cuOpt before custom Python

The first code path that **emits** a schedule, roster, or assignment must
be cuOpt after probe/smoke — not a greedy, backtracking, or hand-rolled
scheduler.

Only bypass cuOpt when:

1. User explicitly wants a manual/heuristic algorithm **instead of** cuOpt
2. Analytics only (summarize/chart — no new plan)
3. Probe shows host cuOpt unreachable — report; no greedy substitute

## Intent (not exact phrases)

See `references/intent-and-triggers.md` — constructive task + constraint
data → cuOpt; feasible/minimize/optimal share one solver path.
