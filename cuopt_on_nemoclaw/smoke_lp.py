# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Remote LP smoke test for the NemoClaw cuOpt sandbox.

Verifies gRPC remote execution for LP (not MILP routing, not local CUDA).

Requires CUOPT_REMOTE_HOST and CUOPT_REMOTE_PORT in the environment when
Python starts (set them in the same ``bash -lc`` line as this script).

Success markers in combined stdout/stderr:
    Using remote GPU backend
    status=Optimal objective=10.0

Exit code: 0 on success, 1 on failure.
"""

from __future__ import annotations

import sys
from os import environ

DEFAULT_HOST = "host.openshell.internal"
DEFAULT_PORT = "5001"

OK_STATUSES = frozenset({"Optimal", "PrimalFeasible"})


def _require_remote_env() -> None:
    host = environ.get("CUOPT_REMOTE_HOST")
    port = environ.get("CUOPT_REMOTE_PORT")
    if not host or not port:
        print(
            "error: CUOPT_REMOTE_HOST and CUOPT_REMOTE_PORT must be set "
            "before Python starts.\n"
            "example:\n"
            "  bash -lc 'source /sandbox/.openclaw-data/cuopt/bin/activate && "
            f"export CUOPT_REMOTE_HOST={DEFAULT_HOST} && "
            f"export CUOPT_REMOTE_PORT={DEFAULT_PORT} && "
            "python3 /sandbox/smoke_lp.py'",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> int:
    _require_remote_env()

    from cuopt.linear_programming.problem import Problem, CONTINUOUS, MAXIMIZE
    from cuopt.linear_programming.solver_settings import SolverSettings

    p = Problem("smoke_lp")
    x = p.addVariable(lb=0, vtype=CONTINUOUS, name="x")
    y = p.addVariable(lb=0, vtype=CONTINUOUS, name="y")
    p.addConstraint(x + y <= 4)
    p.addConstraint(x <= 2)
    p.addConstraint(y <= 3)
    p.setObjective(3 * x + 2 * y, sense=MAXIMIZE)
    p.solve(SolverSettings())

    status = p.Status.name
    if status not in OK_STATUSES:
        print(f"status={status} FAIL", file=sys.stderr)
        return 1

    print(
        f"status={status} objective={p.ObjValue} "
        f"x={x.getValue()} y={y.getValue()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
