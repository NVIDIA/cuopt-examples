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
./cuopt_claw/nemoclaw_cuopt_setup.sh add cuopt
```

> **Watch for the firewall warning banner.** If UFW is active and ports 5000/5001
> are not open to Docker interfaces, the script will print a prominent warning
> with `sudo ufw allow` commands to fix it. Sandbox connections will
> hang (timeout) until the firewall is configured.

## What the setup script does

- **add** — Add cuOpt to an existing sandbox: apply-policy → install → install-skill → test
- **apply-policy** — Merges cuOpt network rules into a running sandbox's policy
- **install** — Creates a Python venv (`/sandbox/cuopt`), installs `cuopt_sh_client`, `cuopt-cu12`, and `grpcio`, and configures `.bashrc` with the server alias
- **install-skill** — Uploads skill files from `cuopt_claw/openclaw-skills/` into the sandbox
- **test** — Smoke tests PyPI access and cuOpt server connectivity from inside the sandbox

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

To install cuopt into an existing venv instead of creating a new one (e.g. `/sandbox/.venv`):

```bash
CUOPT_VENV=.venv ./cuopt_claw/nemoclaw_cuopt_setup.sh add my-sandbox
```

## Updating skills

To modify agent skills, edit or add files under `cuopt_claw/openclaw-skills/`.
Each subdirectory containing a `SKILL.md` will be uploaded. Then re-run:

```bash
./cuopt_claw/nemoclaw_cuopt_setup.sh install-skill cuopt
```

## File locations

| What | Path |
|------|------|
| Setup script | `cuopt_claw/nemoclaw_cuopt_setup.sh` |
| gRPC probe | `cuopt_claw/probe_grpc.py` (uploaded to `/sandbox/probe_grpc.py`) |
| Skill source files | `cuopt_claw/openclaw-skills/cuopt/SKILL.md` |
| cuOpt venv in sandbox | `/sandbox/cuopt/` |

## Starting the cuOpt server

The cuOpt release includes two server interfaces. You can run either or both:

| Interface | Port | Protocol | How to start |
|-----------|------|----------|-------------|
| REST (Python) | 5000 | HTTP | `python3 -m cuopt_server.cuopt_service` |
| gRPC (native) | 5001 | HTTP/2 | `cuopt_grpc_server` (included in `libcuopt`) |

Install the server package (replace `cu12` with your CUDA version):

```bash
pip install cuopt-server-cu12 --extra-index-url=https://pypi.nvidia.com
```

To start the Python REST server:

```bash
python3 -m cuopt_server.cuopt_service
```

To start the gRPC server:

```bash
cuopt_grpc_server
```

Or run a server in the cuOpt container (see NVIDIA cuOpt documentation for container
instructions).

Verify what's running:

```bash
# REST server
curl http://localhost:5000/cuopt/health

# gRPC server
python3 probe_grpc.py
```

Leave the server(s) running — the sandbox connects through
`host.openshell.internal` on port 5000 (REST) and/or 5001 (gRPC).

## Troubleshooting

### Agent gets 403 Forbidden or connection timeout

- Verify the cuOpt server is running:
  - REST: `curl http://localhost:5000/cuopt/health`
  - gRPC: `python3 probe_grpc.py` (or from inside the sandbox: `python3 /sandbox/probe_grpc.py`)
- Check the firewall: `sudo ufw status` — ports 5000 and 5001 must be open on Docker bridges
- Re-run `./cuopt_claw/nemoclaw_cuopt_setup.sh apply-policy cuopt` to repair the network policy

## Advanced troubleshooting

> **Warning:** The steps below modify sandbox internals and can break your setup.
> Use at your own risk.

### Agent outputs raw XML tool calls instead of executing them

If you see raw `<tool_call>` XML in agent output, the inference API may not
support the `openai-responses` format. Switch to `openai-completions` in
the sandbox's `openclaw.json` configuration.
