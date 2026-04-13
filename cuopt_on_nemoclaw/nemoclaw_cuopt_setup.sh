#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
#   add [NAME]            Add cuOpt to a sandbox: policy + install + skill + test.
#   apply-policy [NAME]   Add cuOpt network policy to a running sandbox.
#   install [NAME]        Install cuOpt packages in /sandbox/cuopt venv.
#   install-skill [NAME]  Upload the cuOpt skill into the sandbox.
#   test [NAME]           Smoke-test PyPI + cuOpt server reachability.
#
# Flags:
#   -y, --yes       Skip confirmation prompts (for CI/CD).
#   --activate      Add venv auto-activation to .bashrc (install only;
#                   always on for 'add').
#
# Environment:
#   CUOPT_SANDBOX   Sandbox name             (default: cuopt)
#   CUOPT_VENV      Venv directory name under /sandbox/  (default: cuopt)
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
#
# Examples:
#   ./cuopt_claw/nemoclaw_cuopt_setup.sh add cuopt        # Add cuOpt to sandbox "cuopt"
#   ./cuopt_claw/nemoclaw_cuopt_setup.sh add my-assistant  # Add cuOpt to any sandbox
#   ./cuopt_claw/nemoclaw_cuopt_setup.sh apply-policy bob  # Just fix network policy
#   ./cuopt_claw/nemoclaw_cuopt_setup.sh test cuopt        # Re-run smoke test
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CUOPT_SANDBOX="${CUOPT_SANDBOX:-cuopt}"
CUOPT_VENV="${CUOPT_VENV:-cuopt}"
CUOPT_HOST="${CUOPT_HOST:-}"
CUOPT_PORT="${CUOPT_PORT:-5000}"
CUOPT_GRPC_PORT="${CUOPT_GRPC_PORT:-5001}"
CUOPT_PYTHON_BIN="${CUOPT_PYTHON_BIN:-}"
CUOPT_HOST_IP="${CUOPT_HOST_IP:-}"
FORCE=false
ACTIVATE=false

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

# ── Firewall check ────────────────────────────────────────────────
# Docker containers need to reach the host on CUOPT_PORT and/or
# CUOPT_GRPC_PORT. If UFW drops that traffic, sandbox connections hang.
# Also detects stale rules for bridges that no longer exist (e.g. after
# nemoclaw destroy / onboard recreates the Docker network).
# Usage: check_firewall [port ...]
#   If ports are given, only check those. Otherwise check both.
check_firewall() {
  if ! command -v ufw &>/dev/null; then return 0; fi
  local status
  status="$(sudo -n ufw status 2>/dev/null || ufw status 2>/dev/null || true)"
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
  done < <(ip -o link show type bridge 2>/dev/null \
           | awk -F': ' '{print $2}' \
           | grep -E '^(docker|br-)' || true)
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
  )

  local cuopt_ip="host.openshell.internal"
  [[ -n "$CUOPT_HOST" ]] && cuopt_ip="$CUOPT_HOST"

  if [[ "$ACTIVATE" == true ]]; then
    commands+=(
      ""
      "if ! grep -q '${venv}/bin/activate' /sandbox/.bashrc 2>/dev/null; then"
      "  echo '' >> /sandbox/.bashrc"
      "  echo '# cuOpt environment (added by nemoclaw_cuopt_setup.sh)' >> /sandbox/.bashrc"
      "  echo 'if [ -f ${venv}/bin/activate ]; then source ${venv}/bin/activate; fi' >> /sandbox/.bashrc"
      "  echo 'export CUOPT_SERVER=${cuopt_ip}:${CUOPT_PORT}' >> /sandbox/.bashrc"
      "  echo 'alias cuopt_sh=\"cuopt_sh -i ${cuopt_ip} -p ${CUOPT_PORT}\"' >> /sandbox/.bashrc"
      "  echo 'Added venv auto-activation + cuopt_sh alias to /sandbox/.bashrc'"
      "fi"
    )
  fi

  commands+=("exit")
  printf '%s\n' "${commands[@]}" | openshell sandbox connect "$sandbox"
  echo "Install complete."
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

  local sandbox_cmds="
source ${venv}/bin/activate
echo '--- pip check ---'
python3 -c \"import cuopt_sh_client; print('cuopt_sh_client', cuopt_sh_client.__version__)\"
"

  if [[ "$has_grpc" == true ]]; then
    sandbox_cmds+="
echo ''
echo '--- gRPC server (${grpc_host}:${CUOPT_GRPC_PORT}) ---'
CUOPT_REMOTE_HOST=${grpc_host} CUOPT_REMOTE_PORT=${CUOPT_GRPC_PORT} python3 /sandbox/probe_grpc.py || true
"
  fi

  if [[ "$has_rest" == true ]]; then
    sandbox_cmds+="
