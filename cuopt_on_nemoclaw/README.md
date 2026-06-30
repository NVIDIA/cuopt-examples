# cuOpt + NemoClaw Setup Guide

The cuOpt server must be running on the host before the sandbox can connect to it.
If you don't have it running yet, see [Starting the cuOpt server](#starting-the-cuopt-server).

Install NemoClaw and then add cuOpt configuration.

### 1. Install NemoClaw if it's not already installed

For an interactive install of NemoClaw, do the following
and specify 'cuopt' as the sandbox name when prompted

```bash
curl -fsSL https://nvidia.com/nemoclaw.sh | bash
```

For a non-interactive install of NemoClaw you can set
the configuration with environment variables. See
the [NemoClaw documentation](https://docs.nvidia.com/nemoclaw/latest/inference/use-local-inference.html) for more details. For example:

```bash
export NVIDIA_API_KEY="nvapi-..."
export NEMOCLAW_PROVIDER=build
export NEMOCLAW_MODEL=nvidia/nemotron-3-super-120b-a12b
export NEMOCLAW_SANDBOX_NAME=cuopt

curl -fsSL https://nvidia.com/nemoclaw.sh | bash -s -- \
  --non-interactive --yes-i-accept-third-party-software
```

### 2. Add the cuOpt configuration to a sandbox

The 'add' command takes a sandbox name as an argument. Here we use 'cuopt' but
it can be any existing sandbox.

```bash
./nemoclaw_cuopt_setup.sh add cuopt
```

> **Watch for the firewall warning banner.** If UFW is active and ports 5000/5001
> are not open to Docker interfaces, the script will print a prominent warning
> with `sudo ufw allow` commands to fix it. Sandbox connections will
> hang (timeout) until the firewall is configured.

## What the setup script does

- **add** — Add cuOpt to an existing sandbox: apply-policy → install → install-skill → `test --smoke`
- **apply-policy** — Merges cuOpt network rules into a running sandbox's policy
- **install** — Creates a Python venv (`/sandbox/.openclaw-data/cuopt`), installs `cuopt_sh_client`, `cuopt-cu13`, and `grpcio`, and stamps the cuOpt venv activation file (`/sandbox/.bash_profile`)
- **install-activation** — Re-stamps `/sandbox/.bash_profile` without reinstalling the venv (use after changing `CUOPT_HOST`, `CUOPT_PORT`, or `CUOPT_VENV`)
- **install-skill** — Uploads skill files from `openclaw-skills/` into the sandbox, then vendors the upstream cuOpt skills (numerical optimization for LP/MILP/QP, routing, server, formulation, user-rules, skill-evolution) from `github.com/NVIDIA/cuopt/tree/release/26.06/skills` so the agent can read them without outbound HTTPS. Override the upstream ref via `CUOPT_SKILLS_REF` (default `release/26.06`); narrow what gets installed via `CUOPT_SKILLS_SKIP` (comma-separated globs, default `cuopt-install,*developer*,*-api-c`). Finally, the step writes a fresh `skills.entries.cuopt-sandbox.config.lastInstallAt` timestamp into `~/.openclaw/openclaw.json` so the gateway's config-reload watcher invalidates the cached `<available_skills>` snapshot — without this, skills uploaded after the agent's first run never appear in the prompt (see [How `<available_skills>` is cached](#how-available_skills-is-cached) below).
- **test** — Connectivity probe from inside the sandbox (`probe_cuopt.py` + pip check). Does **not** run solve smokes.
- **test --smoke** — Probe plus end-to-end LP/MILP/VRP solves via `/sandbox/smoke_*.py` when `install-skill` has uploaded them. LP/MILP run only if gRPC is reachable; VRP only if REST is reachable (per the probe's `available:` line).

### Version compatibility

`nemoclaw_cuopt_setup.sh` was last verified against **nemoclaw v0.0.55** and **openshell v0.0.44**. If your installed versions differ, the script prints a non-fatal banner at startup. Silence it with `NEMOCLAW_VERSION_CHECK=0`.

The public NemoClaw installer defaults to the `lkg` ref, which currently points at the same commit as **v0.0.55**. To pin explicitly:

```bash
NEMOCLAW_INSTALL_TAG=v0.0.55 \
  curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash -s -- \
  --non-interactive --yes-i-accept-third-party-software
```

## Getting cuOpt data into the sandbox

Upload files from the host:

```bash
openshell sandbox upload cuopt /path/to/local/file.mps /sandbox/workspace/
```

Or clone a git repository inside the sandbox to get sample datasets, for example:

```bash
# From inside the sandbox (nemoclaw cuopt connect)
git clone https://github.com/NVIDIA/cuopt repo
```

### Quick test with a sample dataset

After cloning, verify end-to-end with a small LP:

If you are running the Python service, use cuopt_sh

```bash
cuopt_sh -t LP /sandbox/repo/datasets/linear_programming/afiro_original.mps
```

If you are running the gRPC server, use cuopt_cli

```bash
cuopt_cli /sandbox/repo/datasets/linear_programming/afiro_original.mps
```

## Talking to the agent

```bash
openclaw agent --agent main -m "your prompt here"
```

Or use the interactive TUI:

```bash
openshell term
```

## Adding cuopt to an existing venv in a sandbox

To install cuopt into an existing venv instead of creating a new one (e.g. `/sandbox/.openclaw-data/.venv`):

```bash
CUOPT_VENV=.openclaw-data/.venv ./nemoclaw_cuopt_setup.sh add my-sandbox
```

## Updating skills

To modify agent skills, edit or add files under `openclaw-skills/`.
Each subdirectory containing a `SKILL.md` will be uploaded. Then re-run:

```bash
./nemoclaw_cuopt_setup.sh install-skill cuopt
```

## File locations

| What | Path |
|------|------|
| Setup script | `cuopt_on_nemoclaw/nemoclaw_cuopt_setup.sh` |
| Endpoint probe | `cuopt_on_nemoclaw/probe_cuopt.py` → `/sandbox/probe_cuopt.py` (REST + gRPC reachability) |
| Smoke tests | `smoke_lp.py`, `smoke_milp.py`, `smoke_vrp.py` → `/sandbox/` (pre-built; agent runs as-is — see skills) |
| Skill source files | `cuopt_on_nemoclaw/openclaw-skills/cuopt-sandbox/SKILL.md` |
| cuOpt venv in sandbox | `/sandbox/.openclaw-data/cuopt/` |

## Starting the cuOpt server

The cuOpt release includes two server interfaces. Run either or both via the
official cuOpt container — the sandbox expects them at ports 5000 (REST) and
5001 (gRPC).

| Interface | Host port | Container default | Selector |
|-----------|-----------|-------------------|----------|
| REST (Python) | 5000 | `CUOPT_SERVER_PORT` (8000) | unset / `CUOPT_SERVER_TYPE=rest` |
| gRPC (native) | 5001 | 5001 | `CUOPT_SERVER_TYPE=grpc` |

### Prerequisites

- NVIDIA driver + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host (`nvidia-ctk --version`).
- Docker can see the GPU: `docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi`.

Pick an image tag that matches your CUDA + Python; the latest stable line is
`nvidia/cuopt:latest-cuda13.0-py3.13` (Docker Hub, no auth needed). The same
image is published on NGC at `nvcr.io/nvidia/cuopt/cuopt:<tag>`.

```bash
export CUOPT_IMAGE=nvidia/cuopt:latest-cuda13.0-py3.13
docker pull "$CUOPT_IMAGE"
```

### REST server (port 5000)

```bash
docker run -d --name cuopt-rest --gpus all --restart unless-stopped \
  -p 5000:5000 -e CUOPT_SERVER_PORT=5000 \
  "$CUOPT_IMAGE"
```

Verify:

```bash
curl http://localhost:5000/cuopt/health
```

### gRPC server (port 5001)

```bash
docker run -d --name cuopt-grpc --gpus all --restart unless-stopped \
  -p 5001:5001 -e CUOPT_SERVER_TYPE=grpc \
  "$CUOPT_IMAGE"
```

Verify (from the host or the sandbox):

```bash
python3 probe_cuopt.py
```

### Running both at once

The two `docker run` commands above are independent — running both yields
`cuopt-rest` on 5000 and `cuopt-grpc` on 5001. They can share the same GPU.

Leave the server(s) running — the sandbox connects through
`host.openshell.internal` on port 5000 (REST) and/or 5001 (gRPC).

### Stopping or upgrading

```bash
docker stop cuopt-rest cuopt-grpc && docker rm cuopt-rest cuopt-grpc
docker pull "$CUOPT_IMAGE"   # then re-run the start commands
```

> Running the server natively (without Docker) is supported — install
> `cuopt-server-cu12` from `https://pypi.nvidia.com` and start
> `python3 -m cuopt_server.cuopt_service` (REST) or `cuopt_grpc_server`
> (gRPC). See the [upstream cuOpt docs](https://docs.nvidia.com/cuopt/) for
> details. The container path above is preferred because it pins CUDA and
> the Python toolchain to the cuOpt release.

## Troubleshooting

### Agent gets 403 Forbidden or connection timeout

- Verify the cuOpt server is running:
  - REST: `curl http://localhost:5000/cuopt/health`
  - Both at once (host or sandbox): `python3 probe_cuopt.py` (or from inside the sandbox: `python3 /sandbox/probe_cuopt.py`)
- Check the firewall: `sudo ufw status` — ports 5000 and 5001 must be open on Docker bridges
- Re-run `./nemoclaw_cuopt_setup.sh apply-policy cuopt` to repair the network policy

## Advanced troubleshooting

> **Warning:** The steps below modify sandbox internals and can break your setup.
> Use at your own risk.

### How `<available_skills>` is cached

OpenClaw assembles the `<available_skills>` block in the agent's system prompt
from a per-session snapshot stored at:

```
~/.openclaw/agents/<agentId>/sessions/sessions.json
```

The snapshot is built on the agent's *first* run for a session and reused on
every subsequent run. Skills written to disk *after* that first run will not
appear in the prompt until the snapshot is invalidated, even though
`openclaw skills list` (which reads disk directly) sees them.

Invalidation hooks (in OpenClaw source — `gateway/config-reload.ts`,
`agents/skills/refresh.ts`):

- The gateway watches `~/.openclaw/openclaw.json`. When any path under
  `skills.*` changes, it bumps the snapshot version and the next agent run
  rebuilds the prompt from disk.
- A filesystem watcher (chokidar) optionally watches `~/.openclaw/skills/`
  itself when `skills.load.watch` is enabled. In some sandbox configurations
  the watcher fires inconsistently, so the setup script does not rely on it.

`install-skill` triggers the config-reload hook by writing two
schema-defined fields into the sandbox's `~/.openclaw/openclaw.json`:

- `skills.load.watch: true` — enable the (best-effort) filesystem watcher.
- `skills.entries.cuopt-sandbox.config.lastInstallAt: <ISO timestamp>` —
  guarantees a non-empty config diff on every run.

If you upload skill files manually (without re-running `install-skill`), you
can force the same invalidation by hand:

```bash
openshell sandbox exec --name cuopt --no-tty -- python3 -c '
import json, time
p = "/sandbox/.openclaw/openclaw.json"
cfg = json.load(open(p))
cfg.setdefault("skills", {}).setdefault("load", {})["watch"] = True
cfg["skills"].setdefault("entries", {}) \
   .setdefault("cuopt-sandbox", {}) \
   .setdefault("config", {})["lastInstallAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(cfg, open(p, "w"), indent=2)'
```

To verify which skills the agent currently sees in `<available_skills>`,
ask it (the `openclaw skills list` CLI bypasses the snapshot):

```bash
openclaw agent --agent main -m "Use the read tool to read /sandbox/.openclaw/skills/cuopt-sandbox/SKILL.md ONLY if it is in your available_skills list. If it is not, output: NOT_IN_AVAILABLE_SKILLS"
```

### Agent outputs raw XML tool calls instead of executing them

If you see raw `<tool_call>` XML in agent output, the inference API may not
support the `openai-responses` format. Switch to `openai-completions` in
the sandbox's `openclaw.json` configuration.
