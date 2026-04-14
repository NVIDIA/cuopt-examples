# SPDX-FileCopyrightText: Copyright (c) 2025-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Production container for NeMo Agent Toolkit with cuOpt skills.
# Build context must be repo root (cuopt-agent/).
#
# docker build -f cuopt_agent/docker/Dockerfile -t cuopt-agent .

FROM nvcr.io/nvidia/cuopt/cuopt:26.2.0-cuda12.9-py3.13

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# ---------- dependency install (cached unless pyproject.toml, uv.lock, or src/ changes) ----------
COPY cuopt_agent/pyproject.toml cuopt_agent/uv.lock /app/cuopt_agent/
COPY cuopt_agent/src /app/cuopt_agent/src

# Create venv that inherits system site-packages (cuOpt, numpy, numba, etc. from base image),
# then uv sync reads [tool.uv] overrides and pins to uv.lock — only installing what's missing.
RUN --mount=type=cache,target=/root/.cache/uv \
    cd /app/cuopt_agent && \
    uv venv --system-site-packages && \
    uv sync --frozen

ENV PATH="/app/cuopt_agent/.venv/bin:$PATH"

# ---------- application code ----------
COPY cuopt_agent/configs /app/cuopt_agent/configs
COPY cuopt_agent/data    /app/cuopt_agent/data
COPY skills              /app/skills
COPY external/cuopt/skills /app/external/skills/cuopt
COPY AGENTS.md           /app/AGENTS.md

# CWD must be cuopt_agent/ so config relative paths resolve correctly:
#   ../skills  -> /app/skills       ../AGENTS.md -> /app/AGENTS.md
WORKDIR /app/cuopt_agent

EXPOSE 8000

CMD ["nat", "serve", "--config_file", "/app/cuopt_agent/configs/config-deepagent.yml", "--host", "0.0.0.0", "--port", "8000"]