echo ''
echo '--- REST server (${cuopt_url}) ---'
python3 -c \"
import requests
try:
    r = requests.get('${cuopt_url}/cuopt/health', timeout=5)
    print(f'REST: status {r.status_code}')
    print(f'REST: {r.text[:300]}')
except Exception as e:
    print(f'REST: NOT reachable ({e})')
\"
"
  fi

  sandbox_cmds+="
echo ''
exit
"
  echo "$sandbox_cmds" | openshell sandbox connect "$sandbox"
  echo "Test complete."

  # Only warn about firewall for ports that are actually listening
  local check_ports=()
  [[ "$has_rest" == true ]] && check_ports+=("${CUOPT_PORT}")
  [[ "$has_grpc" == true ]] && check_ports+=("${CUOPT_GRPC_PORT}")
  check_firewall "${check_ports[@]}"
}

# ── install-skill ─────────────────────────────────────────────────
cmd_install_skill() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  local skills_dir="$SCRIPT_DIR/openclaw-skills"

  if [[ ! -d "$skills_dir" ]]; then
    echo "error: skills directory not found at $skills_dir" >&2
    exit 1
  fi

  echo "Installing skills into sandbox '$sandbox' ..."
  for skill in "$skills_dir"/*/; do
    local name
    name="$(basename "$skill")"
    if [[ -f "$skill/SKILL.md" ]]; then
      echo "  Uploading skill: $name"
      if ! openshell sandbox upload "$sandbox" "$skill" "/sandbox/.openclaw-data/skills/$name" 2>&1; then
        echo "  warning: upload failed for skill '$name'" >&2
      fi
    fi
  done

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
description: "Read this FIRST when working with cuOpt. If you cannot read the cuopt skill at ~/.openclaw/skills/cuopt/SKILL.md, this tells you where the real file lives."
---

# cuOpt skill — path resolution

The full cuOpt skill is installed at an absolute path that always works:

    /sandbox/.openclaw-data/skills/cuopt/SKILL.md

Read that file now for complete cuOpt usage instructions.

## Why this guardrail exists

OpenClaw compacts skill paths to `~/…` in the system prompt. When you try
to read `~/.openclaw/skills/cuopt/SKILL.md`, the `~` may expand to `/root/`
or another directory that is not readable. If that happens:

1. Do NOT give up on using cuOpt.
2. Read the skill from the absolute path above.
3. Also check `/sandbox/.openclaw/skills/cuopt/SKILL.md` (symlink to same file).
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

  echo "Skills installed."

  # Upload gRPC probe script
  local probe="$SCRIPT_DIR/probe_grpc.py"
  if [[ -f "$probe" ]]; then
    echo "  Uploading probe_grpc.py"
    if ! openshell sandbox upload "$sandbox" "$probe" "/sandbox/probe_grpc.py" 2>&1; then
      echo "  Upload failed — falling back to inline copy via sandbox connect"
      local probe_content
      probe_content="$(cat "$probe")"
      printf '%s\n' \
        "cat > /sandbox/probe_grpc.py << 'PROBE_EOF'" \
        "$probe_content" \
        "PROBE_EOF" \
        "exit" \
      | openshell sandbox connect "$sandbox" >/dev/null 2>&1
      if openshell sandbox connect "$sandbox" -- test -f /sandbox/probe_grpc.py 2>/dev/null; then
        echo "  probe_grpc.py written via fallback"
      else
        echo "  warning: failed to write probe_grpc.py into sandbox" >&2
      fi
    fi
  else
    echo "  warning: probe_grpc.py not found at $probe — skipping" >&2
  fi
}


# ── add (existing sandbox shortcut) ───────────────────────────────
cmd_add() {
  local sandbox="${1:-$CUOPT_SANDBOX}"
  ACTIVATE=true
  cmd_apply_policy "$sandbox"
  cmd_install "$sandbox"
  cmd_install_skill "$sandbox"
  cmd_test "$sandbox"
}


# ── dispatch ──────────────────────────────────────────────────────
usage() {
  sed -n '2,37p' "$0"
}

main() {
  # Pull out global flags before subcommand dispatch
  local args=()
  for arg in "$@"; do
    case "$arg" in
      -y|--yes) FORCE=true ;;
      --activate) ACTIVATE=true ;;
      *) args+=("$arg") ;;
    esac
  done
  set -- "${args[@]+"${args[@]}"}"

  local sub="${1:-}"
  shift || true
  case "${sub}" in
    apply-policy)  cmd_apply_policy "${1:-}" ;;
    install)       cmd_install "${1:-}" ;;
    install-skill) cmd_install_skill "${1:-}" ;;
    test)          cmd_test "${1:-}" ;;
    add)           cmd_add "${1:-}" ;;
    help|-h|--help) usage ;;
    *)
      echo "unknown command: ${sub:-<none>}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
