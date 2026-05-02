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
#   add [NAME]             Add cuOpt to a sandbox: policy + install + skill + test.
#   apply-policy [NAME]    Add cuOpt network policy to a running sandbox.
#   install [NAME]         Install cuOpt packages in the sandbox venv and stamp
#                          an auto-activation block into /sandbox/.bashrc.
#   install-bashrc [NAME]  Re-stamp the auto-activation block in /sandbox/.bashrc
#                          without reinstalling the venv (useful after changing
#                          CUOPT_HOST, CUOPT_PORT, or CUOPT_VENV).
#   install-skill [NAME]   Upload the cuOpt skill into the sandbox.
#   test [NAME]            Smoke-test PyPI + cuOpt server reachability.
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
#                      (default: main).
#   CUOPT_SKILLS_SKIP  Comma-separated glob patterns matching upstream skill
#                      names to NOT install (default:
#                      *installation*,*developer*,*-api-c).
#                      *installation* — host-side install flows; cuOpt is
#                          already installed in the sandbox.
#                      *developer*    — for contributing to the cuOpt
#                          codebase; agents use cuOpt, they don't build it.
#                      *-api-c        — libcuopt is present so the C API
#                          works, but its CSR-matrix inputs are awkward to
#                          build from an agent; the Python API is strictly
#                          easier. Override this to ship them anyway.
#
# Examples:
#   ./nemoclaw_cuopt_setup.sh add cuopt        # Add cuOpt to sandbox "cuopt"
#   ./nemoclaw_cuopt_setup.sh add my-assistant # Add cuOpt to any sandbox
#   ./nemoclaw_cuopt_setup.sh apply-policy bob # Just fix network policy
#   ./nemoclaw_cuopt_setup.sh test cuopt       # Re-run smoke test
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
# a tag or commit SHA so users get a reproducible vendoring even when
# upstream main moves. Update deliberately, alongside the version banner
# constants above, when a newer cuOpt skill release is verified. Override
# at runtime with CUOPT_SKILLS_REF=<ref>.
TESTED_CUOPT_SKILLS_REF="main"
CUOPT_SKILLS_REF="${CUOPT_SKILLS_REF:-${TESTED_CUOPT_SKILLS_REF}}"
CUOPT_SKILLS_SKIP="${CUOPT_SKILLS_SKIP:-*installation*,*developer*,*-api-c}"
FORCE=false

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
TESTED_NEMOCLAW_VERSION="0.0.30"
TESTED_OPENSHELL_VERSION="0.0.36"

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



