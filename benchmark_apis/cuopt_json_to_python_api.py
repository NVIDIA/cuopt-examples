#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.  # noqa
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
"""
cuOpt JSON to Problem API Converter (Version 2 - Bounds-Based Constraint Types)

This script reads a cuOpt JSON problem file (specified as a command line argument)
and converts it to use the new high-level Problem API for solving Linear 
Programming (LP) and Mixed Integer Programming (MIP) problems.

This version determines constraint types from explicit lower and upper bounds 
rather than using constraint type information from the JSON file, similar to the
approach used in cvxpy JSON readers.

Usage: python cuopt_json_to_python_api.py <json_file_path>

The cuOpt JSON format contains:
- CSR constraint matrix (offsets, indices, values)  
- Constraint bounds with separate lower_bounds and upper_bounds arrays
- Objective coefficients
- Variable bounds and types
- Variable names

Constraint Type Logic:
- Equality constraints: lower_bound == upper_bound (both finite)
- Upper bound constraints: finite upper_bound and not equality
- Lower bound constraints: finite lower_bound and not equality

Note: This version uses constraint_bounds["lower_bounds"] and 
constraint_bounds["upper_bounds"] and ignores constraint_bounds["bounds"]
"""

import json
import numpy as np
import sys
import time
from typing import Dict, Any, List

from cuopt.linear_programming.problem import Problem, VType, CType, sense, Constraint
from cuopt.linear_programming.solver_settings import SolverSettings

