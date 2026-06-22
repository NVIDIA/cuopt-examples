# cuOpt Agent

Reference optimization agent built on [NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/) (NAT) with GPU-accelerated LP/MILP solving powered by [NVIDIA cuOpt](https://developer.nvidia.com/cuopt).

## Table of Contents

- [Overview](#overview)
- [Software Components](#software-components)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Try It Out](#try-it-out)
- [Ways to Run the Agent](#ways-to-run-the-agent)
  - [Production (Docker Compose)](#production-docker-compose)
  - [Development (Docker Compose)](#development-docker-compose)
  - [Local Installation (Advanced)](#local-installation-advanced)
- [Skills](#skills)
- [Services](#services)
- [Evaluation](#evaluation)
- [For AI Agents](#for-ai-agents)
- [Project Structure](#project-structure)
- [References](#references)
- [License](#license)

## Overview

The cuOpt Agent is a reference optimization assistant that translates natural-language problem descriptions into mathematical models, solves them on the GPU with NVIDIA cuOpt, and returns explained results. It ships with a **multi-period supply chain planning** scenario (max-supply) as its built-in use case, but the architecture is designed to be extended to other LP/MILP domains by adding new skills, data files, and configs. It is built as a [LangChain Deep Agents](https://www.langchain.com/) workflow on top of NAT, with structured skills that make the path from problem text to correct formulation more reliable. The agent uses an **orchestrator-subagent** pattern: the orchestrator receives user queries and delegates optimization work to a specialized cuOpt subagent via the `task()` tool, keeping coordination logic separate from problem-solving logic.

**Key features:**

- **GPU-accelerated solver** -- cuOpt LP/MILP solver for fast optimization on NVIDIA GPUs.
- **Structured skills** -- Parsing, modeling, debugging, and supply-chain planning skills give the agent rules and reference models so it formulates correctly on the first try.
- **Mandatory ambiguity handling** -- When problem text is ambiguous, the agent must clarify or solve all plausible interpretations.
- **YAML-driven configuration** -- Agents, LLMs, and workflows are defined in config files; tune behavior without code changes.
- **Web UI** -- Chat interface for interacting with the agent.
- **Tracing** -- [Phoenix](https://github.com/Arize-ai/phoenix) and [LangSmith](https://smith.langchain.com/) (optional) for inspecting agent behavior.
- **Evaluation harness** -- Built-in eval configs for measuring agent quality.

## Software Components

| Component | Purpose |
|-----------|---------|
| [NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/) | Agent framework and serving |
| [NVIDIA cuOpt](https://developer.nvidia.com/cuopt) | GPU-accelerated LP/MILP solver |
| [LangChain Deep Agents](https://www.langchain.com/) | Multi-step agent workflow |
| [minimaxai/minimax-m3](https://build.nvidia.com/) (via NIM) | LLM for agent reasoning |
| [Phoenix](https://github.com/Arize-ai/phoenix) | OpenTelemetry tracing |
| [LangSmith](https://smith.langchain.com/) (optional) | Agent tracing and observability |
| [NAT UI](external/nat-ui/) | Chat web interface |

## Prerequisites

- NVIDIA GPU with CUDA support
- Docker and Docker Compose (with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html))
- Access to `nvcr.io/nvidia/cuopt/cuopt:26.2.0-cuda12.9-py3.13` base image ([NGC](https://catalog.ngc.nvidia.com/))
- NVIDIA API key from [build.nvidia.com](https://build.nvidia.com/)

**Optional:**

- [LangSmith](https://smith.langchain.com/) API key for agent tracing (uncomment the LangSmith section in the config YAML to enable)

**For local development (without Docker):**

- Python 3.11--3.13
- [uv](https://github.com/astral-sh/uv) package manager
- CUDA toolkit and cuOpt installed locally

**For improved performance:**

The default configuration uses NVIDIA's shared API endpoint (`integrate.api.nvidia.com`), which may experience variable latency under load. For consistent performance, deploy the model on dedicated infrastructure using [NVIDIA NIM](https://docs.nvidia.com/nim/), [NVIDIA Dynamo](https://developer.nvidia.com/dynamo), or another model-serving framework. See the [NAT LLM configuration docs](https://docs.nvidia.com/nemo/agent-toolkit/latest/build-workflows/llms/index.html) for how to update the `llms` section of your config YAML.

## Quick Start

```bash
# 1. Initialize submodules (required for the Chat UI)
git submodule update --init --recursive

# 2. Set up environment variables
cp .env.example .env
# Edit .env and add your NVIDIA_API_KEY

# 3. Build and start all services
docker compose -f deploy/compose/docker-compose.yml build
docker compose -f deploy/compose/docker-compose.yml up -d
```

Then open:

- **Chat UI:** http://localhost:3000
- **Phoenix tracing:** http://localhost:6006

## Try It Out

Sample prompts are included to test the agent end-to-end. They pose supply-chain what-if scenarios against the max-supply planning model.

1. Open the Chat UI at http://localhost:3000.
2. Copy the contents of a sample prompt and paste it into the chat input:
   - [`scenario_0.md`](cuopt_agent/data/max_supply_what_ifs/sample_prompts/scenario_0.md) -- Add opening inventory and compare against the baseline.
   - [`scenario_1.md`](cuopt_agent/data/max_supply_what_ifs/sample_prompts/scenario_1.md) -- Change supply constraints from upper bounds to equality (forced procurement) and analyse the impact.
   - [`scenario_2.md`](cuopt_agent/data/max_supply_what_ifs/sample_prompts/scenario_2.md) -- Introduce a substitute raw material (RM4) via a spot-buy shipment and add substitution logic.
   - [`scenario_3.md`](cuopt_agent/data/max_supply_what_ifs/sample_prompts/scenario_3.md) -- Full problem description with detailed BOM, co-production, and resource constraints.
3. Submit the prompt.

The agent will read the dataset, formulate the LP model, solve it on the GPU, and return results.

## Ways to Run the Agent

### Production (Docker Compose)

The production compose file starts all services automatically with health checks and restart policies.

```bash
# Start all services (agent, UI, Phoenix)
docker compose -f deploy/compose/docker-compose.yml up -d

# Run evaluation (one-shot, then exits)
docker compose -f deploy/compose/docker-compose.yml run --rm cuopt-agent-eval

# View logs
docker compose -f deploy/compose/docker-compose.yml logs -f cuopt-agent

# Stop everything
docker compose -f deploy/compose/docker-compose.yml down
```

The agent starts automatically via `nat serve` and is health-checked at `/health`. The UI waits for the agent to be healthy before starting.

### Development (Docker Compose)

The dev compose file launches an interactive container with the repo source-mounted as a volume. You install dependencies and start the agent manually, so changes to code and skills are reflected immediately.

```bash
# Start the dev environment
docker compose -f deploy/compose/docker-compose.dev.yml up -d

# Shell into the dev container
docker exec -it cuopt-agent-dev bash

# Inside the container (CWD is /app/cuopt_agent):
uv pip install -e . --system

# Start the agent (--host 0.0.0.0 and --port 8000 so the UI container can reach it)
nat serve --config_file configs/config-deepagent.yml --host 0.0.0.0 --port 8000

# Run evaluation (from inside the container)
nat eval --config_file configs/config-deepagent-eval.yml
```

### Local Installation (Advanced)

> **Note:** Docker is the recommended path. Local installation requires cuOpt and CUDA to be available on the host machine, which is non-trivial to set up outside the container.

```bash
# Install the agent package (must be run from the cuopt_agent/ directory)
cd cuopt_agent
uv pip install -e . --system

# Load environment variables
source ../.env

# Start the agent
nat serve --config_file configs/config-deepagent.yml --host 0.0.0.0
```

## Skills

Skills provide structured guidance for the agent. They live in `skills/` at the repo root, organized into two groups: `max-supply` skills ship in this repo; `cuopt` skills come from the [cuopt submodule](https://github.com/NVIDIA/cuopt) (see [Quick Start](#quick-start) for setup).

**This repo (`skills/max-supply/`):**

| Skill | Description |
|-------|-------------|
| [generic-max-supply](skills/max-supply/generic-max-supply/SKILL.md) | Multi-period supply chain planning model (BOM structure, variables, constraints) |
| [cuopt-debugging](skills/max-supply/cuopt-debugging/SKILL.md) | Troubleshooting, diagnostics, and common fixes |

**From cuopt submodule (`skills/cuopt/` -- symlinked from `external/cuopt/skills/`):**

| Skill | Description |
|-------|-------------|
| cuopt-lp-milp-api-python | cuOpt Python API patterns and reference models |
| lp-milp-formulation | LP/MILP formulation guidance and modeling best practices |
| *(and others)* | Additional skills maintained in the upstream cuopt repository |

**Why skills?** Agents can already use docs and references to reach a solution. Skills add rules and structure so that going from problem text to the right math model is more reliable. The cuopt submodule skills (e.g., `cuopt-lp-milp-api-python`) give the agent a direct way to see API usage without searching docs. The debugging skill provides a fast path to common fixes.

**Progressive disclosure:** Skills use a progressive disclosure pattern -- the agent sees only skill names and descriptions in its system prompt. When a user query matches a skill, the agent reads the full `SKILL.md` on demand. This keeps the base context small and focused while still giving the agent access to detailed instructions and reference code when needed.

**Extending to other use cases:** The included `generic-max-supply` skill and data target the supply chain planning scenario. To adapt the agent for a different LP/MILP domain:

1. Add a new skill under `skills/` describing the domain model (variables, constraints, objective). Bundle reference data and scripts inside the skill directory itself (e.g., `skills/my-new-skill/scripts/` and `scripts/data/`), following the `generic-max-supply` pattern. This keeps each skill self-contained.
2. Update the `system_prompt` in the config to orient the agent toward the new domain.
3. Add eval cases under a new eval directory to measure quality on the new problem type.

The general-purpose skills from the cuopt submodule (`cuopt-lp-milp-api-python`, `lp-milp-formulation`, etc.) work across all cuOpt LP/MILP use cases and do not need to be replaced.

## Services

| Service | Port | Description |
|---------|------|-------------|
| cuopt-agent | 8000 | NAT agent backend (FastAPI + Uvicorn) |
| nat-ui | 3000 | Chat web UI |
| phoenix | 6006 | OpenTelemetry tracing dashboard |

The agent backend exposes interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs). To verify the agent is running:

```bash
curl -X GET http://localhost:8000/health -H 'accept: application/json'
```

## Evaluation

Evaluation configs are in `cuopt_agent/configs/`. The eval harness runs the agent against a test dataset and scores the results.

**Production:**

```bash
docker compose -f deploy/compose/docker-compose.yml run --rm cuopt-agent-eval
```

> **Note:** The eval service uses a compose profile. If the command above fails, try adding `--profile eval` before `run`.

**Development (from inside the dev container):**

```bash
nat eval --config_file configs/config-deepagent-eval.yml
```

## For AI Agents

See [AGENTS.md](AGENTS.md) for instructions on how to use these skills.

## Project Structure

```
cuopt-agent/
├── AGENTS.md                         # Instructions for AI agents
├── README.md                         # This file
├── .env.example                      # Environment variable template
├── cuopt_agent/
│   ├── configs/                      # NAT YAML configs (serve + eval)
│   ├── data/
│   │   └── max_supply_what_ifs/
│   │       ├── eval/                 # Eval dataset (CSV + JSON)
│   │       └── sample_prompts/       # Scenario prompts for testing
│   ├── docker/
│   │   ├── Dockerfile                # Production image
│   │   └── Dockerfile.dev            # Development image
│   ├── src/nat_cuopt_agent/
│   │   └── function/
│   │       ├── deepagent_fn.py       # Orchestrator agent
│   │       ├── subagent_factory.py   # Subagent factory
│   │       ├── utils.py              # Shared utilities
│   │       ├── healthcheck_fn.py     # Health check endpoint
│   │       └── register.py           # NAT plugin registration
│   └── pyproject.toml                # Python dependencies
├── deploy/
│   └── compose/
│       ├── docker-compose.yml        # Production compose
│       └── docker-compose.dev.yml    # Development compose
├── skills/                           # Agent skills
│   ├── max-supply/                   # Skills in this repo
│   │   ├── generic-max-supply/       # Supply chain planning skill
│   │   │   ├── SKILL.md
│   │   │   └── scripts/              # Self-contained model and data
│   │   │       ├── model.py
│   │   │       ├── data.py
│   │   │       └── data/             # Sample CSV datasets
│   │   └── cuopt-debugging/          # Troubleshooting and diagnostics
│   │       ├── SKILL.md
│   │       └── resources/
│   └── cuopt -> external/cuopt/skills  # Symlink to cuopt submodule skills
│       ├── cuopt-lp-milp-api-python/ # cuOpt Python API patterns and reference models
│       ├── lp-milp-formulation/      # LP/MILP formulation guidance
│       └── ...                       # Additional upstream skills
└── external/
    ├── cuopt/                        # cuOpt submodule (github.com/NVIDIA/cuopt)
    └── nat-ui/                       # Chat UI (git submodule)
```

## References

- **Documentation:** [cuOpt User Guide](https://docs.nvidia.com/cuopt/user-guide/latest/introduction.html), [API Reference](https://docs.nvidia.com/cuopt/user-guide/latest/api.html)
- **Examples:** [cuopt-examples](https://github.com/NVIDIA/cuopt-examples), [Google Colab notebooks](https://colab.research.google.com/github/nvidia/cuopt-examples/)
- **NeMo Agent Toolkit:** [NAT Documentation](https://docs.nvidia.com/nemo/agent-toolkit/latest/)
- **Support:** [NVIDIA Developer Forums](https://forums.developer.nvidia.com/c/ai-data-science/nvidia-cuopt/514), [GitHub Issues](https://github.com/NVIDIA/cuopt/issues)

## License

This project is licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0). See the license headers in individual source files for details.