# ── Detect the exact Python binary path inside the sandbox image ──
# OpenShell requires exact binary paths (no globs).
detect_python_bin() {
  if [[ -n "$CUOPT_PYTHON_BIN" ]]; then
    echo "$CUOPT_PYTHON_BIN"
    return
  fi

  # Try detecting from a running sandbox
  local sandbox="${1:-}"
  if [[ -n "$sandbox" ]]; then
    local resolved
    resolved="$(echo 'readlink -f /usr/bin/python3 && exit' \
                | openshell sandbox connect "$sandbox" 2>/dev/null \
                | grep '^/usr/bin/python3' | head -1)"
    if [[ -n "$resolved" ]]; then
      echo "$resolved"
      return
    fi
  fi

  echo >&2 "  (no running sandbox to detect from — using default /usr/bin/python3.11;"
  echo >&2 "   set CUOPT_PYTHON_BIN to override)"
  echo "/usr/bin/python3.11"
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
    ip="$(echo 'getent hosts host.openshell.internal | awk "{print \$1}" && exit' \
          | openshell sandbox connect "$sandbox" 2>/dev/null \
          | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
    if [[ -n "$ip" ]]; then
      echo "$ip"
      return
    fi
  fi

  echo >&2 "  (no running sandbox to detect from — using default 172.17.0.1;"
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

# ── Policy entry generation (used by apply-policy) ───────────────
# OpenShell binary paths must be exact — globs (*, **) are silently ignored.
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

  cat <<YAML

  # ── cuOpt: PyPI + NVIDIA PyPI + cuOpt server (nvidia-cuopt cuopt_claw) ──
  # Binary paths must be exact (no globs) — OpenShell enforces literal matching.
  # Hostname endpoints need allowed_ips for the proxy to match resolved IPs.
  pypi_public:
    name: pypi-public
    endpoints:
      - host: pypi.org
        port: 443
      - host: files.pythonhosted.org
        port: 443
    binaries:
      - { path: ${python_bin} }

  nvidia_pypi:
    name: nvidia-pypi
    endpoints:
      - host: pypi.nvidia.com
        port: 443
    binaries:
      - { path: ${python_bin} }

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
      - { path: ${python_bin} }
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


# ── install ───────────────────────────────────────────────────────
cmd_install() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local venv="/sandbox/${CUOPT_VENV}"
  echo "Installing cuopt_sh_client in ${venv} venv (sandbox: $sandbox) ..."

  # Detect the sandbox's Python and check it against the policy.
  local actual_python
  actual_python="$(detect_python_bin "$sandbox")"
  echo "Sandbox Python binary: $actual_python"

  local root policy_file
  root="$(find_nemoclaw_root 2>/dev/null || true)"
  if [[ -n "$root" ]]; then
    policy_file="$root/nemoclaw-blueprint/policies/openclaw-sandbox.yaml"
    if [[ -f "$policy_file" ]] && grep -q 'cuopt_host:' "$policy_file"; then
      local policy_python
      policy_python="$(grep -A 20 'cuopt_host:' "$policy_file" \
                       | grep '{ path: /usr/bin/python' \
                       | head -1 \
                       | sed 's/.*{ path: \([^ }]*\).*/\1/')"
      if [[ -n "$policy_python" && "$policy_python" != "$actual_python" ]]; then
        echo ""
        echo "WARNING: Python version mismatch!"
        echo "  Sandbox has:    $actual_python"
        echo "  Policy expects: $policy_python"
        echo ""
        echo "  Network requests from Python will be blocked (403 Forbidden)."
        echo "  Fix: re-run apply-policy to update the policy:"
        echo "    $0 apply-policy $sandbox"
        echo ""
      fi
    fi
  fi

  local commands=(
    "python3 -m venv ${venv}"
    "source ${venv}/bin/activate"
    "pip install cuopt-sh-client cuopt-cu12==26.04 grpcio --extra-index-url=https://pypi.nvidia.com"
    "python3 -c \"import cuopt_sh_client; print('cuopt_sh_client', cuopt_sh_client.__version__)\""
    "exit"
  )

  printf '%s\n' "${commands[@]}" | openshell sandbox connect "$sandbox"

  local cuopt_ip="host.openshell.internal"
  [[ -n "$CUOPT_HOST" ]] && cuopt_ip="$CUOPT_HOST"

  if install_bashrc_activation "$sandbox" "$cuopt_ip" "$CUOPT_PORT"; then
    cat <<EOF
Install complete. Auto-activation is installed in /sandbox/.bashrc
(mode 0444, Landlock read-only). Reconnect with:

    nemoclaw ${sandbox} connect

The venv, CUOPT_SERVER, and cuopt_sh alias will be active in every shell.
EOF
  else
    cat <<EOF
Install complete, but auto-activation could not be installed in
/sandbox/.bashrc (see warning above). Activate manually per session:

    nemoclaw ${sandbox} connect
    source ${venv}/bin/activate
    export CUOPT_SERVER=${cuopt_ip}:${CUOPT_PORT}
EOF
  fi
}

# ── install-bashrc ────────────────────────────────────────────────
# Re-stamp /sandbox/.bashrc with the current CUOPT_VENV / CUOPT_HOST / CUOPT_PORT
# values without touching the venv. Useful after changing the cuOpt server.
cmd_install_bashrc() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local cuopt_ip="host.openshell.internal"
  [[ -n "$CUOPT_HOST" ]] && cuopt_ip="$CUOPT_HOST"
  install_bashrc_activation "$sandbox" "$cuopt_ip" "$CUOPT_PORT"
}

