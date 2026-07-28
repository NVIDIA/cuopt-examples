# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""gRPC MILP smoke test for the NemoClaw cuOpt sandbox.

MILP uses the same ``cuopt.linear_programming.problem.Problem`` class as LP
with ``vtype=INTEGER`` — there is no ``from cuopt import milp``.

Success markers:
    execution_mode=async-grpc job_status=COMPLETED ...
    execution_mode=remote-execution status=Optimal ...

Exit code: 0 on success, 1 on failure.
"""

from __future__ import annotations

import sys
from os import environ

DEFAULT_HOST = "host.openshell.internal"
DEFAULT_PORT = 5001
OK_STATUSES = frozenset({"Optimal", "FeasibleFound", "PrimalFeasible"})


def main() -> int:
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

    try:
        from cuopt.grpc.linear_programming import Client, JobStatus
    except (ImportError, ModuleNotFoundError):
        if not environ.get("CUOPT_REMOTE_HOST") or not environ.get(
            "CUOPT_REMOTE_PORT"
        ):
            print(
                "error: async gRPC client unavailable; set CUOPT_REMOTE_HOST "
                "and CUOPT_REMOTE_PORT before Python starts",
                file=sys.stderr,
            )
            return 1
        print(
            "execution_mode=remote-execution cancellation=unavailable",
            flush=True,
        )
        p.solve(settings)
        status = p.Status.name
        if status not in OK_STATUSES:
            print(f"execution_mode=remote-execution status={status} FAIL")
            return 1
        print(
            f"execution_mode=remote-execution status={status} "
            f"objective={p.ObjValue} x={x.getValue()} y={y.getValue()}"
        )
        return 0

    client = Client(DEFAULT_HOST, DEFAULT_PORT, tls=False)
    job_id = client.submit(p, settings)
    print(f"job_id={job_id}", flush=True)
    try:
        status = client.wait(job_id, timeout=120)
        if status != JobStatus.COMPLETED:
            print(f"job_status={status.name} FAIL", file=sys.stderr)
            return 1

        names = [variable.getVariableName() for variable in p.getVariables()]
        solution = client.result(job_id, names)
        if solution is None:
            print("job_status=COMPLETED result=None FAIL", file=sys.stderr)
            return 1

        values = solution.get_vars()
        print(
            f"execution_mode=async-grpc job_status={status.name} "
            f"termination={solution.get_termination_reason()} "
            f"objective={solution.get_primal_objective()} "
            f"x={values['x']} y={values['y']}"
        )
        return 0
    finally:
        # delete() cancels queued/running jobs, then removes server state.
        if client.status(job_id) != JobStatus.NOT_FOUND:
            client.delete(job_id)


if __name__ == "__main__":
    sys.exit(main())
