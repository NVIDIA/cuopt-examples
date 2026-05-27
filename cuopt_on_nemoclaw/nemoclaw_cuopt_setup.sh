#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
# NemoClaw cuOpt sandbox setup
#
# Subcommands:
#   add [NAME]                 Add cuOpt to a sandbox: policy + install + skill + test.
#   apply-policy [NAME]        Add cuOpt network policy to a running sandbox.
#   install [NAME]             Install cuOpt packages in the sandbox venv and
#                              stamp the activation file (see install-activation).
#                              If a wheel cache exists at $CUOPT_WHEEL_CACHE
#                              matching the package set + sandbox python,
#                              install offline.
#   install-activation [NAME]  Re-stamp the cuOpt venv activation file
#                              (/sandbox/.bash_profile). Use after changing
#                              CUOPT_HOST, CUOPT_PORT, or CUOPT_VENV.
#   install-skill [NAME]       Upload the cuOpt skill into the sandbox.
#   cache-wheels [NAME]        Snapshot a sandbox's already-installed wheels
#                              into $CUOPT_WHEEL_CACHE. NAME must already have
#                              cuOpt installed (run `add` or `install` against
#                              it online once first). Subsequent `install` /
#                              `add` runs against any sandbox reuse the cache
#                              and install offline.
#   clear-wheel-cache          Remove $CUOPT_WHEEL_CACHE.
#   test [NAME]                Smoke-test PyPI + cuOpt server reachability.
#
# Flags:
#   -y, --yes       Skip confirmation prompts (for CI/CD).
#
# Environment:
#   CUOPT_SANDBOX   Sandbox name             (default: cuopt)
#   CUOPT_VENV      Venv directory path under /sandbox/
#                   (default: .openclaw-data/cuopt). The default NemoClaw
#                   filesystem policy only allows writes under
#                   /sandbox/.openclaw-data and /sandbox/.nemoclaw, so the
#                   venv must live under one of those.
#   CUOPT_HOST      cuOpt server hostname    (default: "" = localhost only)
#                   Set to a hostname, IP, or k8s service to allow remote cuOpt.
#                   Localhost entries (host.openshell.internal / host.docker.internal)
#                   are always included. CUOPT_HOST adds an additional endpoint.
#   CUOPT_PORT      cuOpt REST server port   (default: 5000)
#   CUOPT_GRPC_PORT cuOpt gRPC server port   (default: 5001)
#   CUOPT_PYTHON_BIN  Exact path to Python binary in sandbox image
#                   (default: auto-detected from running sandbox, or
#                    /usr/bin/python3.11). Must be exact — no globs.
#   CUOPT_HOST_IP   IP that host.openshell.internal resolves to
#                   (default: auto-detected from running sandbox, or
#                    172.17.0.1). Needed for OpenShell allowed_ips.
#   CUOPT_SKILLS_REPO  GitHub repo to fetch upstream cuOpt skills from
#                      (default: NVIDIA/cuopt).
#   CUOPT_SKILLS_REF   Branch / tag / commit SHA to fetch from CUOPT_SKILLS_REPO
#                      (default: release/26.06 — the cuOpt release line this
#                      script was last verified against; override to `main`
#                      to pull the latest in-progress skills).
#   CUOPT_SKILLS_SKIP  Comma-separated glob patterns matching upstream skill
#                      names to NOT install (default:
#                      cuopt-install,*developer*,*-api-c).
#                      cuopt-install  — host-side install flows; cuOpt is
#                          already installed in the sandbox.
#                      *developer*    — for contributing to the cuOpt
#                          codebase; agents use cuOpt, they don't build it.
#                      *-api-c        — libcuopt is present so the C API
#                          works, but its CSR-matrix inputs are awkward to
#                          build from an agent; the Python API is strictly
#                          easier. Override this to ship them anyway.
#   CUOPT_WHEEL_CACHE  Host directory holding snapshotted cuOpt wheels.
#                      (default: ${XDG_CACHE_HOME:-~/.cache}/cuopt-wheels)
#                      Populated by `cache-wheels` (snapshots from a
#                      sandbox that already has cuOpt installed). `install`
#                      auto-detects the matching subdir and uploads it for
#                      offline install.
#
# Examples:
#   ./nemoclaw_cuopt_setup.sh add cuopt              # Slow first install (online)
#   ./nemoclaw_cuopt_setup.sh cache-wheels cuopt     # Snapshot wheels to host
#   nemoclaw delete cuopt && nemoclaw create cuopt   # Recreate sandbox
#   ./nemoclaw_cuopt_setup.sh add cuopt              # Now installs offline (fast)
#   ./nemoclaw_cuopt_setup.sh apply-policy bob       # Just fix network policy
#   ./nemoclaw_cuopt_setup.sh test cuopt             # Re-run smoke test
#
# Version compatibility:
#   The TESTED_NEMOCLAW_VERSION / TESTED_OPENSHELL_VERSION constants below
#   pin the NemoClaw and OpenShell releases this script was verified
#   against. At startup the script prints a warning banner on stderr if
#   the installed tools differ (non-fatal). To install the exact tested
#   NemoClaw build:
#
#     NEMOCLAW_INSTALL_TAG=v<tested-version> \
#       curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
#
#   Silence the banner with NEMOCLAW_VERSION_CHECK=0.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CUOPT_SANDBOX="${CUOPT_SANDBOX:-cuopt}"
# The default NemoClaw sandbox filesystem policy marks /sandbox as read-only
# and only allows writes under /sandbox/.openclaw-data and /sandbox/.nemoclaw
# (Landlock, best_effort). Putting the venv directly at /sandbox/cuopt fails
# with Permission denied on current sandbox-base images.
CUOPT_VENV="${CUOPT_VENV:-.openclaw-data/cuopt}"
CUOPT_HOST="${CUOPT_HOST:-}"
CUOPT_PORT="${CUOPT_PORT:-5000}"
CUOPT_GRPC_PORT="${CUOPT_GRPC_PORT:-5001}"
CUOPT_PYTHON_BIN="${CUOPT_PYTHON_BIN:-}"
CUOPT_HOST_IP="${CUOPT_HOST_IP:-}"
CUOPT_SKILLS_REPO="${CUOPT_SKILLS_REPO:-NVIDIA/cuopt}"
# Skill set last verified end-to-end with this script. Keep this pinned to
# a release branch, tag, or commit SHA so users get a stable vendoring
# even when upstream main moves. Update deliberately, alongside the
# version banner constants above, when a newer cuOpt skill release is
# verified. Override at runtime with CUOPT_SKILLS_REF=<ref>.
TESTED_CUOPT_SKILLS_REF="release/26.06"
CUOPT_SKILLS_REF="${CUOPT_SKILLS_REF:-${TESTED_CUOPT_SKILLS_REF}}"
CUOPT_SKILLS_SKIP="${CUOPT_SKILLS_SKIP:-cuopt-install,*developer*,*-api-c}"

# ── pip-package set (single source of truth) ─────────────────────
# Pinned packages installed by cmd_install AND fetched by cmd_cache_wheels.
# Edit here once; the cache key incorporates this string's hash so version
# bumps automatically invalidate stale caches.
CUOPT_PIP_PACKAGES="${CUOPT_PIP_PACKAGES:-cuopt-sh-client cuopt-cu13==26.04 grpcio}"
CUOPT_PIP_EXTRA_INDEX="${CUOPT_PIP_EXTRA_INDEX:-https://pypi.nvidia.com}"

# ── wheel cache (host-side, snapshotted from a sandbox) ─────────
# `cache-wheels` snapshots an already-installed sandbox's resolved wheel
# set into this dir, then `install` uploads it back to a fresh sandbox
# for offline pip install. XDG-compliant; safe to rm -rf at any time
# (a cache miss reverts to online install).
#
# We snapshot from a sandbox rather than running `pip download` on the
# host because cuOpt's transitive deps trigger pip resolver backtracking
# through every cuda-toolkit 13.x release (~1 GB of needless downloads).
# Resolution-already-done in the sandbox + `pip download --no-deps -r
# <(pip freeze)` sidesteps that entirely.
CUOPT_WHEEL_CACHE="${CUOPT_WHEEL_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/cuopt-wheels}"
# Sandbox-side staging dir (also serves as the install-time upload target).
# Lives under /sandbox/.openclaw-data because Landlock marks /sandbox itself
# read-only.
CUOPT_SANDBOX_WHEEL_DIR="/sandbox/.openclaw-data/wheels"

FORCE=false

# ── cmd_test status (populated by cmd_test, read by print_service_status_summary) ─
# Tracks what the smoke test observed so cmd_add can show a compact
# post-test summary when something didn't pass. Values:
#   CUOPT_TEST_HOST_REST     "up" | "down"            (is the host process listening?)
#   CUOPT_TEST_HOST_GRPC     "up" | "down"
#   CUOPT_TEST_SANDBOX_REST  "ok" | "unreachable" | "n/a"  ("n/a" when host is down)
#   CUOPT_TEST_SANDBOX_GRPC  "ok" | "unreachable" | "n/a"
# Initial empty value means cmd_test hasn't run yet in this invocation.
CUOPT_TEST_HOST_REST=""
CUOPT_TEST_HOST_GRPC=""
CUOPT_TEST_SANDBOX_REST=""
CUOPT_TEST_SANDBOX_GRPC=""

# ── Tested NemoClaw / OpenShell versions ──────────────────────────
# The versions this script was last verified against. Bumped when we test
# a newer release end-to-end. Used by check_versions() to surface a
# non-fatal warning banner if the installed tools drift ahead.
#
# To install the exact tested NemoClaw build:
#   NEMOCLAW_INSTALL_TAG=v${TESTED_NEMOCLAW_VERSION} \
#     curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
#
# Silence the banner with NEMOCLAW_VERSION_CHECK=0.
TESTED_NEMOCLAW_VERSION="0.0.48"
TESTED_OPENSHELL_VERSION="0.0.39"

