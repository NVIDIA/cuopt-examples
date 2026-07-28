# Routing (REST only in sandbox)

Vehicle routing (VRP, TSP, PDP) uses the **REST API** on port **5000**,
not either LP/MILP/QP gRPC execution path.

| Interface | Port | Client |
|---|---|---|
| LP / MILP / QP (Python) | 5001 gRPC | Async `Client` or legacy remote fallback |
| VRP / routing | 5000 REST | `cuopt_sh_client` / REST |

Host: `host.openshell.internal` (not `localhost`).

## Probe

If `probe_cuopt.py` shows `rest` in `available:`, REST is reachable.
If only `grpc`, skip VRP smoke — LP/MILP may still work.

## Smoke

```bash
bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && \
  python3 /sandbox/smoke_vrp.py'
```

Uses pre-installed `cuopt_sh_client` patterns; run as-is for gate checks.

## Skills after gates

1. `routing-formulation`
2. `cuopt-routing-api-python`
3. `cuopt-server-api-python` (REST payload shape)

## Defaults

- Minimal fleet + cost matrix for first solve; expand after status is
  terminal.
- One REST job at a time — see `references/long-running-jobs.md`.