# ── install_bashrc_activation (helper) ────────────────────────────
# Drop a managed auto-activation block into /sandbox/.bashrc as root via the
# gateway container, the same escape hatch cmd_install_skill already uses for
# the cuopt-setup guardrail. The default NemoClaw filesystem policy marks
# /sandbox as Landlock read-only, so a file written here can be sourced by the
# sandbox user's shell but cannot be modified by the agent. The kubectl-exec'd
# root process is NOT in the user's Landlock process tree so it can write.
#
# The block is delimited by stable begin/end markers so re-stamping is exact
# (no fragile partial-line matching).
#
# Returns 0 on success, 1 if docker/gateway is unavailable.
install_bashrc_activation() {
  local sandbox="$1"
  local cuopt_ip="$2"
  local cuopt_port="$3"
  local venv="/sandbox/${CUOPT_VENV}"
  local gw="${GATEWAY_CONTAINER:-openshell-cluster-nemoclaw}"
  local ns="${K8S_NAMESPACE:-openshell}"

  if ! command -v docker >/dev/null 2>&1; then
    echo "  warning: docker not found on host — cannot install /sandbox/.bashrc" >&2
    return 1
  fi

  # The inner script runs as root inside the sandbox pod via kubectl exec.
  # Base64 over the whole payload so we don't have to fight three layers of
  # shell quoting (bash here-doc -> docker exec -> kubectl exec -- sh -c).
  # Variables we want expanded NOW (outer bash): ${venv}, ${cuopt_ip},
  # ${cuopt_port}. Variables we want expanded by the inner sh: escaped with \$.
  local inner_script
  inner_script=$(cat <<INNER_EOF
set -eu
bashrc=/sandbox/.bashrc
begin='# >>> cuopt activation (managed by nemoclaw_cuopt_setup.sh) >>>'
end='# <<< cuopt activation <<<'

[ -f "\$bashrc" ] || : > "\$bashrc"
chmod 0644 "\$bashrc"

# Idempotent re-stamp: strip any previous block between the markers.
if grep -qF "\$begin" "\$bashrc" 2>/dev/null; then
  b=\$(grep -nF "\$begin" "\$bashrc" | head -1 | cut -d: -f1)
  e=\$(grep -nF "\$end"   "\$bashrc" | head -1 | cut -d: -f1)
  if [ -n "\$b" ] && [ -n "\$e" ] && [ "\$e" -ge "\$b" ]; then
    sed -i "\${b},\${e}d" "\$bashrc"
  fi
fi

cat >> "\$bashrc" <<BASHRC_EOF
\$begin
if [ -f ${venv}/bin/activate ]; then
  . ${venv}/bin/activate
  export CUOPT_SERVER=${cuopt_ip}:${cuopt_port}
  alias cuopt_sh='cuopt_sh -i ${cuopt_ip} -p ${cuopt_port}'
fi
\$end
BASHRC_EOF

# sed -i and 'cat > file' (for a freshly-created file) end up as root:root.
# Restore the NemoClaw default (sandbox:sandbox) so 'ls -l' looks normal.
chown sandbox:sandbox "\$bashrc" 2>/dev/null || true
chmod 0444 "\$bashrc"
INNER_EOF
)

  local inner_b64
  inner_b64=$(printf '%s' "$inner_script" | base64 -w 0)

  if docker exec "$gw" kubectl exec -n "$ns" "$sandbox" -- \
       sh -c "echo '$inner_b64' | base64 -d | sh" >/dev/null 2>&1; then
    echo "  Installed cuOpt auto-activation in /sandbox/.bashrc (mode 0444, Landlock read-only)"
    return 0
  fi

  echo "  warning: could not install /sandbox/.bashrc via gateway" >&2
  echo "    gateway container: $gw   sandbox namespace: $ns" >&2
  echo "    override with GATEWAY_CONTAINER=... / K8S_NAMESPACE=..." >&2
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

  if [[ "$has_grpc" == false && "$has_rest" == false ]]; then
    echo ""
    echo "No cuOpt server detected on the host."
    echo "  - Nothing listening on port ${CUOPT_PORT} (REST)"
    echo "  - Nothing listening on port ${CUOPT_GRPC_PORT} (gRPC)"
    echo "  Start a cuOpt server first, then re-run: $0 test ${sandbox}"
    echo ""
    return 1
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
  if [[ "$has_rest" == true ]] \
     && grep -qE '^rest:[[:space:]]+unreachable' "$probe_log"; then
    rest_unreachable=true
  fi
  if [[ "$has_grpc" == true ]] \
     && grep -qE '^grpc:[[:space:]]+unreachable' "$probe_log"; then
    grpc_unreachable=true
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
# Glob is bash extglob-free; '*' and '?' work as expected (e.g. *installation*).
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

  echo "Installing skills into sandbox '$sandbox' ..."
  for skill in "$skills_dir"/*/; do
    name="$(basename "$skill")"
    if [[ -f "$skill/SKILL.md" ]]; then
      echo "  Uploading local skill: $name"
      if openshell sandbox upload "$sandbox" "$skill" "/sandbox/.openclaw/skills/$name" 2>&1; then
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
      if ! openshell sandbox upload "$sandbox" "$skill" "/sandbox/.openclaw/skills/$upstream_name" 2>&1; then
        echo "  warning: upload failed for upstream skill '$upstream_name'" >&2
      fi
    done

    # Validate SKIP patterns. A glob in CUOPT_SKILLS_SKIP that matches no
    # upstream name almost always means upstream renamed/removed the
    # category the pattern targeted (e.g. *installation* before/after a
    # skill consolidation). We surface this so the operator can update
    # the SKIP list rather than silently shipping skills they intended
    # to filter out.
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
  # Best-effort — if docker exec is unavailable the managed skill still works
  # whenever ~ resolves correctly.
  local gw="${GATEWAY_CONTAINER:-openshell-cluster-nemoclaw}"
  local ns="${K8S_NAMESPACE:-openshell}"
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
cuopt-lp-milp-api-python, cuopt-routing-api-python, lp-milp-formulation,
etc.) which live in the same `/sandbox/.openclaw/skills/` directory.

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
  docker exec "$gw" \
    kubectl exec -n "$ns" "$sandbox" -- \
    sh -c "mkdir -p '${bundled_dir}' && echo '${b64}' | base64 -d > '${bundled_dir}/SKILL.md'" \
    2>/dev/null \
  || echo "  warning: could not install cuopt-setup guardrail (non-fatal)" >&2

  # ── invalidate cached <available_skills> snapshot ───────────────────
  # OpenClaw caches the skills prompt in a per-session snapshot stored in
  # ~/.openclaw/agents/<id>/sessions/sessions.json. The snapshot is built
  # on the agent's first run and reused thereafter, so skills uploaded
  # *after* that first run never appear in <available_skills>.
  #
  # The supported invalidation hook is the gateway's openclaw.json
  # watcher (openclaw/src/gateway/config-reload.ts): when any path
  # under `skills.*` changes, it bumps the snapshot version and the
  # next agent run rebuilds the prompt from disk.
  #
  # We use only schema-defined keys (SkillsLoadConfig.watch /
  # watchDebounceMs and SkillConfig.config) so the resulting config
  # remains valid:
  #   • skills.load.watch=true                            — best-effort
  #     filesystem-watch invalidation for future drops; chokidar inside
  #     the sandbox is not always reliable so we don't rely on it.
  #   • skills.entries.cuopt-sandbox.config.lastInstallAt — a fresh ISO
  #     timestamp on every install guarantees a non-empty config diff
  #     even if `watch` is already true.
  echo "  Invalidating cached skills snapshot via openclaw.json update ..."
  local invalidator
  invalidator='
import json, os, sys, time, tempfile
cfg_path = "/sandbox/.openclaw/openclaw.json"
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
load["watch"] = True
load.setdefault("watchDebounceMs", 250)
entries = skills.setdefault("entries", {})
sentinel = entries.setdefault("cuopt-sandbox", {})
sentinel_cfg = sentinel.setdefault("config", {})
sentinel_cfg["lastInstallAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
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
print("    skills.entries.cuopt-sandbox.config.lastInstallAt=" + sentinel_cfg["lastInstallAt"])
'
  local invalidator_b64
  invalidator_b64="$(printf '%s' "$invalidator" | base64 -w 0)"
  if ! openshell sandbox exec --name "$sandbox" --no-tty -- \
        bash -c "echo '${invalidator_b64}' | base64 -d | python3" 2>&1; then
    echo "  warning: failed to bump openclaw.json — agent may continue using a stale" >&2
    echo "           skills snapshot until the next config change or a fresh onboard" >&2
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
  # via `openshell sandbox exec` if the upload fails outright.
  local probe="$SCRIPT_DIR/probe_cuopt.py"
  if [[ -f "$probe" ]]; then
    openshell sandbox exec --name "$sandbox" --no-tty -- \
      rm -rf /sandbox/probe_cuopt.py 2>/dev/null || true

    echo "  Uploading probe_cuopt.py -> /sandbox/probe_cuopt.py"
    if ! openshell sandbox upload "$sandbox" "$probe" "/sandbox/" 2>&1; then
      echo "  Upload failed — falling back to inline base64 copy via sandbox exec"
      local probe_b64
      probe_b64="$(base64 -w 0 < "$probe")"
      if openshell sandbox exec --name "$sandbox" --no-tty -- \
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
  cmd_test "$sandbox"
}


# ── dispatch ──────────────────────────────────────────────────────
usage() {
  sed -n '16,70p' "$0"
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
    apply-policy)   cmd_apply_policy "${1:-}" ;;
    install)        cmd_install "${1:-}" ;;
    install-bashrc) cmd_install_bashrc "${1:-}" ;;
    install-skill)  cmd_install_skill "${1:-}" ;;
    test)           cmd_test "${1:-}" ;;
    add)            cmd_add "${1:-}" ;;
    help|-h|--help) usage ;;
    *)
      echo "unknown command: ${sub:-<none>}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
