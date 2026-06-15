# Environment and networking

## Sandbox layout

| Path | Purpose |
|---|---|
| `/sandbox/` | Workspace root — scripts, some uploads |
| `/sandbox/.openclaw/workspace/` | **Common** chat/workspace file uploads |
| `/sandbox/workspace/` | Alternative upload target (openshell) |
| `/sandbox/probe_cuopt.py` | Connectivity probe (no env side effects) |
| `/sandbox/smoke_*.py` | Gate 3 smoke tests |
| `/sandbox/.openclaw-data/cuopt/bin/activate` | cuOpt Python venv |
| `/sandbox/.openclaw/skills/` | Installed skills (upstream + local) |

## Host endpoints

| Service | Host:port | Notes |
|---|---|---|
| gRPC (LP/MILP/QP) | `host.openshell.internal:5001` | Requires `CUOPT_REMOTE_*` |
| REST (VRP) | `host.openshell.internal:5000` | No remote env vars |

From inside the sandbox container, `localhost` points at the sandbox —
not the host cuOpt services.

## Capability check (probe)

```bash
bash -lc 'python3 /sandbox/probe_cuopt.py'
```

Read `available:` — typical values: `grpc`, `rest`, `rest grpc`, or empty
if host services are down.

| `available:` | Implication |
|---|---|
| `grpc` | LP/MILP/QP path viable after env + smoke |
| `rest` | VRP REST viable |
| `rest grpc` | Both paths |
| (empty / errors) | Report to user; do not invent heuristics as substitute |

Probe success ≠ ready to solve — still run env + smoke for gRPC.

## Remote-first workflow

1. Probe → note `available:`
2. For gRPC: export vars → smoke_lp (→ smoke_milp if scheduling)
3. For routing only: smoke_vrp if `rest` present
4. Read formulation + API skills → build model
5. Solve once; poll until terminal — `references/long-running-jobs.md`

## Path quirks

Tilde paths (`~/file.csv`) may fail in some tool contexts — prefer
`/sandbox/...` absolute paths.
