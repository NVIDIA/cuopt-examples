# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Remote MILP smoke test for the NemoClaw cuOpt sandbox.

MILP uses the same ``cuopt.linear_programming.problem.Problem`` class as LP
with ``vtype=INTEGER`` — there is no ``from cuopt import milp``.

Requires CUOPT_REMOTE_HOST and CUOPT_REMOTE_PORT when Python starts.

Success markers:
    Using remote GPU backend
    status=Optimal (or FeasibleFound)

Exit code: 0 on success, 1 on failure.
"""

from __future__ import annotations

import sys
from os import environ

OK_STATUSES = frozenset({"Optimal", "FeasibleFound", "PrimalFeasible"})


def _require_remote_env() -> None:
    if not environ.get("CUOPT_REMOTE_HOST") or not environ.get("CUOPT_REMOTE_PORT"):
        print(
            "error: export CUOPT_REMOTE_HOST and CUOPT_REMOTE_PORT before "
            "running (see /sandbox/.openclaw/skills/cuopt-remote-env/SKILL.md)",
            file=sys.stderr,
        )
        sys.exit(1)


def main() -> int:
    _require_remote_env()

    from cuopt.linear_programming.problem import Problem, INTEGER, MAXIMIZE
    from cuopt.linear_programming.solver_settings import SolverSettings

    # Need at least one constraint so the CSR matrix (A_offsets) is built.
    # Tiny 2-variable integer problem (same shape as milp_basic, smaller nums).
    p = Problem("smoke_milp")
    x = p.addVariable(vtype=INTEGER, lb=0, ub=10, name="x")
    y = p.addVariable(vtype=INTEGER, lb=0, ub=10, name="y")
    p.addConstraint(x + y <= 4)
    p.addConstraint(x <= 2)
    p.setObjective(x + 2 * y, sense=MAXIMIZE)
    settings = SolverSettings()
    settings.set_parameter("time_limit", 60)
    p.solve(settings)

    status = p.Status.name
    if status not in OK_STATUSES:
        print(f"status={status} FAIL", file=sys.stderr)
        return 1

    print(f"status={status} objective={p.ObjValue} x={x.getValue()} y={y.getValue()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
