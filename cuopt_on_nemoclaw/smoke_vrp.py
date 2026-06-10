# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""REST VRP smoke test for the NemoClaw cuOpt sandbox.

Routing uses REST on port 5000 (not CUOPT_REMOTE_* gRPC vars).
Do not use ``from cuopt import routing`` — there is no GPU in the sandbox.

Env (defaults shown):
    CUOPT_SERVER_HOST=host.openshell.internal
    CUOPT_SERVER_PORT=5000

Success markers:
    status=0
    solution_cost present in solver_response

Exit code: 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import sys
import time
from os import environ
from typing import Any

DEFAULT_HOST = "host.openshell.internal"
DEFAULT_PORT = "5000"

# Minimal valid payload (same shape as vrp_minimal cookbook).
PAYLOAD: dict[str, Any] = {
    "cost_matrix_data": {
        "data": {
            "0": [
                [0, 1, 1],
                [1, 0, 1],
                [1, 1, 0],
            ]
        }
    },
    "task_data": {"task_locations": [1, 2]},
    "fleet_data": {"vehicle_locations": [[0, 0]]},
    "solver_config": {"time_limit": 30},
}


def _repoll(client: Any, solution: dict[str, Any], tries: int = 120) -> dict[str, Any]:
    if "reqId" not in solution or "response" in solution:
        return solution
    req_id = solution["reqId"]
    for _ in range(tries):
        solution = client.repoll(req_id, response_type="dict")
        if "response" in solution:
            return solution
        time.sleep(1)
    return solution


def main() -> int:
    host = environ.get("CUOPT_SERVER_HOST", DEFAULT_HOST)
    port = environ.get("CUOPT_SERVER_PORT", DEFAULT_PORT)

    from cuopt_sh_client import CuOptServiceSelfHostClient

    client = CuOptServiceSelfHostClient(
        ip=host,
        port=str(port),
        polling_timeout=60,
        timeout_exception=False,
    )
    solution = client.get_optimized_routes(PAYLOAD)
    solution = _repoll(client, solution)

    if "response" not in solution:
        print(
            "error: no response from REST VRP (still polling or server error)",
            file=sys.stderr,
        )
        print(json.dumps(solution, indent=2), file=sys.stderr)
        return 1

    sr = solution["response"].get("solver_response", {})
    status = sr.get("status")
    cost = sr.get("solution_cost")
    if status != 0:
        print(f"status={status} FAIL", file=sys.stderr)
        print(json.dumps(solution, indent=2), file=sys.stderr)
        return 1

    print(f"status={status} solution_cost={cost} host={host} port={port}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