from cuopt.linear_programming.internals import (
    GetSolutionCallback,
    SetSolutionCallback,
)
def handle_infinity_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert string representations of infinity back to float values.
    
    cuOpt JSON files may contain "inf" and "ninf" strings that need to be 
    converted back to float('inf') and float('-inf').
    """
    def transform_list(lst):
        return [
            float('inf') if x == "inf" else 
            float('-inf') if x == "ninf" else x 
            for x in lst
        ]
    
    def transform_recursive(obj):
        if isinstance(obj, dict):
            return {k: transform_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return transform_list(obj)
        else:
            return obj
    
    return transform_recursive(data)


def create_problem_from_cuopt_json(json_file_path: str) -> Problem:
    """
    Read a cuOpt JSON file and create a Problem instance using the new API.
    
    Parameters
    ----------
    json_file_path : str
        Path to the cuOpt JSON file
        
    Returns
    -------
    Problem
        A Problem instance ready to be solved
    """
    
    # Read the JSON file
    with open(json_file_path, 'r') as f:
        problem_data = json.load(f)

    print(f"PROBLEM_START: {time.time()}")
        
    # Handle infinity values
    problem_data = handle_infinity_values(problem_data)
    
    # Extract data from JSON structure
    csr_matrix = problem_data["csr_constraint_matrix"]
    constraint_bounds = problem_data["constraint_bounds"] 
    objective_data = problem_data["objective_data"]
    variable_bounds = problem_data["variable_bounds"]
    variable_types = problem_data["variable_types"]
    variable_names = problem_data.get("variable_names", [])
    maximize = problem_data.get("maximize", False)
    
    # Create the problem
    prob = Problem("cuOpt JSON Problem")
    
    # Determine variable type mapping
    def get_vtype(var_type_char):
        if isinstance(var_type_char, bytes):
            var_type_char = var_type_char.decode('utf-8')
        return VType.INTEGER if var_type_char == 'I' else VType.CONTINUOUS
    
    # Add variables
    num_vars = len(variable_bounds["lower_bounds"])
    variables = []
    
    for i in range(num_vars):
        lb = variable_bounds["lower_bounds"][i]
        ub = variable_bounds["upper_bounds"][i]
        obj_coeff = objective_data["coefficients"][i] if i < len(objective_data["coefficients"]) else 0.0
        vtype = get_vtype(variable_types[i]) if i < len(variable_types) else VType.CONTINUOUS
        name = variable_names[i] if i < len(variable_names) else f"x_{i}"
        
        var = prob.addVariable(lb=lb, ub=ub, obj=obj_coeff, vtype=vtype, name=name)
        variables.append(var)
    
    # Add constraints from CSR matrix
    offsets = csr_matrix["offsets"]
    indices = csr_matrix["indices"] 
    values = csr_matrix["values"]
    
    # Extract lower and upper bounds for constraints directly
    # Use only lower_bounds and upper_bounds, ignore constraint_bounds["bounds"]
    lower_bounds = np.array(constraint_bounds["lower_bounds"])
    upper_bounds = np.array(constraint_bounds["upper_bounds"])
    
    num_constraints = len(offsets) - 1
    
    # Pre-compute masks for different constraint types (analogous to cvxpy logic)
    equality_mask = (lower_bounds == upper_bounds) & (lower_bounds != -np.inf) & (upper_bounds != np.inf)
    upper_mask = (upper_bounds != np.inf) & ~equality_mask
    lower_mask = (lower_bounds != -np.inf) & ~equality_mask
    
    print(f"Constraint analysis:")
    print(f"  - Equality constraints: {np.sum(equality_mask)}")
    print(f"  - Upper bound constraints: {np.sum(upper_mask)}")
    print(f"  - Lower bound constraints: {np.sum(lower_mask)}")
    
    # Create constraints based on bounds analysis
    for i in range(num_constraints):
        # Get the range of non-zeros for this constraint
        start_idx = offsets[i]
        end_idx = offsets[i + 1]
        
        # Build the linear expression for this constraint using proper LinearExpression construction
        from cuopt.linear_programming.problem import LinearExpression
        
        # Collect variables and coefficients for this constraint
        constraint_vars = []
        constraint_coeffs = []
        
        for j in range(start_idx, end_idx):
            var_idx = indices[j]
            coeff = values[j]
            constraint_vars.append(variables[var_idx])
            constraint_coeffs.append(coeff)
        
        # Create the LinearExpression properly
        if constraint_vars:
            expr = LinearExpression(constraint_vars, constraint_coeffs, 0.0)
        else:
            # Handle empty constraint (shouldn't happen in practice)
            expr = LinearExpression([], [], 0.0)
        
        # Add constraints based on bound analysis
        if equality_mask[i]:
            # Equality constraint: expr == bound
            prob.addConstraint(Constraint(expr, CType.EQ, lower_bounds[i]), name=f"C_{i}_eq")
        else:
            # Add upper bound constraint if finite upper bound
            if upper_mask[i]:
                prob.addConstraint(Constraint(expr, CType.LE, upper_bounds[i]), name=f"C_{i}_up")
            
            # Add lower bound constraint if finite lower bound  
            if lower_mask[i]:
                prob.addConstraint(Constraint(expr, CType.GE, lower_bounds[i]), name=f"C_{i}_low")
    
    # Set objective sense
    obj_sense = sense.MAXIMIZE if maximize else sense.MINIMIZE
    
    # Create objective expression using proper LinearExpression construction
    obj_vars = []
    obj_coeffs = []
    
    for i, var in enumerate(variables):
        if i < len(objective_data["coefficients"]):
            coeff = objective_data["coefficients"][i]
            if coeff != 0:
                obj_vars.append(var)
                obj_coeffs.append(coeff)
    
    # Get objective offset
    obj_offset = objective_data.get("offset", 0.0)
    
    # Create the objective LinearExpression
    if obj_vars:
        obj_expr = LinearExpression(obj_vars, obj_coeffs, obj_offset)
    else:
        # Handle case with no variables in objective (constant objective)
        obj_expr = LinearExpression([], [], obj_offset)
    
    prob.setObjective(obj_expr, sense=obj_sense)
    
    return prob


def solve_cuopt_json_example(json_file_path: str, time_limit: float = 60.0):
    """
    Complete example: read cuOpt JSON file and solve using the new Problem API.
    
    Parameters
    ----------
    json_file_path : str
        Path to the cuOpt JSON file
    time_limit : float
        Solver time limit in seconds
    """
    
    print(f"Reading cuOpt JSON file: {json_file_path}")
    
    # Create problem from JSON
    prob = create_problem_from_cuopt_json(json_file_path)
    
    print(f"Problem created:")
    print(f"  - Variables: {prob.NumVariables}")
    print(f"  - Constraints: {prob.NumConstraints}") 
    print(f"  - Non-zeros: {prob.NumNZs}")
    print(f"  - Problem type: {'MIP' if prob.IsMIP else 'LP'}")
    print(f"  - Objective sense: {'MAXIMIZE' if prob.ObjSense == sense.MAXIMIZE else 'MINIMIZE'}")
    
    # Configure solver settings
    settings = SolverSettings()
    settings.set_parameter("time_limit", time_limit)
    settings.set_parameter("log_to_console", True)
    settings.set_parameter("method", 0)
    settings.set_parameter("pdlp_solver_mode", 1)
    
    print(f"\nSolving with time limit: {time_limit} seconds...")
    
    # Solve the problem
    prob.solve(settings)
    print(f"SOLVE_END_TIME: {time.time()}")
    
    print(f"\nSolution found!")
    print(f"  - Status: {prob.Status.name}")
    print(f"  - Solve time: {prob.SolveTime:.3f} seconds")
    print(f"  - Objective value: {prob.ObjValue}")
    
    # Print variable values (first 10 variables only to avoid cluttering)
    print(f"\nVariable values (first 10):")
    for i, var in enumerate(prob.getVariables()[:10]):
        print(f"  {var.getVariableName()}: {var.getValue():.6f}")
    
    if prob.NumVariables > 10:
        print(f"  ... and {prob.NumVariables - 10} more variables")
    
    # Print constraint slacks (first 10 constraints only)
    if not prob.IsMIP:  # Slack is available for LP problems
        print(f"\nConstraint slacks (first 10):")
        for i, constr in enumerate(prob.getConstraints()[:10]):
            print(f"  {constr.getConstraintName()}: {constr.Slack:.6f}")
        
        if prob.NumConstraints > 10:
            print(f"  ... and {prob.NumConstraints - 10} more constraints")

    return prob


def create_example_cuopt_json(filename: str = "example_cuopt_problem.json"):
    """
    Create an example cuOpt JSON file for testing.
    
    This creates a simple MIP problem:
    maximize  5*x + 3*y
    subject to:
        2*x + 4*y >= 230
        3*x + 2*y <= 190
        x, y integer
        x >= 0, y >= 10, y <= 50
    """
    
    example_data = {
        "csr_constraint_matrix": {
            "offsets": [0, 2, 4],
            "indices": [0, 1, 0, 1], 
            "values": [2.0, 4.0, 3.0, 2.0]
        },
        "constraint_bounds": {
            "bounds": [230.0, 190.0],
            "upper_bounds": [230.0, 190.0],
            "lower_bounds": [230.0, 190.0],
            "types": ["G", "L"]
        },
        "objective_data": {
            "coefficients": [5.0, 3.0],
            "scalability_factor": 1.0,
            "offset": 0.0
        },
        "variable_bounds": {
            "upper_bounds": ["inf", 50.0],
            "lower_bounds": [0.0, 10.0]
        },
        "maximize": True,
        "variable_types": ["I", "I"],
        "variable_names": ["x", "y"]
    }
    
    with open(filename, 'w') as f:
        json.dump(example_data, f, indent=2)
    
    print(f"Created example cuOpt JSON file: {filename}")
    return filename


if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) != 2:
        print("Usage: python cuopt_json_to_python_api.py <json_file_path>")
        print("Example: python cuopt_json_to_python_api.py my_problem.json")
        sys.exit(1)
    
    json_file_path = sys.argv[1]
    
    # Check if file exists
    import os
    if not os.path.exists(json_file_path):
        print(f"ERROR: File '{json_file_path}' not found!")
        sys.exit(1)
    
    try:
        prob = solve_cuopt_json_example(json_file_path, time_limit=60.0)
        
        print("\n" + "="*60)
        print("SUCCESS: cuOpt JSON file successfully converted and solved!")
        print("="*60)
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc() 
