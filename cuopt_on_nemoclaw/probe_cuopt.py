# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""Probe cuOpt service endpoints.

Checks whether the host's cuOpt REST and/or gRPC servers are reachable from
this process (sandbox or host). Used by both the setup-script smoke test and
the in-sandbox agent's capability check.

Output (default):
    rest:      <host>:<port> | unreachable
    grpc:      <host>:<port> | unreachable
    available: rest grpc | rest | grpc | none

When a probe fails, the reason is printed to stderr (e.g. "TCP refused",
"grpc client not installed", "channel not ready within 1.0s").

With --json: a single JSON object including per-service `errors`.

Exit code: 0 if at least one endpoint is reachable, 1 if neither.

Endpoints can be overridden via env (defaults shown):
    CUOPT_SERVER_HOST=host.openshell.internal   # REST
    CUOPT_SERVER_PORT=5000
    CUOPT_REMOTE_HOST=host.openshell.internal   # gRPC
    CUOPT_REMOTE_PORT=5001
    CUOPT_PROBE_TIMEOUT=1.0                     # seconds, also via --timeout
"""

import argparse
import json
import socket
import sys
import urllib.error
import urllib.request
from os import environ
from typing import Optional, Tuple


DEFAULT_HOST = "host.openshell.internal"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Probe cuOpt REST/gRPC endpoints.")
    p.add_argument(
        "--timeout",
        type=float,
        default=float(environ.get("CUOPT_PROBE_TIMEOUT", "1.0")),
        help="Per-probe timeout in seconds (default: 1.0; env CUOPT_PROBE_TIMEOUT).",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON object with full results and error reasons.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stderr error reasons (default: print on failure).",
    )
    return p.parse_args()


def probe_rest(host: str, port: int, timeout: float) -> Tuple[Optional[str], Optional[str]]:
    """Return (endpoint, error). endpoint is set on success; error on failure."""
    url = f"http://{host}:{port}/cuopt/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            if 200 <= r.status < 300:
                return f"{host}:{port}", None
            return None, f"HTTP {r.status} from {url}"
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} {e.reason} from {url}"
    except urllib.error.URLError as e:
        return None, f"URLError contacting {url}: {e.reason}"
    except (TimeoutError, socket.timeout):
        return None, f"timeout after {timeout}s contacting {url}"
    except OSError as e:
        return None, f"OSError contacting {url}: {e}"


def probe_grpc(host: str, port: int, timeout: float) -> Tuple[Optional[str], Optional[str]]:
    """Return (endpoint, error).

    Note: deliberately does NOT do a `socket.create_connection` TCP pre-check.
    Inside the OpenShell sandbox, raw TCP to `host.openshell.internal:5001`
    is gated separately from gRPC traffic (the gateway's network policy
    inspects/forwards the gRPC client's HTTP/2 differently from arbitrary
    TCP). A pre-check there returns ECONNREFUSED even when the gRPC channel
    itself would handshake successfully. Trust `channel_ready_future` as
    the source of truth.
    """
    try:
        import grpc
    except ImportError as e:
        return None, (
            f"`grpc` Python package is not installed in this interpreter "
            f"({e}). Activate the cuOpt venv "
            "(`source /sandbox/.openclaw-data/cuopt/bin/activate`) or install "
            "`grpcio`."
        )

    try:
        ch = grpc.insecure_channel(f"{host}:{port}")
        grpc.channel_ready_future(ch).result(timeout=timeout)
        return f"{host}:{port}", None
    except grpc.FutureTimeoutError:
        return None, (
            f"gRPC channel to {host}:{port} not ready within {timeout}s — "
            "server may not be running, port may not be open in the sandbox "
            "policy, or the server is slow to accept. Try `--timeout 3.0`."
        )
    except grpc.RpcError as e:
        return None, f"gRPC RpcError on {host}:{port}: {e}"
    except Exception as e:
        return None, f"unexpected error probing gRPC {host}:{port}: {type(e).__name__}: {e}"


def main() -> int:
    args = _parse_args()
    timeout = args.timeout

    rest_host = environ.get("CUOPT_SERVER_HOST", DEFAULT_HOST)
    rest_port = int(environ.get("CUOPT_SERVER_PORT", "5000"))
    grpc_host = environ.get("CUOPT_REMOTE_HOST", DEFAULT_HOST)
    grpc_port = int(environ.get("CUOPT_REMOTE_PORT", "5001"))

    rest_ep, rest_err = probe_rest(rest_host, rest_port, timeout)
    grpc_ep, grpc_err = probe_grpc(grpc_host, grpc_port, timeout)

    available = [k for k, v in (("rest", rest_ep), ("grpc", grpc_ep)) if v]
    out = {
        "rest": rest_ep,
        "grpc": grpc_ep,
        "available": available,
        "timeout_s": timeout,
        "errors": {
            "rest": rest_err,
            "grpc": grpc_err,
        },
    }

    if args.json:
        print(json.dumps(out))
    else:
        print(f"rest:      {rest_ep or 'unreachable'}")
        print(f"grpc:      {grpc_ep or 'unreachable'}")
        print(f"available: {' '.join(available) or 'none'}")

    if not args.quiet:
        if rest_ep is None and rest_err:
            print(f"rest probe: {rest_err}", file=sys.stderr)
        if grpc_ep is None and grpc_err:
            print(f"grpc probe: {grpc_err}", file=sys.stderr)

    return 0 if available else 1


if __name__ == "__main__":
    sys.exit(main())