# ── NemoClaw / OpenShell version compatibility check ─────────────
# Non-fatal. Prints a warning banner when the installed tool version
# differs from the version this script was tested against, and points the
# user at NEMOCLAW_INSTALL_TAG for pinning. Call once from main().
#
# Parses the first X.Y.Z substring from `<tool> --version` output; tolerant
# of a leading 'v', extra columns, or surrounding text.
check_versions() {
  if [[ "${NEMOCLAW_VERSION_CHECK:-1}" == "0" ]]; then
    return 0
  fi

  local issues=()

  local nc_raw nc_cur
  if command -v nemoclaw >/dev/null 2>&1; then
    nc_raw="$(nemoclaw --version 2>/dev/null || true)"
    nc_cur="$(echo "$nc_raw" | grep -oE 'v?[0-9]+\.[0-9]+\.[0-9]+' | head -1 | sed 's/^v//')"
    if [[ -z "$nc_cur" ]]; then
      issues+=("could not parse nemoclaw version from: ${nc_raw:-<empty>}")
    elif [[ "$nc_cur" != "$TESTED_NEMOCLAW_VERSION" ]]; then
      local newest
      newest="$(printf '%s\n%s\n' "$TESTED_NEMOCLAW_VERSION" "$nc_cur" | sort -V | tail -1)"
      if [[ "$newest" == "$nc_cur" ]]; then
        issues+=("nemoclaw v${nc_cur} is NEWER than tested v${TESTED_NEMOCLAW_VERSION}")
      else
        issues+=("nemoclaw v${nc_cur} is OLDER than tested v${TESTED_NEMOCLAW_VERSION}")
      fi
    fi
  else
    issues+=("nemoclaw not on PATH")
  fi

  local os_raw os_cur
  if command -v openshell >/dev/null 2>&1; then
    os_raw="$(openshell --version 2>/dev/null || true)"
    os_cur="$(echo "$os_raw" | grep -oE 'v?[0-9]+\.[0-9]+\.[0-9]+' | head -1 | sed 's/^v//')"
    if [[ -z "$os_cur" ]]; then
      issues+=("could not parse openshell version from: ${os_raw:-<empty>}")
    elif [[ "$os_cur" != "$TESTED_OPENSHELL_VERSION" ]]; then
      local newest
      newest="$(printf '%s\n%s\n' "$TESTED_OPENSHELL_VERSION" "$os_cur" | sort -V | tail -1)"
      if [[ "$newest" == "$os_cur" ]]; then
        issues+=("openshell v${os_cur} is NEWER than tested v${TESTED_OPENSHELL_VERSION}")
      else
        issues+=("openshell v${os_cur} is OLDER than tested v${TESTED_OPENSHELL_VERSION}")
      fi
    fi
  else
    issues+=("openshell not on PATH")
  fi

  if [[ ${#issues[@]} -eq 0 ]]; then
    return 0
  fi

  # Print a compact banner on stderr so it is visible but does not poison
  # stdout (which some subcommands pipe to `openshell sandbox connect`).
  {
    echo ""
    echo "┌─ NemoClaw/OpenShell version notice ─────────────────────────────────┐"
    for msg in "${issues[@]}"; do
      printf "│  %-67s│\n" "$msg"
    done
    printf "│  %-67s│\n" ""
    printf "│  %-67s│\n" "This script was tested with:"
    printf "│  %-67s│\n" "  nemoclaw  v${TESTED_NEMOCLAW_VERSION}"
    printf "│  %-67s│\n" "  openshell v${TESTED_OPENSHELL_VERSION}"
    printf "│  %-67s│\n" ""
    printf "│  %-67s│\n" "NemoClaw moves quickly; policy schema, gateway container"
    printf "│  %-67s│\n" "name, or sandbox base image may have changed. To pin to the"
    printf "│  %-67s│\n" "tested build:"
    printf "│  %-67s│\n" ""
    printf "│  %-67s│\n" "  NEMOCLAW_INSTALL_TAG=v${TESTED_NEMOCLAW_VERSION} \\"
    printf "│  %-67s│\n" "    curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash"
    printf "│  %-67s│\n" ""
    printf "│  %-67s│\n" "Silence this notice with NEMOCLAW_VERSION_CHECK=0."
    echo "└─────────────────────────────────────────────────────────────────────┘"
    echo ""
  } >&2
}

# ── Sandbox container helpers ─────────────────────────────────────
# Post-2026.05 NemoClaw runs each sandbox as a top-level docker container
# named `openshell-<sandbox>-<uuid>`. The previous architecture nested a
# kubectl-in-the-cluster behind `openshell-cluster-nemoclaw`; that gateway
# container is gone, so the old `docker exec gateway kubectl exec sandbox
# …` paths fail fast with "No such container". We talk to the sandbox
# container directly.
#
# These helpers replace the previous gateway-kubectl plumbing AND avoid
# `openshell sandbox exec`, which hangs intermittently in current builds
# (see earlier diagnostic — bare `openshell sandbox exec --no-tty -- …`
# blocked indefinitely against the same sandbox where `docker exec`
# returns in <1s).
#
# find_sandbox_container <sandbox-name>
#   Prints the container name. Returns:
#     0  match found
#     1  no matching container (sandbox not running)
#     2  docker not available on host

find_sandbox_container() {
  local sandbox="$1"
  if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker not found on host" >&2
    return 2
  fi
  local c
  c=$(docker ps --filter "name=openshell-${sandbox}-" --format '{{.Names}}' | head -1)
  if [[ -z "$c" ]]; then
    echo "error: no running sandbox container matches 'openshell-${sandbox}-*'" >&2
    echo "  docker ps shows:" >&2
    docker ps --format '    {{.Names}}\t{{.Status}}' >&2
    return 1
  fi
  printf '%s\n' "$c"
}

# sandbox_exec <sandbox-name> <cmd> [args…]
#   Run a command inside the sandbox container as the sandbox user. The
#   container's image USER is `sandbox`, but we set -u sandbox explicitly
#   so a future image-USER change can't silently land us as root.
#
#   We also set HOME=/sandbox to match the sandbox user's passwd entry
#   (sandbox:x:998:998::/sandbox:/bin/bash). `docker exec` does NOT
#   re-resolve HOME from passwd when -u changes the user — it keeps
#   whatever HOME the container entrypoint inherited (typically /root).
#   That breaks any tool that uses ~ to locate caches/config: pip looks
#   for its HTTP cache under ~/.cache/pip (warm cache lives at
#   /sandbox/.cache/pip), git looks for ~/.gitconfig, etc. The earlier
#   `kubectl exec` path got the right HOME for free because kubectl
#   honors the pod user's passwd entry.
#
#   Stderr is passed through verbatim — callers that want it quiet
#   should redirect themselves. Returns the inner command's exit code,
#   or whatever find_sandbox_container returned if the container isn't
#   running.
sandbox_exec() {
  local sandbox="$1"; shift
  local container
  container=$(find_sandbox_container "$sandbox") || return $?
  docker exec -u sandbox -e HOME=/sandbox "$container" "$@"
}

# sandbox_exec_root <sandbox-name> <cmd> [args…]
#   Same as sandbox_exec, but as root inside the container. Use only for
#   writes the sandbox user can't perform (e.g. /usr/local/lib/...).
#   HOME is left at the container default (/root), which matches what
#   root would see anywhere else.
sandbox_exec_root() {
  local sandbox="$1"; shift
  local container
  container=$(find_sandbox_container "$sandbox") || return $?
  docker exec -u root "$container" "$@"
}

# upload_wheel_cache <sandbox-name> <host-cache-dir> <sandbox-dest-dir>
#   Copy the CONTENTS of <host-cache-dir> into <sandbox-dest-dir>, flat
#   (no wrapping directory). Replaces `openshell sandbox upload`, which
#   in current builds always preserves the source basename and would
#   land everything one level too deep — pip's --find-links is
#   non-recursive, so the install then errors with "No matching
#   distribution found". The tar-pipe approach gives us byte-exact
#   control of the destination layout. Returns 0 on success, non-zero
#   on any step's failure.
upload_wheel_cache() {
  local sandbox="$1" host_dir="$2" dest_dir="$3"
  if [[ ! -d "$host_dir" ]]; then
    echo "  error: wheel cache source dir does not exist: $host_dir" >&2
    return 1
  fi
  local container
  container=$(find_sandbox_container "$sandbox") || return $?
  # mkdir -p the destination (idempotent; safe even if a prior install
  # already left files there — tar will overwrite same-named entries).
  if ! docker exec -u sandbox -e HOME=/sandbox "$container" \
         mkdir -p "$dest_dir" 2>&1; then
    echo "  error: could not mkdir $dest_dir in sandbox" >&2
    return 1
  fi
  # Tar the *contents* of host_dir (-C ... .) so the destination layout
  # is flat. `-i` (--ignore-zeros) on the receiving end is unnecessary;
  # default tar handles a single stream cleanly.
  if ! tar -C "$host_dir" -cf - . \
       | docker exec -i -u sandbox -e HOME=/sandbox "$container" \
           tar -C "$dest_dir" -xf -; then
    echo "  error: tar-pipe into sandbox failed" >&2
    return 1
  fi
  return 0
}

# ── Locate NemoClaw package root ─────────────────────────────────
find_nemoclaw_root() {
  local bin
  bin="$(command -v nemoclaw 2>/dev/null || true)"
  if [[ -z "$bin" ]]; then
    echo "error: nemoclaw not on PATH" >&2
    return 1
  fi
  local resolved
  resolved="$(readlink -f "$bin")"
  local candidate
  candidate="$(cd "$(dirname "$resolved")/.." && pwd)"
  if [[ -f "$candidate/nemoclaw-blueprint/policies/openclaw-sandbox.yaml" ]]; then
    echo "$candidate"; return 0
  fi
  local npm_root
  npm_root="$(npm root -g 2>/dev/null || true)"
  if [[ -n "$npm_root" && -f "$npm_root/nemoclaw/nemoclaw-blueprint/policies/openclaw-sandbox.yaml" ]]; then
    echo "$npm_root/nemoclaw"; return 0
  fi
  echo "error: could not locate nemoclaw-blueprint/policies/openclaw-sandbox.yaml" >&2
  return 1
}



# ── Pick the Python binary path inside the sandbox ────────────────
# We deliberately use the unversioned /usr/bin/python3 symlink (always
# present across NemoClaw base-image bumps) rather than version-pinning,
# and the policy enumerates python3.10–3.13 so any minor version works.
# Use CUOPT_PYTHON_BIN to override.
detect_python_bin() {
  if [[ -n "$CUOPT_PYTHON_BIN" ]]; then
    echo "$CUOPT_PYTHON_BIN"
    return
  fi
  echo "/usr/bin/python3"
}

# ── Detect the Docker host IP (for allowed_ips in policy) ─────────
# OpenShell requires allowed_ips on hostname-based endpoints so the proxy
# can match outbound connections (to resolved IPs) back to hostname rules.
detect_host_ip() {
  if [[ -n "$CUOPT_HOST_IP" ]]; then
    echo "$CUOPT_HOST_IP"
    return
  fi

  local sandbox="${1:-}"
  if [[ -n "$sandbox" ]]; then
    local ip
    # OpenShell v0.0.36+ wraps connect output with bracketed-paste ANSI
    # escapes (\e[?2004l). Strip them before grepping for an IP.
    ip="$(echo 'getent hosts host.openshell.internal | awk "{print \$1}" && exit' \
          | openshell sandbox connect "$sandbox" 2>/dev/null \
          | sed 's/\x1b\[[?0-9;]*[a-zA-Z]//g' \
          | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
    if [[ -n "$ip" ]]; then
      echo "$ip"
      return
    fi
  fi

  echo >&2 "  (could not detect host IP from sandbox — using default 172.17.0.1;"
  echo >&2 "   set CUOPT_HOST_IP to override)"
  echo "172.17.0.1"
}

# ── Docker bridge discovery (used by firewall check + hint) ──────
# List active bridge interfaces that look like Docker (docker0) or a
# user-defined Docker network (br-<hex>). Empty output is fine.
discover_docker_bridges() {
  ip -o link show type bridge 2>/dev/null \
    | awk -F': ' '{print $2}' \
    | grep -E '^(docker|br-)' || true
}

# ── Firewall check ────────────────────────────────────────────────
# Docker containers need to reach the host on CUOPT_PORT and/or
# CUOPT_GRPC_PORT. If UFW drops that traffic, sandbox connections hang.
# Also detects stale rules for bridges that no longer exist (e.g. after
# nemoclaw destroy / onboard recreates the Docker network).
# Usage: check_firewall [port ...]
#   If ports are given, only check those. Otherwise check both.
# Returns: 0 if no warning needed (or warning printed), 2 if UFW status
#   could not be determined non-interactively (caller may want to print
#   a fallback hint via print_ufw_unknown_hint).
check_firewall() {
  if ! command -v ufw &>/dev/null; then return 0; fi
  # Use sudo -n only. Falling back to plain `ufw status` is pointless: it
  # also requires root and prints "ERROR: You need to be root..." to stderr,
  # which we'd swallow and treat as "all clear" — exactly the silent failure
  # this script saw on hosts where sudo requires a password (#TBD).
  local status
  status="$(sudo -n ufw status 2>/dev/null)"
  if [[ -z "$status" ]]; then
    # Could not query UFW (sudo needs password, ufw refused, etc.). Tell
    # the caller so it can print a more useful hint when paired with
    # actual probe results.
    return 2
  fi
  if ! echo "$status" | grep -q "^Status: active"; then return 0; fi

  # Ports to check for missing rules (only services that are running)
  local ports=("$@")
  if [[ ${#ports[@]} -eq 0 ]]; then
    ports=("${CUOPT_PORT}" "${CUOPT_GRPC_PORT}")
  fi
  # All cuOpt ports — used for stale rule cleanup regardless of what's running
  local all_ports=("${CUOPT_PORT}" "${CUOPT_GRPC_PORT}")

  # Current Docker bridge interfaces on this host
  local -a current_bridges=()
  while IFS= read -r iface; do
    [[ -n "$iface" ]] && current_bridges+=("$iface")
  done < <(discover_docker_bridges)
  if [[ ${#current_bridges[@]} -eq 0 ]]; then return 0; fi

  # Bridge interfaces referenced in UFW rules
  local -a rule_bridges=()
  while IFS= read -r rb; do
    [[ -n "$rb" ]] && rule_bridges+=("$rb")
  done < <(echo "$status" | grep -oE "on (docker0|br-[a-f0-9]+)" \
           | awk '{print $2}' | sort -u)

  # Stale bridges: in UFW rules but not actually present on the host
  local -a stale_bridges=()
  for rb in "${rule_bridges[@]}"; do
    local is_current=false
    for cb in "${current_bridges[@]}"; do
      if [[ "$rb" == "$cb" ]]; then is_current=true; break; fi
    done
    if [[ "$is_current" == false ]]; then
      stale_bridges+=("$rb")
    fi
  done

  # Missing rules: current bridges that lack a rule for one of our ports.
  # UFW format: "5001 on docker0  ALLOW  Anywhere" (interface before ALLOW).
  # A true blanket allow (not scoped to any interface, e.g. "5001  ALLOW  Anywhere")
  # covers all bridges. Interface-scoped rules only apply to that bridge.
  local -a missing_rules=()
  for port in "${ports[@]}"; do
    if echo "$status" | grep -E "^${port} " | grep -v " on " \
       | grep -qE "ALLOW"; then
      continue
    fi
    for cb in "${current_bridges[@]}"; do
      if ! echo "$status" | grep -qE "^${port}.*on ${cb}.*ALLOW"; then
        missing_rules+=("${cb}:${port}")
      fi
    done
  done

  # Count actual stale rules (check all cuOpt ports, not just listening ones)
  local stale_rule_count=0
  for sb in "${stale_bridges[@]}"; do
    for port in "${all_ports[@]}"; do
      if echo "$status" | grep -qE "^${port}.*on ${sb}"; then
        ((stale_rule_count++)) || true
      fi
    done
  done

  # Nothing to report
  if [[ $stale_rule_count -eq 0 && ${#missing_rules[@]} -eq 0 ]]; then
    return 0
  fi

  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  ⚠  FIREWALL WARNING                                          ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"

  if [[ ${#stale_bridges[@]} -gt 0 ]]; then
    local -a stale_cmds=()
    for sb in "${stale_bridges[@]}"; do
      for port in "${all_ports[@]}"; do
        if echo "$status" | grep -qE "^${port}.*on ${sb}"; then
          stale_cmds+=("sudo ufw delete allow in on ${sb} to any port ${port}")
        fi
      done
    done
    if [[ ${#stale_cmds[@]} -gt 0 ]]; then
      echo ""
      echo "  Stale UFW rules found for Docker bridges that no longer"
      echo "  exist (likely from a previous sandbox). Delete them:"
      echo ""
      for cmd in "${stale_cmds[@]}"; do
        echo "    $cmd"
      done
    fi
  fi

  if [[ ${#missing_rules[@]} -gt 0 ]]; then
    echo ""
    echo "  Missing rules — sandbox connections to cuOpt will HANG:"
    echo ""
    for entry in "${missing_rules[@]}"; do
      local iface="${entry%%:*}"
      local port="${entry##*:}"
      echo "    sudo ufw allow in on ${iface} to any port ${port}"
    done
  fi

  echo ""
  echo "  Then retry: $0 test"
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo ""
}

# ── Firewall hint (when UFW status can't be queried) ─────────────
# Called from cmd_test when check_firewall returned 2 (couldn't query
# ufw non-interactively) AND the in-sandbox probe reported one or more
# host-listening ports as unreachable. Prints the exact `sudo ufw allow`
# commands the user would need *if* UFW turns out to be active and
# blocking. Safe to call when UFW is actually inactive — the hint is
# explicitly conditional.
# Usage: print_ufw_unknown_hint <port> [port ...]
print_ufw_unknown_hint() {
  local ports=("$@")
  if [[ ${#ports[@]} -eq 0 ]]; then
    ports=("${CUOPT_PORT}" "${CUOPT_GRPC_PORT}")
  fi

  local -a bridges=()
  while IFS= read -r iface; do
    [[ -n "$iface" ]] && bridges+=("$iface")
  done < <(discover_docker_bridges)

  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  ⚠  FIREWALL HINT (could not query UFW)                       ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  Could not query UFW non-interactively (sudo password required)."
  echo "  Host services are listening but the sandbox could not reach them,"
  echo "  which often means UFW is dropping traffic from the Docker bridge."
  echo ""
  echo "  First, confirm UFW is the cause:"
  echo ""
  echo "    sudo ufw status"
  echo ""
  if [[ ${#bridges[@]} -gt 0 ]]; then
    echo "  If 'Status: active' and no rules cover these ports on the"
    echo "  Docker bridge(s) below, add them:"
    echo ""
    for iface in "${bridges[@]}"; do
      for port in "${ports[@]}"; do
        echo "    sudo ufw allow in on ${iface} to any port ${port}"
      done
    done
    echo ""
    echo "  Then retry: $0 test"
  else
    echo "  (No Docker bridges detected — issue is likely elsewhere.)"
  fi
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo ""
}

# ── Activation banner ─────────────────────────────────────────────
# Short, boxed reminder of how to pick up the venv after
# `nemoclaw connect`. Uses the same boxed style as the firewall warnings
# so it stands out from the install/upload chatter that comes before it.
# Why this exists: NemoClaw seals /sandbox/.bashrc, so cuOpt activation
# lives in /sandbox/.bash_profile — which non-login interactive bash
# (what `nemoclaw connect` spawns) does not source. Users have to take
# one explicit step after connecting.
print_activation_banner() {
  local sandbox="$1"
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  echo "║  cuOpt venv activation                                           ║"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
  echo "  After:"
  echo "      nemoclaw ${sandbox} connect"
  echo ""
  echo "  Run ONE of these inside the sandbox shell to activate the venv,"
  echo "  set CUOPT_SERVER, and define the cuopt_sh alias:"
  echo ""
  echo "      source /sandbox/.bash_profile      # activate the current shell"
  echo "      exec bash -l                       # replace with a login shell"
  echo ""
  echo "  (NemoClaw seals /sandbox/.bashrc, so cuOpt activation lives in"
  echo "  .bash_profile, which non-login interactive shells don't source.)"
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo ""
}

# ── Service status summary (post-test) ────────────────────────────
# Render a compact, boxed summary of what cmd_test observed. Called by
# cmd_add only when cmd_test returned non-zero, so the user sees the
# big picture at the bottom of the scrollback right after the
# activation banner — and doesn't have to scroll up through pip output
# to figure out which leg failed.
#
# Reads the CUOPT_TEST_* globals populated by cmd_test:
#   CUOPT_TEST_HOST_REST     "up" | "down"
#   CUOPT_TEST_HOST_GRPC     "up" | "down"
#   CUOPT_TEST_SANDBOX_REST  "ok" | "unreachable" | "n/a"
#   CUOPT_TEST_SANDBOX_GRPC  "ok" | "unreachable" | "n/a"
print_service_status_summary() {
  local sandbox="$1"
  local test_rc="${2:-1}"
  # Use ASCII hyphen rather than em-dash here: printf "%-64s" measures
  # bytes, but the em-dash is 3 bytes wide / 1 visual column, which would
  # pull the right-hand "║" two columns left of the box border.
  local header
  case "$test_rc" in
    2) header="Service status - NO cuOpt SERVER RUNNING" ;;
    *) header="Service status - TEST FAILED" ;;
  esac
  echo ""
  echo "╔══════════════════════════════════════════════════════════════════╗"
  printf "║  %-64s║\n" "$header"
  echo "╚══════════════════════════════════════════════════════════════════╝"
  echo ""
  printf "  Host process listening    REST: %-12s  gRPC: %-12s\n" \
    "${CUOPT_TEST_HOST_REST:-?}" "${CUOPT_TEST_HOST_GRPC:-?}"
  printf "  Sandbox -> host reach     REST: %-12s  gRPC: %-12s\n" \
    "${CUOPT_TEST_SANDBOX_REST:-?}" "${CUOPT_TEST_SANDBOX_GRPC:-?}"
  echo ""

  if [[ "$test_rc" -eq 2 ]]; then
    echo "  No cuOpt service is listening on the host. Start one, then retry:"
    echo "      ./nemoclaw_cuopt_setup.sh test ${sandbox}"
    echo "  See cuopt-examples/cuopt_on_nemoclaw/SETUP.md > Starting the"
    echo "  cuOpt server for the supported launch commands."
  else
    echo "  Common causes for 'unreachable' on a listening service:"
    echo "    - UFW blocks the docker bridge -> host (see firewall hints above)"
    echo "    - cuOpt server bound to 127.0.0.1 only, not 0.0.0.0"
    echo "    - Sandbox network policy missing the port"
    echo "      (re-apply with: ./nemoclaw_cuopt_setup.sh apply-policy ${sandbox})"
    echo ""
    echo "  Retry after fixing:"
    echo "      ./nemoclaw_cuopt_setup.sh test ${sandbox}"
  fi
  echo ""
  echo "══════════════════════════════════════════════════════════════════════"
  echo ""
}

# ── Python binary enumeration for policy ─────────────────────────
# OpenShell enforces literal binary path matching, so we enumerate every
# Python interpreter the sandbox might end up using: the unversioned
# /usr/bin/python3 symlink, every supported minor version (3.10–3.13),
# the same set inside the venv created by `add`, and pip front-ends.
# That way a NemoClaw base-image bump from python3.11 → python3.13 (or
# similar) doesn't silently 403 every pip request from the venv.
python_binaries_block() {
  local indent="${1:-      }"
  local venv="/sandbox/${CUOPT_VENV}"
  local p
  for p in /usr/bin/python3 \
           /usr/bin/python3.10 /usr/bin/python3.11 \
           /usr/bin/python3.12 /usr/bin/python3.13 \
           "${venv}/bin/python3" \
           "${venv}/bin/python3.10" "${venv}/bin/python3.11" \
           "${venv}/bin/python3.12" "${venv}/bin/python3.13" \
           "${venv}/bin/pip" "${venv}/bin/pip3" \
           /usr/bin/pip /usr/bin/pip3; do
    printf '%s- { path: %s }\n' "$indent" "$p"
  done
}

# ── Policy entry generation (used by apply-policy) ───────────────
# Hostname endpoints require allowed_ips so the proxy can match resolved IPs.
generate_policy_entries() {
  local sandbox="${1:-}"
  local python_bin
  python_bin="$(detect_python_bin "$sandbox")"
  echo "  Using Python binary: $python_bin" >&2

  local host_ip
  host_ip="$(detect_host_ip "$sandbox")"
  echo "  Docker host IP: $host_ip" >&2

  local remote_endpoint=""
  if [[ -n "$CUOPT_HOST" ]]; then
    remote_endpoint="
      - host: ${CUOPT_HOST}
        port: ${CUOPT_PORT}
      - host: ${CUOPT_HOST}
        port: ${CUOPT_GRPC_PORT}"
  fi

  local pybins
  pybins="$(python_binaries_block)"

  cat <<YAML

  # ── cuOpt: PyPI + NVIDIA PyPI + cuOpt server (nvidia-cuopt cuopt_claw) ──
  # Hostname endpoints need allowed_ips for the proxy to match resolved IPs.
  # Binary lists enumerate every Python the sandbox might use (system +
  # venv at /sandbox/${CUOPT_VENV}/bin) so pip works from any of them.
  pypi_public:
    name: pypi-public
    endpoints:
      - host: pypi.org
        port: 443
      - host: files.pythonhosted.org
        port: 443
    binaries:
${pybins}

  nvidia_pypi:
    name: nvidia-pypi
    endpoints:
      - host: pypi.nvidia.com
        port: 443
    binaries:
${pybins}

  cuopt_host:
    name: cuopt-host
    endpoints:
      - host: host.openshell.internal
        port: ${CUOPT_PORT}
        allowed_ips:
          - ${host_ip}
      - host: host.openshell.internal
        port: ${CUOPT_GRPC_PORT}
        allowed_ips:
          - ${host_ip}
      - host: host.docker.internal
        port: ${CUOPT_PORT}
        allowed_ips:
          - ${host_ip}
      - host: host.docker.internal
        port: ${CUOPT_GRPC_PORT}
        allowed_ips:
          - ${host_ip}${remote_endpoint}
    binaries:
${pybins}
      - { path: /usr/bin/curl }
YAML
}


# ── apply-policy ──────────────────────────────────────────────────
cmd_apply_policy() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  echo "Applying cuOpt network policy to running sandbox '$sandbox' ..."

  local current
  current="$(openshell policy get --full "$sandbox" 2>/dev/null || true)"
  if [[ -z "$current" ]]; then
    echo "error: could not read policy for sandbox '$sandbox'." >&2
    echo "  Is the sandbox running? Check with: openshell sandbox list" >&2
    exit 1
  fi

  # openshell policy get --full may include metadata fields (e.g. "Version")
  # that openshell policy set rejects. Strip any top-level keys that aren't
  # in the accepted schema.
  current="$(python3 "$SCRIPT_DIR/utils/strip_policy_metadata.py" <<< "$current")"

  local entries
  entries="$(generate_policy_entries "$sandbox")"
  if [[ -n "$CUOPT_HOST" ]]; then
    echo "Remote cuOpt endpoint: ${CUOPT_HOST}:${CUOPT_PORT}"
  fi

  # Merge entries into the network_policies section of the current policy.
  # openshell policy set replaces the full policy, so we must read-merge-write.
  # If our entries already exist, strip them first so they get re-added with
  # freshly detected values (Python binary, host IP).
  local merged
  merged="$(python3 "$SCRIPT_DIR/utils/merge_policy_entries.py" --entries "$entries" <<< "$current")"

  local tmpfile
  tmpfile="$(mktemp /tmp/cuopt-policy-XXXXXX.yaml)"
  echo "$merged" > "$tmpfile"

  openshell policy set --policy "$tmpfile" --wait "$sandbox"
  rm -f "$tmpfile"
  echo "Policy applied to sandbox '$sandbox'."
}


# ── wheel cache helpers ───────────────────────────────────────────
# Cache subdir = sha256(package set) so version bumps invalidate the
# cache. We don't include a platform tag because the snapshotted wheels
# are tagged for whatever the sandbox's actual python is — pip honors
# those tags at install time without us second-guessing.
wheel_cache_subdir() {
  local h
  h="$(printf '%s' "$CUOPT_PIP_PACKAGES" | sha256sum | head -c 12)"
  printf '%s' "$h"
}

wheel_cache_dir() {
  printf '%s/%s' "$CUOPT_WHEEL_CACHE" "$(wheel_cache_subdir)"
}

# True iff $cache has at least one .whl file. Treats empty / missing dir
# as miss so we never try to install from a half-populated cache.
wheel_cache_present() {
  local d="$(wheel_cache_dir)"
  [[ -d "$d" ]] && compgen -G "$d/*.whl" > /dev/null
}

# ── cache-wheels ──────────────────────────────────────────────────
# Snapshot a sandbox's already-installed cuOpt wheels into the host cache.
# Requires the sandbox to have CUOPT_PIP_PACKAGES installed in its venv
# (i.e. you've already run `add` or `install` against it once, online).
# Subsequent fresh sandboxes will reuse this cache and install offline.
#
# Implementation note: we exec directly into the sandbox container via
# `docker exec -u sandbox` (see find_sandbox_container / sandbox_exec
# helpers near the top of this file) instead of `openshell sandbox exec`
# / `download`, because the latter hang in current nemoclaw builds while
# the docker-exec path returns in <1s. Tar-piped extraction sidesteps
# `kubectl cp` and `openshell sandbox download` (both silently misbehave
# in current builds — kubectl cp no-ops when called via docker exec, and
# openshell download has the same hang as exec).
cmd_cache_wheels() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local cache_dir; cache_dir="$(wheel_cache_dir)"
  local sandbox_venv="/sandbox/${CUOPT_VENV}"
  local sandbox_stage="/sandbox/.openclaw-data/wheels-snapshot"

  # Find the container once and close over it — saves a `docker ps` on
  # every invocation and fails fast if the sandbox isn't running.
  local container
  container=$(find_sandbox_container "$sandbox") || exit 2

  # Local helper: run a command inside the sandbox container as the
  # sandbox user. Mirrors the shared sandbox_exec helper, including the
  # HOME=/sandbox fix-up. Without HOME=/sandbox, pip's cache lookup
  # resolves ~/.cache/pip to the container default /root/.cache/pip
  # (root-owned, unwritable from the sandbox user), so the cache
  # silently disables and `pip download` re-fetches everything from
  # PyPI — ~30 min instead of seconds.
  _sb_exec() {
    docker exec -u sandbox -e HOME=/sandbox "$container" "$@"
  }

  echo "Snapshotting cuOpt wheels from sandbox '$sandbox':"
  echo "  venv : $sandbox_venv"
  echo "  cache: $cache_dir"

  # 1. Verify sandbox venv has cuopt installed. Cheap (<1s).
  if ! _sb_exec "$sandbox_venv/bin/python" -c \
         "import cuopt_sh_client" >/dev/null 2>&1; then
    cat >&2 <<EOF
error: sandbox '$sandbox' does not have a working cuOpt venv at
       $sandbox_venv. Run './nemoclaw_cuopt_setup.sh install $sandbox'
       (or 'add $sandbox') first to do the slow online install once;
       then 'cache-wheels' will snapshot the resolved wheels for
       offline reuse.
EOF
    exit 2
  fi

  # 2. In the sandbox: freeze + pip download --no-deps. With exact-version
  #    pins and --no-deps, pip does zero resolution; wheels come from
  #    pip's HTTP cache (already populated during the prior install, so
  #    this step usually uses no network).
  echo "  Step 1/3: freezing sandbox venv and downloading exact-version wheels ..."
  # _sb_exec already runs as the sandbox user (-u sandbox on docker exec).
  # This matters because the original install populated pip's HTTP cache at
  # /tmp/.cache/pip owned by uid 998 — running as root would see a
  # non-writable cache, pip would "disable" it, and we'd re-download
  # everything from PyPI (~30 min on slow links). It also avoids pip's
  # cache-disabled save_linked_requirement code path, which occasionally
  # hits FileNotFoundError on the final copy.
  local inner_script
  inner_script=$(cat <<INNER
set -e
rm -rf '$sandbox_stage'
mkdir -p '$sandbox_stage'
'$sandbox_venv/bin/pip' freeze \\
  | grep -viE '^(pip|setuptools|wheel)==' \\
  > '$sandbox_stage/requirements.txt'
n_pkgs=\$(wc -l < '$sandbox_stage/requirements.txt')
echo "    frozen \$n_pkgs packages"
'$sandbox_venv/bin/pip' download \\
  --no-deps \\
  --dest '$sandbox_stage' \\
  --extra-index-url='$CUOPT_PIP_EXTRA_INDEX' \\
  --requirement '$sandbox_stage/requirements.txt' \\
  --quiet
n_whl=\$(ls -1 '$sandbox_stage'/*.whl 2>/dev/null | wc -l)
sz=\$(du -sh '$sandbox_stage' 2>/dev/null | cut -f1)
echo "    downloaded \$n_whl wheels (\$sz) to $sandbox_stage"
INNER
  )
  if ! _sb_exec bash -c "$inner_script"; then
    echo "" >&2
    echo "error: in-sandbox pip download failed. Stage dir: $sandbox_stage" >&2
    exit 1
  fi

  # 3. Tar-pipe out to host cache. `openshell sandbox download` hangs in
  #    current builds, and tarring through docker exec keeps the snapshot
  #    atomic (no intermediate kubectl/openshell layer to lose bytes).
  echo "  Step 2/3: tar-piping snapshot to host cache ..."
  rm -rf "$cache_dir"
  mkdir -p "$cache_dir"
  local stage_parent stage_name
  stage_parent="$(dirname "$sandbox_stage")"
  stage_name="$(basename "$sandbox_stage")"
  if ! _sb_exec tar -C "$stage_parent" -cf - "$stage_name" \
       | tar -C "$cache_dir" -xf - --strip-components=1; then
    echo "" >&2
    echo "error: tar-pipe extract failed. cache_dir=$cache_dir" >&2
    exit 1
  fi

  echo "  Step 3/3: verifying ..."
  local n; n="$(ls -1 "$cache_dir"/*.whl 2>/dev/null | wc -l)"
  local sz; sz="$(du -sh "$cache_dir" 2>/dev/null | cut -f1)"
  if [[ "$n" -lt 5 ]]; then
    echo "" >&2
    echo "error: only $n wheels in $cache_dir; expected >=5 (cuopt-cu13 alone" >&2
    echo "       has many transitive wheels). Snapshot looks incomplete." >&2
    exit 1
  fi

  # Best-effort: clean up the sandbox-side stage dir so we don't leave
  # ~1 GB of wheels lingering in the agent's writable filesystem.
  _sb_exec rm -rf "$sandbox_stage" >/dev/null 2>&1 || true

  echo ""
  echo "Cached $n wheels ($sz) in $cache_dir"
  echo "Subsequent './nemoclaw_cuopt_setup.sh install' / 'add' will install offline."
}

# ── clear-wheel-cache ─────────────────────────────────────────────
cmd_clear_wheel_cache() {
  if [[ -d "$CUOPT_WHEEL_CACHE" ]]; then
    local sz; sz="$(du -sh "$CUOPT_WHEEL_CACHE" 2>/dev/null | cut -f1)"
    rm -rf "$CUOPT_WHEEL_CACHE"
    echo "Removed $CUOPT_WHEEL_CACHE ($sz)"
  else
    echo "No wheel cache at $CUOPT_WHEEL_CACHE"
  fi
}

# ── install ───────────────────────────────────────────────────────
cmd_install() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local venv="/sandbox/${CUOPT_VENV}"
  echo "Installing cuopt_sh_client in ${venv} venv (sandbox: $sandbox) ..."

  # We use the unversioned /usr/bin/python3 symlink (or CUOPT_PYTHON_BIN
  # override) and the policy enumerates every minor version, so no
  # version-mismatch check is needed here. The pip output below will show
  # exactly which wheel + Python version got resolved.
  local actual_python
  actual_python="$(detect_python_bin "$sandbox")"
  echo "Sandbox Python binary: $actual_python"

  # Build the venv with the explicit interpreter path so it stays consistent
  # across base-image bumps. After activation we use bare `python3` / `pip`
  # so they resolve to the venv shims (otherwise we'd shadow the venv with
  # the system interpreter).
  #
  # We install cuopt-cu13 even though execution is remote: the agent builds
  # problems with the cuopt Python API, which has to import cuopt.* — those
  # imports require the package to be installed locally. The CUOPT_SERVER
  # env var (written by install_activation into .bash_profile) routes
  # the actual solve to the remote server, so CUDA never gets loaded in the
  # sandbox. cu13 is
  # used because the host driver is CUDA 13.x; switch to cuopt-cu12 by
  # editing this line if your host driver is CUDA 12.x.

  # Decide online vs offline-from-cache. The cache is keyed by the
  # CUOPT_PIP_PACKAGES hash, so editing the package set automatically
  # invalidates the cache and we never silently install an out-of-date
  # set. (Wheel platform tags are baked into the snapshotted .whl
  # filenames; pip honors them at install time.)
  local pip_install_line
  if wheel_cache_present; then
    local cache_dir; cache_dir="$(wheel_cache_dir)"
    local n; n="$(ls -1 "$cache_dir"/*.whl 2>/dev/null | wc -l)"
    echo "  Wheel cache hit ($n wheels in $cache_dir); uploading and installing offline."
    # Why tar-pipe via docker exec instead of `openshell sandbox upload`?
    # Current openshell upload semantics preserve the source directory
    # name: `upload <host>/cache/<hash>/ <sandbox>/wheels` lands the
    # wheels at <sandbox>/wheels/<hash>/*.whl (one level too deep), and
    # pip's --find-links is non-recursive so the install fails with
    # "No matching distribution". Same gotcha that hit the skill upload
    # path. A tar-pipe gives us byte-level control of the layout: we
    # land the .whl files flat under $CUOPT_SANDBOX_WHEEL_DIR/ so the
    # existing --find-links path keeps working unchanged.
    if ! upload_wheel_cache "$sandbox" "$cache_dir" "$CUOPT_SANDBOX_WHEEL_DIR"; then
      echo "  warning: wheel cache upload failed; falling back to online install" >&2
      pip_install_line="pip install $CUOPT_PIP_PACKAGES --extra-index-url=$CUOPT_PIP_EXTRA_INDEX"
    else
      pip_install_line="pip install --no-index --find-links=$CUOPT_SANDBOX_WHEEL_DIR $CUOPT_PIP_PACKAGES"
    fi
  else
    echo "  No wheel cache at $(wheel_cache_dir); installing online from PyPI."
    echo "  (Run './nemoclaw_cuopt_setup.sh cache-wheels' once to make subsequent installs fast.)"
    pip_install_line="pip install $CUOPT_PIP_PACKAGES --extra-index-url=$CUOPT_PIP_EXTRA_INDEX"
  fi

  local commands=(
    "${actual_python} -m venv ${venv}"
    "source ${venv}/bin/activate"
    "python3 -V"
    "${pip_install_line}"
    "python3 -c \"import cuopt_sh_client; print('cuopt_sh_client', cuopt_sh_client.__version__)\""
    "exit"
  )

  printf '%s\n' "${commands[@]}" | openshell sandbox connect "$sandbox"

  local cuopt_ip="host.openshell.internal"
  [[ -n "$CUOPT_HOST" ]] && cuopt_ip="$CUOPT_HOST"

  if install_activation "$sandbox" "$cuopt_ip" "$CUOPT_PORT"; then
    echo "Install complete."
  else
    cat <<EOF
Install complete, but auto-activation could NOT be installed in
/sandbox/.bash_profile (see warning above). Activate manually per session:

    nemoclaw connect ${sandbox}
    source ${venv}/bin/activate
    export CUOPT_SERVER=${cuopt_ip}:${CUOPT_PORT}
EOF
  fi
}

# ── install-activation ────────────────────────────────────────────
# Re-stamp /sandbox/.bash_profile with the current CUOPT_VENV / CUOPT_HOST /
# CUOPT_PORT values without touching the venv. Useful after changing the
# cuOpt server.
cmd_install_activation() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local cuopt_ip="host.openshell.internal"
  [[ -n "$CUOPT_HOST" ]] && cuopt_ip="$CUOPT_HOST"
  if install_activation "$sandbox" "$cuopt_ip" "$CUOPT_PORT"; then
    print_activation_banner "$sandbox"
  fi
}

# ── install_activation (helper) ───────────────────────────────────
# Drop a managed auto-activation block into /sandbox/.bash_profile by
# `docker exec`ing directly into the sandbox container.
#
# Why .bash_profile and not .bashrc?
#   NemoClaw bakes /sandbox/.bashrc and /sandbox/.profile as root-owned mode
#   444 (see nemoclaw Dockerfile.base lines 136-145, "Ref: #2181 — the file
#   must not be writable by the sandbox user") AND enforces the same lock
#   under Landlock (see e2e-cloud-experimental/checks/04-landlock-readonly.sh
#   check 2, which asserts BASHRC_BLOCKED). Even root processes can't write
#   to .bashrc/.profile at runtime. Bash's startup-file search order means
#   /sandbox/.bash_profile, when it exists, wins over /sandbox/.profile for
#   login shells (bash -l, bash -lc). Non-login interactive bash (what
#   `openshell sandbox connect` / `nemoclaw connect` spawn) and non-login
#   non-interactive bash (`bash -c '…'`) do NOT source .bash_profile — the
#   user / agent must run `source /sandbox/.bash_profile`, `exec bash -l`,
#   or `bash -lc '…'` to get the venv. The sandbox SKILL.md spells this out
#   for the agent.
#
# /sandbox itself is writable (Landlock check 1) for new files, so creating
# .bash_profile works as the sandbox user. We don't need root, and we don't
# need to chmod anything.
#
# Why docker exec and not the old `docker exec gateway kubectl exec sandbox`
# path?
#   Latest NemoClaw (post-2026.05) no longer ships an
#   `openshell-cluster-nemoclaw` gateway container; the sandbox pod runs
#   directly as a top-level docker container named `openshell-<sandbox>-
#   <uuid>`. The old gateway-kubectl path fails fast ("No such container"),
#   silently swallowed by the previous helper, leaving the user with a
#   surprising "auto-activation could not be installed" warning. We now
#   find the container by name pattern and exec into it as the sandbox
#   user. If a future NemoClaw revives the gateway architecture, gate the
#   container lookup on a fallback chain.
#
# The block is delimited by stable begin/end markers so re-stamping is exact
# (no fragile partial-line matching).
#
# Returns 0 on success, 1 if docker/container is unavailable or the inner
# write fails.
install_activation() {
  local sandbox="$1"
  local cuopt_ip="$2"
  local cuopt_port="$3"
  local venv="/sandbox/${CUOPT_VENV}"

  local container
  if ! container=$(find_sandbox_container "$sandbox"); then
    echo "  warning: cannot install /sandbox/.bash_profile (sandbox container not running)" >&2
    return 1
  fi

  # The inner script runs inside the sandbox container as the sandbox user
  # via sandbox_exec. Base64 over the whole payload so we don't have to
  # fight three layers of shell quoting (bash here-doc -> docker exec ->
  # sh -c). Variables we want expanded NOW (outer bash): ${venv},
  # ${cuopt_ip}, ${cuopt_port}. Variables we want expanded by the inner
  # sh: escaped with \$.
  local inner_script
  inner_script=$(cat <<INNER_EOF
set -eu
profile=/sandbox/.bash_profile
begin='# >>> cuopt activation (managed by nemoclaw_cuopt_setup.sh) >>>'
end='# <<< cuopt activation <<<'

# First-time setup: create .bash_profile that re-sources the NemoClaw-sealed
# .profile (so the runtime proxy env hook still fires for login shells, just
# like it would have if .bash_profile didn't exist and bash had fallen back
# to .profile). On subsequent runs we leave the existing header alone and
# only re-stamp the managed block.
if [ ! -f "\$profile" ]; then
  cat > "\$profile" <<HEAD_EOF
# Login shell init for the sandbox user. NemoClaw seals /sandbox/.bashrc
# and /sandbox/.profile, so cuOpt auto-activation lives here instead.
# Managed by nemoclaw_cuopt_setup.sh — see cuopt-examples/cuopt_on_nemoclaw.
[ -f /sandbox/.profile ] && . /sandbox/.profile
HEAD_EOF
fi

# Idempotent re-stamp: strip any previous block between the markers.
if grep -qF "\$begin" "\$profile" 2>/dev/null; then
  b=\$(grep -nF "\$begin" "\$profile" | head -1 | cut -d: -f1)
  e=\$(grep -nF "\$end"   "\$profile" | head -1 | cut -d: -f1)
  if [ -n "\$b" ] && [ -n "\$e" ] && [ "\$e" -ge "\$b" ]; then
    sed -i "\${b},\${e}d" "\$profile"
  fi
fi

cat >> "\$profile" <<BASHPROFILE_EOF
\$begin
if [ -f ${venv}/bin/activate ]; then
  . ${venv}/bin/activate
  export CUOPT_SERVER=${cuopt_ip}:${cuopt_port}
  alias cuopt_sh='cuopt_sh -i ${cuopt_ip} -p ${cuopt_port}'
fi
\$end
BASHPROFILE_EOF
INNER_EOF
)

  local inner_b64
  inner_b64=$(printf '%s' "$inner_script" | base64 -w 0)

  # Capture stderr so a failed inner write produces a useful diagnostic
  # instead of a silent retry-warn loop. Don't swallow it the way the
  # previous helper did.
  local err_log
  err_log=$(mktemp)
  if sandbox_exec "$sandbox" \
       sh -c "echo '$inner_b64' | base64 -d | sh" >/dev/null 2>"$err_log"; then
    rm -f "$err_log"
    echo "  Installed cuOpt auto-activation in /sandbox/.bash_profile"
    return 0
  fi

  echo "  warning: could not write /sandbox/.bash_profile in container '$container'" >&2
  if [[ -s "$err_log" ]]; then
    echo "  stderr from the inner write:" >&2
    sed 's/^/    /' "$err_log" >&2
  fi
  rm -f "$err_log"
  return 1
}

# ── test ──────────────────────────────────────────────────────────
cmd_test() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local venv="/sandbox/${CUOPT_VENV}"
  local grpc_host="host.openshell.internal"
  local cuopt_url="http://host.openshell.internal:${CUOPT_PORT}"
  if [[ -n "$CUOPT_HOST" ]]; then
    grpc_host="${CUOPT_HOST}"
    local scheme="http"
    [[ "$CUOPT_PORT" == "443" ]] && scheme="https"
    cuopt_url="${scheme}://${CUOPT_HOST}:${CUOPT_PORT}"
  fi
  # Check what's actually listening on the host before bothering the sandbox
  local has_grpc=false has_rest=false
  if ss -tlnH "sport = :${CUOPT_GRPC_PORT}" 2>/dev/null | grep -q .; then
    has_grpc=true
  fi
  if ss -tlnH "sport = :${CUOPT_PORT}" 2>/dev/null | grep -q .; then
    has_rest=true
  fi

  # Record status for the post-test summary (read by print_service_status_summary).
  CUOPT_TEST_HOST_REST=$([[ "$has_rest" == true ]] && echo "up" || echo "down")
  CUOPT_TEST_HOST_GRPC=$([[ "$has_grpc" == true ]] && echo "up" || echo "down")
  CUOPT_TEST_SANDBOX_REST="n/a"
  CUOPT_TEST_SANDBOX_GRPC="n/a"

  if [[ "$has_grpc" == false && "$has_rest" == false ]]; then
    echo ""
    echo "No cuOpt server detected on the host."
    echo "  - Nothing listening on port ${CUOPT_PORT} (REST)"
    echo "  - Nothing listening on port ${CUOPT_GRPC_PORT} (gRPC)"
    echo "  Start a cuOpt server first, then re-run: $0 test ${sandbox}"
    echo ""
    return 2
  fi

  echo "Host services: REST=$(if $has_rest; then echo UP; else echo DOWN; fi)  gRPC=$(if $has_grpc; then echo UP; else echo DOWN; fi)"
  echo "Smoke-testing sandbox: $sandbox (venv: $venv) ..."

  # probe_cuopt.py reports REST and gRPC reachability in one call. We pass
  # CUOPT_SERVER_HOST/PORT (REST) and CUOPT_REMOTE_HOST/PORT (gRPC) so the
  # probe checks the same endpoints we just verified are listening on the
  # host. The probe's exit code is non-zero only when *both* are unreachable
  # from inside the sandbox — `|| true` prevents that from breaking the
  # heredoc's overall exit status.
  local sandbox_cmds="
source ${venv}/bin/activate
echo '--- pip check ---'
python3 -c \"import cuopt_sh_client; print('cuopt_sh_client', cuopt_sh_client.__version__)\"

echo ''
echo '--- cuOpt endpoint probe (REST=${cuopt_url}, gRPC=${grpc_host}:${CUOPT_GRPC_PORT}) ---'
CUOPT_SERVER_HOST=${grpc_host} CUOPT_SERVER_PORT=${CUOPT_PORT} \\
CUOPT_REMOTE_HOST=${grpc_host} CUOPT_REMOTE_PORT=${CUOPT_GRPC_PORT} \\
python3 /sandbox/probe_cuopt.py || true

echo ''
exit
"
  # Capture the sandbox output so we can both display it AND parse it for
  # reachability ('unreachable' literal from probe_cuopt.py). `tee` keeps
  # the live UX intact; mktemp avoids clobbering anything else in /tmp.
  local probe_log
  probe_log="$(mktemp /tmp/cuopt-probe-XXXXXX.log)"
  echo "$sandbox_cmds" | openshell sandbox connect "$sandbox" 2>&1 \
    | tee "$probe_log"
  echo "Test complete."

  # Detect probe failures per service. Only treat as a failure if the
  # service was actually listening on the host — there's no point hinting
  # about a port we never expected to be reachable.
  local rest_unreachable=false grpc_unreachable=false
  if [[ "$has_rest" == true ]]; then
    if grep -qE '^rest:[[:space:]]+unreachable' "$probe_log"; then
      rest_unreachable=true
      CUOPT_TEST_SANDBOX_REST="unreachable"
    else
      CUOPT_TEST_SANDBOX_REST="ok"
    fi
  fi
  if [[ "$has_grpc" == true ]]; then
    if grep -qE '^grpc:[[:space:]]+unreachable' "$probe_log"; then
      grpc_unreachable=true
      CUOPT_TEST_SANDBOX_GRPC="unreachable"
    else
      CUOPT_TEST_SANDBOX_GRPC="ok"
    fi
  fi
  rm -f "$probe_log"

  # Only warn about firewall for ports that are actually listening
  local check_ports=()
  [[ "$has_rest" == true ]] && check_ports+=("${CUOPT_PORT}")
  [[ "$has_grpc" == true ]] && check_ports+=("${CUOPT_GRPC_PORT}")
  local check_rc=0
  check_firewall "${check_ports[@]}" || check_rc=$?

  # check_firewall returns 2 when it could not query UFW non-interactively
  # (sudo password required). Pre-fix, this silently degraded to "all
  # clear" and users hit a real UFW block with no hint. Now: if the probe
  # also showed any host-listening service as unreachable, print the
  # exact `sudo ufw allow ...` commands they would need *if* UFW turns
  # out to be active. If the probe succeeded, just leave a one-liner so
  # the user knows the check was skipped (no false sense of completeness).
  if [[ $check_rc -eq 2 ]]; then
    local -a unreachable_ports=()
    [[ "$rest_unreachable" == true ]] && unreachable_ports+=("${CUOPT_PORT}")
    [[ "$grpc_unreachable" == true ]] && unreachable_ports+=("${CUOPT_GRPC_PORT}")
    if [[ ${#unreachable_ports[@]} -gt 0 ]]; then
      print_ufw_unknown_hint "${unreachable_ports[@]}"
    else
      echo ""
      echo "Note: could not query UFW non-interactively (sudo password required)."
      echo "      Probe succeeded so this is informational; to audit:"
      echo "        sudo ufw status"
      echo ""
    fi
  fi

  # Return 1 if any host-listening service was unreachable from inside the
  # sandbox, 0 otherwise. cmd_add reads this to decide whether to print
  # print_service_status_summary after the activation banner.
  if [[ "$rest_unreachable" == true || "$grpc_unreachable" == true ]]; then
    return 1
  fi
  return 0
}

# ── Upstream skills fetch ─────────────────────────────────────────
# Download the cuOpt repo's `skills/` tree as a tarball and extract it into
# $1 so each subdirectory under skills/ becomes a top-level entry. The agent
# can't reach github.com from inside the sandbox, so we vendor the skills at
# install time. Returns 0 on success, 1 on any fetch/extract failure (caller
# should fall through to local-only installation).
#
# Notes on resilience to upstream layout changes:
#   - We do NOT swallow tar's stderr. If `--wildcards "*/skills/*"` matches
#     nothing (e.g. upstream moved skills out of skills/), tar exits 0 but
#     prints "Not found in archive", which then surfaces to the operator.
#   - The caller (cmd_install_skill) additionally counts SKILL.md entries
#     post-extract and warns explicitly when zero are found, so a quietly
#     empty extract never silently degrades to "local skills only".
fetch_upstream_skills() {
  local dest="$1"
  local repo="${CUOPT_SKILLS_REPO}"
  local ref="${CUOPT_SKILLS_REF}"
  local url="https://github.com/${repo}/archive/${ref}.tar.gz"

  if [[ "$ref" != "$TESTED_CUOPT_SKILLS_REF" ]]; then
    echo "  Note: CUOPT_SKILLS_REF=${ref} differs from tested ref ${TESTED_CUOPT_SKILLS_REF}" >&2
  fi
  echo "  Fetching upstream skills from ${repo}@${ref} ..." >&2
  if ! curl -fsSL "$url" \
       | tar -xz -C "$dest" --strip-components=2 --wildcards "*/skills/*"; then
    echo "  warning: failed to fetch upstream skills from $url" >&2
    return 1
  fi
  return 0
}

# Returns 0 if $1 matches any comma-separated glob in $CUOPT_SKILLS_SKIP.
# Glob is bash extglob-free; '*' and '?' work as expected (e.g. *developer*).
skill_is_skipped() {
  local name="$1"
  local raw="$CUOPT_SKILLS_SKIP"
  [[ -z "$raw" ]] && return 1
  local IFS=','
  local pat
  for pat in $raw; do
    pat="${pat# }"; pat="${pat% }"
    [[ -z "$pat" ]] && continue
    # shellcheck disable=SC2053  # intentional unquoted RHS for glob match
    if [[ "$name" == $pat ]]; then
      return 0
    fi
  done
  return 1
}

# ── install-skill ─────────────────────────────────────────────────
cmd_install_skill() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local skills_dir="$SCRIPT_DIR/openclaw-skills"

  if [[ ! -d "$skills_dir" ]]; then
    echo "error: skills directory not found at $skills_dir" >&2
    exit 1
  fi

  # Track names already uploaded so upstream skills can't override local ones.
  local -a uploaded_names=()
  local name

  # ── upload semantics note ──────────────────────────────────────────
  # In openshell >= 0.0.38, `sandbox upload <SRC_DIR> <DST_DIR>` copies
  # SRC_DIR as a *named subdirectory* of DST_DIR (so DST_DIR/<basename of
  # SRC_DIR> ends up populated). Older openshell versions treated DST as
  # the destination directory itself and copied SRC's *contents* into it.
  #
  # We rely on the new semantics: pass the PARENT path
  # ("/sandbox/.openclaw/skills/") as DST so each skill dir lands at
  # the depth OpenClaw's loader expects: <extraDir>/<name>/SKILL.md.
  # Passing "/sandbox/.openclaw/skills/$name" under new semantics would
  # nest as <extraDir>/<name>/<name>/SKILL.md and the loader would
  # silently skip every skill (see types.skills.d.ts: "Each directory
  # should contain skill subfolders with SKILL.md.").
  echo "Installing skills into sandbox '$sandbox' ..."
  for skill in "$skills_dir"/*/; do
    name="$(basename "$skill")"
    if [[ -f "$skill/SKILL.md" ]]; then
      echo "  Uploading local skill: $name"
      if openshell sandbox upload "$sandbox" "$skill" "/sandbox/.openclaw/skills/" 2>&1; then
        uploaded_names+=("$name")
      else
        echo "  warning: upload failed for skill '$name'" >&2
      fi
    fi
  done

  # Vendor upstream cuOpt skills so the agent doesn't need github.com egress.
  # Local skills (above) take precedence on name collisions; names matched by
  # CUOPT_SKILLS_SKIP are filtered out (host-side install / codebase developer
  # skills don't apply in a pre-installed sandbox).
  local upstream_dir
  upstream_dir="$(mktemp -d /tmp/cuopt-skills-XXXXXX)"
  # Best-effort cleanup; don't trap globally so we don't stomp on other handlers.
  if fetch_upstream_skills "$upstream_dir"; then
    # Collect every upstream skill directory name (those with a SKILL.md)
    # BEFORE we apply the SKIP filter. We use this list for two checks:
    #   1. Detect a zero-skill extract (upstream may have moved skills/).
    #   2. Verify each CUOPT_SKILLS_SKIP pattern matched at least one
    #      pre-filter name (a pattern that matches nothing is almost
    #      always a stale glob from before an upstream rename).
    local -a upstream_names_all=()
    local skill upstream_name was_uploaded
    for skill in "$upstream_dir"/*/; do
      [[ -d "$skill" ]] || continue
      [[ -f "$skill/SKILL.md" ]] || continue
      upstream_names_all+=("$(basename "$skill")")
    done

    if [[ ${#upstream_names_all[@]} -eq 0 ]]; then
      echo "  warning: upstream tarball produced 0 skill directories with SKILL.md" >&2
      echo "           upstream layout may have changed (e.g. skills/ moved)." >&2
      echo "           Repo:${CUOPT_SKILLS_REPO}  Ref:${CUOPT_SKILLS_REF}" >&2
      echo "           Continuing with local skills only." >&2
    fi

    for upstream_name in "${upstream_names_all[@]+"${upstream_names_all[@]}"}"; do
      skill="$upstream_dir/$upstream_name/"

      was_uploaded=false
      for n in "${uploaded_names[@]+"${uploaded_names[@]}"}"; do
        [[ "$n" == "$upstream_name" ]] && { was_uploaded=true; break; }
      done
      if $was_uploaded; then
        echo "  Skipping upstream '$upstream_name' (overridden by local skill)"
        continue
      fi
      if skill_is_skipped "$upstream_name"; then
        echo "  Skipping upstream '$upstream_name' (matches CUOPT_SKILLS_SKIP)"
        continue
      fi

      echo "  Uploading upstream skill: $upstream_name"
      # Parent-dir destination per openshell >= 0.0.38 semantics (see
      # "upload semantics note" above the local-skill upload loop).
      if ! openshell sandbox upload "$sandbox" "$skill" "/sandbox/.openclaw/skills/" 2>&1; then
        echo "  warning: upload failed for upstream skill '$upstream_name'" >&2
      fi
    done

    # Validate SKIP patterns. A glob in CUOPT_SKILLS_SKIP that matches no
    # upstream name almost always means upstream renamed/removed the
    # category the pattern targeted (e.g. when LP/MILP/QP skills were
    # consolidated into a single cuopt-numerical-optimization-api-* set,
    # the prior `*-api-c` pattern still matched but `*installation*`
    # stopped matching anything because installation skills had been
    # merged into a single `cuopt-install`). We surface this so the
    # operator can update the SKIP list rather than silently shipping
    # skills they intended to filter out.
    if [[ -n "$CUOPT_SKILLS_SKIP" && ${#upstream_names_all[@]} -gt 0 ]]; then
      local skip_save_ifs="$IFS"
      IFS=','
      local pat matched n
      for pat in $CUOPT_SKILLS_SKIP; do
        pat="${pat# }"; pat="${pat% }"
        [[ -z "$pat" ]] && continue
        matched=false
        for n in "${upstream_names_all[@]}"; do
          # shellcheck disable=SC2053  # intentional unquoted RHS for glob match
          if [[ "$n" == $pat ]]; then matched=true; break; fi
        done
        if ! $matched; then
          echo "  warning: CUOPT_SKILLS_SKIP pattern '${pat}' matched 0 upstream skills" >&2
          echo "           (upstream may have renamed/removed; review CUOPT_SKILLS_SKIP)" >&2
        fi
      done
      IFS="$skip_save_ifs"
    fi
  fi
  rm -rf "$upstream_dir"

  # The OpenClaw agent compacts paths under $HOME to ~/… in the system prompt.
  # When the agent later tries to read that path, ~ may expand to a different
  # directory (e.g. /root/) depending on the tool executor context.
  #
  # Workaround: install a small "cuopt-setup" guardrail skill into the OpenClaw
  # bundled skills directory. That path is absolute (outside $HOME), so it never
  # gets ~-compacted. The guardrail tells the agent where to find the real skill
  # if the ~-based path fails.
  #
  # Best-effort — if docker isn't available, or the sandbox container
  # isn't running, we skip the bundled-skills write and rely on the
  # absolute-path skill at /sandbox/.openclaw/skills/cuopt-sandbox.
  local bundled_dir="/usr/local/lib/node_modules/openclaw/skills/cuopt-setup"

  local guardrail_content
  guardrail_content="$(cat <<'GUARDRAIL'
---
name: cuopt-setup
description: "Read this FIRST when working with cuOpt. If you cannot read the cuopt-sandbox skill at ~/.openclaw/skills/cuopt-sandbox/SKILL.md, this tells you where the real file lives."
---

# cuOpt sandbox skill — path resolution

The cuopt-sandbox skill (sandbox-specific setup, networking, venv) is
installed at an absolute path that always works:

    /sandbox/.openclaw/skills/cuopt-sandbox/SKILL.md

Read that file FIRST for sandbox-specific cuOpt setup, then consult the
per-task sibling skills it points at (cuopt-user-rules,
cuopt-numerical-optimization-api-python, cuopt-routing-api-python,
numerical-optimization-formulation, etc.) which live in the same
`/sandbox/.openclaw/skills/` directory.

## Why this guardrail exists

OpenClaw compacts skill paths to `~/…` in the system prompt. When you try
to read `~/.openclaw/skills/cuopt-sandbox/SKILL.md`, the `~` may expand to
`/root/` or another directory that is not readable. If that happens:

1. Do NOT give up on using cuOpt.
2. Read the skill from the absolute path above.
3. Also check `/sandbox/.openclaw/skills/cuopt-sandbox/SKILL.md` (symlink
   to the same file).
GUARDRAIL
)"

  local b64
  b64="$(printf '%s' "$guardrail_content" | base64 -w 0)"

  echo "  Installing cuopt-setup guardrail into bundled skills dir ..."
  # /usr/local/lib/... is owned by root, so use the root variant of the
  # exec helper. The guardrail is read-only data, so writing as root is
  # safe and matches how the bundled-skills directory was provisioned by
  # the base image.
  sandbox_exec_root "$sandbox" \
    sh -c "mkdir -p '${bundled_dir}' && echo '${b64}' | base64 -d > '${bundled_dir}/SKILL.md'" \
    2>/dev/null \
  || echo "  warning: could not install cuopt-setup guardrail (non-fatal)" >&2

  # ── register /sandbox/.openclaw/skills/ as a scanned skills root ──
  # OpenClaw 2026.x's skills loader scans a small fixed set of paths
  # (bundled, workspace, plugin-provided) plus any directories listed
  # in skills.load.extraDirs (see plugin-sdk/src/config/types.skills.d.ts:
  # SkillsLoadConfig.extraDirs — "Additional skill folders to scan
  # (lowest precedence). Each directory should contain skill subfolders
  # with SKILL.md."). Without that entry, our uploaded skills are
  # invisible to `openclaw skills list` and the agent's <available_skills>
  # prompt section — even though the files exist on disk.
  #
  # We also set skills.load.watch so the snapshot refreshes when files
  # change. The earlier mechanism (bumping skills.entries.X.config.* to
  # invalidate a per-session snapshot via a gateway config-reload watcher)
  # was tied to an older OpenClaw layout and no longer triggers discovery;
  # the discovery itself now keys off extraDirs membership.
  echo "  Registering /sandbox/.openclaw/skills as an extra skills root ..."
  local invalidator
  invalidator='
import json, os, sys, tempfile
cfg_path = "/sandbox/.openclaw/openclaw.json"
extra_dir = "/sandbox/.openclaw/skills"
try:
    with open(cfg_path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
except Exception as e:
    print("error: cannot read " + cfg_path + ": " + str(e), file=sys.stderr)
    sys.exit(1)
skills = cfg.setdefault("skills", {})
load = skills.setdefault("load", {})
existing = load.get("extraDirs") or []
# Idempotent: dedupe while preserving order, append ours if missing.
if extra_dir not in existing:
    existing = existing + [extra_dir]
load["extraDirs"] = existing
load.setdefault("watch", True)
load.setdefault("watchDebounceMs", 250)
# Drop the obsolete sentinel from the prior mechanism if present so the
# config stays clean. The new loader ignores skills.entries.X.config
# for discovery purposes.
entries = skills.get("entries") or {}
if "cuopt-sandbox" in entries and set(entries["cuopt-sandbox"].keys()) <= {"config"}:
    del entries["cuopt-sandbox"]
    if entries:
        skills["entries"] = entries
    else:
        skills.pop("entries", None)
fd, tmp = tempfile.mkstemp(prefix=".openclaw.", dir=os.path.dirname(cfg_path))
try:
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    os.replace(tmp, cfg_path)
except Exception:
    if os.path.exists(tmp):
        os.unlink(tmp)
    raise
print("    skills.load.extraDirs=" + json.dumps(existing))
'
  local invalidator_b64
  invalidator_b64="$(printf '%s' "$invalidator" | base64 -w 0)"
  # Was: `openshell sandbox exec --no-tty -- bash -c …`, which hangs in
  # current builds. Direct docker exec returns in <1s.
  if ! sandbox_exec "$sandbox" \
        bash -c "echo '${invalidator_b64}' | base64 -d | python3" 2>&1; then
    echo "  warning: failed to update openclaw.json — uploaded skills will not appear" >&2
    echo "           in 'openclaw skills list' or the agent's <available_skills> prompt" >&2
    echo "           until skills.load.extraDirs includes /sandbox/.openclaw/skills" >&2
  fi

  echo "Skills installed."

  # Upload the combined REST/gRPC probe directly to /sandbox/. The probe is
  # not a skill (it's run by `cmd_test`), so it doesn't need to live under
  # the skills tree. Direct upload is preferred when policy allows it.
  #
  # IMPORTANT: `openshell sandbox upload` treats DEST as a *directory* and
  # lands the file at DEST/<basename(SRC)>. Passing a file path (e.g.
  # `/sandbox/probe_cuopt.py`) creates a directory with that name containing
  # the real file inside — Python then errors with "can't find '__main__'
  # module" when invoked against the directory. So we pass `/sandbox/` and
  # let the basename come from SRC.
  #
  # We also defensively `rm -rf` any prior file or directory at the
  # destination before uploading, and fall back to an inline base64 copy
  # via sandbox_exec if the upload fails outright.
  local probe="$SCRIPT_DIR/probe_cuopt.py"
  if [[ -f "$probe" ]]; then
    sandbox_exec "$sandbox" \
      rm -rf /sandbox/probe_cuopt.py 2>/dev/null || true

    echo "  Uploading probe_cuopt.py -> /sandbox/probe_cuopt.py"
    if ! openshell sandbox upload "$sandbox" "$probe" "/sandbox/" 2>&1; then
      echo "  Upload failed — falling back to inline base64 copy via sandbox_exec"
      local probe_b64
      probe_b64="$(base64 -w 0 < "$probe")"
      if sandbox_exec "$sandbox" \
           bash -c "echo '${probe_b64}' | base64 -d > /sandbox/probe_cuopt.py" 2>/dev/null; then
        echo "  probe_cuopt.py written via fallback"
      else
        echo "  warning: failed to write probe_cuopt.py into sandbox" >&2
      fi
    fi
  else
    echo "  warning: probe_cuopt.py not found at $probe — skipping" >&2
  fi
}


# ── add (existing sandbox shortcut) ───────────────────────────────
cmd_add() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  cmd_apply_policy "$sandbox"
  cmd_install "$sandbox"
  cmd_install_skill "$sandbox"
  # Run the test first so any UFW / connectivity output is in the middle
  # of the scrollback; then print the activation banner (always) and the
  # service-status summary (only on test failure). That way the last two
  # loud things on the screen are the next-steps banner and, when
  # something needs attention, a compact post-mortem of what cmd_test
  # actually saw.
  local test_rc=0
  cmd_test "$sandbox" || test_rc=$?
  print_activation_banner "$sandbox"
  if [[ $test_rc -ne 0 ]]; then
    print_service_status_summary "$sandbox" "$test_rc"
  fi
  return $test_rc
}


# ── dispatch ──────────────────────────────────────────────────────
usage() {
  sed -n '16,101p' "$0"
}

main() {
  # Pull out global flags before subcommand dispatch
  local args=()
  for arg in "$@"; do
    case "$arg" in
      -y|--yes) FORCE=true ;;
      *) args+=("$arg") ;;
    esac
  done
  set -- "${args[@]+"${args[@]}"}"

  local sub="${1:-}"
  shift || true

  # Skip the version banner for help/usage so it doesn't clutter docs output.
  case "${sub}" in
    help|-h|--help|"") ;;
    *) check_versions ;;
  esac

  case "${sub}" in
    apply-policy)      cmd_apply_policy "${1:-}" ;;
    install)           cmd_install "${1:-}" ;;
    install-activation) cmd_install_activation "${1:-}" ;;
    install-skill)     cmd_install_skill "${1:-}" ;;
    cache-wheels)      cmd_cache_wheels "${1:-}" ;;
    clear-wheel-cache) cmd_clear_wheel_cache ;;
    test)              cmd_test "${1:-}" ;;
    add)               cmd_add "${1:-}" ;;
    help|-h|--help)    usage ;;
    *)
      echo "unknown command: ${sub:-<none>}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
