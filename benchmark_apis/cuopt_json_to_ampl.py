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
cuOpt LP JSON to AMPL Solver

This script reads a cuOpt JSON problem file and converts it to solve using AMPL.

The cuOpt JSON format contains:
- CSR constraint matrix (offsets, indices, values)  
- Constraint bounds with separate lower_bounds and upper_bounds arrays
- Objective coefficients
- Variable bounds and types
- Variable names

Usage: python cuopt_ampl_solver.py <json_file_path> [--solver SOLVER]
"""

import json
import sys
import os
import time
import argparse
from typing import Dict, Any, List, Optional

try:
    from amplpy import AMPL
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing required package: {e}")
    print("Make sure amplpy and NumPy are installed in your conda environment")
    sys.exit(1)

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

def sanitize_ampl_name(name: str) -> str:
    """
    Sanitize variable name to be AMPL-compatible.
    
    AMPL variable names must start with a letter or underscore, and can contain
    letters, digits, and underscores. Dots have special meaning in AMPL.
    """
    # Remove leading dots and replace remaining dots with underscores
    clean_name = name.lstrip('.')
    clean_name = clean_name.replace('.', '_')
    
    # If name starts with a digit, prefix with underscore
    if clean_name and clean_name[0].isdigit():
        clean_name = '_' + clean_name
    
    # If name is empty or invalid, create a default name
    if not clean_name or not clean_name.replace('_', '').replace('-', '').isalnum():
        clean_name = 'var'
    
    return clean_name

def create_ampl_model(problem_data: Dict[str, Any], verbose: bool = True) -> str:
    """
    Create AMPL model string from cuOpt JSON data.
    
    Parameters
    ----------
    problem_data : dict
        Parsed cuOpt JSON data
    verbose : bool
        Whether to print model creation progress
        
    Returns
    -------
    str
        AMPL model as string
    """
    # Extract data from JSON structure
    csr_matrix = problem_data["csr_constraint_matrix"]
    constraint_bounds = problem_data["constraint_bounds"] 
    objective_data = problem_data["objective_data"]
    variable_bounds = problem_data["variable_bounds"]
    variable_types = problem_data.get("variable_types", [])
    variable_names = problem_data.get("variable_names", [])
    maximize = problem_data.get("maximize", False)
    
    # Sanitize variable names for AMPL compatibility
    if variable_names:
        variable_names = [sanitize_ampl_name(name) for name in variable_names]
    
    num_vars = len(variable_bounds["lower_bounds"])
    num_constraints = len(constraint_bounds["lower_bounds"])
    
    if verbose:
        print(f"Creating AMPL model:")
        print(f"  - Variables: {num_vars}")
        print(f"  - Constraints: {num_constraints}")
        print(f"  - Objective sense: {'MAXIMIZE' if maximize else 'MINIMIZE'}")
    
    # Start building AMPL model
    model_lines = []
    model_lines.append("# Auto-generated AMPL model from cuOpt JSON")
    model_lines.append("")
    
    # Variable declarations
    model_lines.append("# Variable declarations")
    
    # Create variable names if not provided
    if not variable_names:
        variable_names = [f"x_{i}" for i in range(num_vars)]
    
    # Group variables by type for efficient declaration
    continuous_vars = []
    integer_vars = []
    
    for i in range(num_vars):
        var_name = variable_names[i] if i < len(variable_names) else f"x_{i}"
        lb = variable_bounds["lower_bounds"][i]
        ub = variable_bounds["upper_bounds"][i]
        
        # Handle infinity bounds for AMPL
        lb_str = str(lb) if lb != float('-inf') else ""
        ub_str = str(ub) if ub != float('inf') else ""
        
        # Determine variable type
        var_type = 'C'  # Default continuous
        if i < len(variable_types):
            vtype = variable_types[i]
            if isinstance(vtype, bytes):
                vtype = vtype.decode('utf-8')
            var_type = vtype
        
        # Build bounds string
        if lb_str and ub_str:
            bounds = f" >= {lb_str}, <= {ub_str}"
        elif lb_str:
            bounds = f" >= {lb_str}"
        elif ub_str:
            bounds = f" <= {ub_str}"
        else:
            bounds = ""
        
        if var_type == 'I':
            integer_vars.append((var_name, bounds))
        else:
            continuous_vars.append((var_name, bounds))
    
    # Declare continuous variables
    if continuous_vars:
        for var_name, bounds in continuous_vars:
            model_lines.append(f"var {var_name}{bounds};")
    
    # Declare integer variables  
    if integer_vars:
        for var_name, bounds in integer_vars:
            model_lines.append(f"var {var_name} integer{bounds};")
    
    model_lines.append("")
    
    # Objective function
    model_lines.append("# Objective function")
    obj_coeffs = objective_data["coefficients"]
    obj_offset = objective_data.get("offset", 0.0)
    
    obj_sense = "maximize" if maximize else "minimize"
    obj_terms = []
    
    for i in range(min(len(obj_coeffs), num_vars)):
        coeff = obj_coeffs[i]
        if coeff != 0:
            var_name = variable_names[i] if i < len(variable_names) else f"x_{i}"
            if coeff == 1:
                obj_terms.append(var_name)
            elif coeff == -1:
                obj_terms.append(f"-{var_name}")
            else:
                obj_terms.append(f"{coeff}*{var_name}")
    
    if obj_terms:
        obj_expr = " + ".join(obj_terms)
        if obj_offset != 0:
            obj_expr += f" + {obj_offset}"
    else:
        obj_expr = str(obj_offset) if obj_offset != 0 else "0"
    
    model_lines.append(f"{obj_sense} obj: {obj_expr};")
    model_lines.append("")
    
    # Constraints from CSR matrix
    model_lines.append("# Constraints")
    offsets = csr_matrix["offsets"]
    indices = csr_matrix["indices"] 
    values = csr_matrix["values"]
    
    lower_bounds = np.array(constraint_bounds["lower_bounds"])
    upper_bounds = np.array(constraint_bounds["upper_bounds"])
    
    # Pre-compute masks for different constraint types
    equality_mask = (lower_bounds == upper_bounds) & (lower_bounds != -np.inf) & (upper_bounds != np.inf)
    upper_mask = (upper_bounds != np.inf) & ~equality_mask
    lower_mask = (lower_bounds != -np.inf) & ~equality_mask
    
    constraint_count = 0
    
    for i in range(num_constraints):
        # Get the range of non-zeros for this constraint
        start_idx = offsets[i]
        end_idx = offsets[i + 1]
        
        # Build the linear expression for this constraint
        constraint_terms = []
        
        for j in range(start_idx, end_idx):
            var_idx = indices[j]
            coeff = values[j]
            if var_idx < num_vars:  # Safety check
                var_name = variable_names[var_idx] if var_idx < len(variable_names) else f"x_{var_idx}"
                if coeff == 1:
                    constraint_terms.append(var_name)
                elif coeff == -1:
                    constraint_terms.append(f"-{var_name}")
                else:
                    constraint_terms.append(f"{coeff}*{var_name}")
        
        if not constraint_terms:  # Skip empty constraints
            continue
            
        expr = " + ".join(constraint_terms)
        
        # Add constraints based on bound analysis
        if equality_mask[i]:
            # Equality constraint: expr == bound
            model_lines.append(f"subject to c{i}_eq: {expr} = {lower_bounds[i]};")
            constraint_count += 1
        else:
            # Add upper bound constraint if finite upper bound
            if upper_mask[i]:
                model_lines.append(f"subject to c{i}_up: {expr} <= {upper_bounds[i]};")
                constraint_count += 1
            
            # Add lower bound constraint if finite lower bound  
            if lower_mask[i]:
                model_lines.append(f"subject to c{i}_low: {expr} >= {lower_bounds[i]};")
                constraint_count += 1
    
    if verbose:
        print(f"Generated {constraint_count} AMPL constraints")
        print(f"  - Equality constraints: {np.sum(equality_mask)}")
        print(f"  - Upper bound constraints: {np.sum(upper_mask)}")
        print(f"  - Lower bound constraints: {np.sum(lower_mask)}")
    
    return "\n".join(model_lines)

def solve_cuopt_json_with_ampl(json_file_path: str, solver: Optional[str] = None, verbose: bool = True) -> Dict:
    """
    Read a cuOpt JSON file and solve using AMPL.
    
    Parameters
    ----------
    json_file_path : str
        Path to the cuOpt JSON file
    solver : str, optional
        AMPL solver to use (e.g., 'cuopt', 'gurobi', 'cplex', 'cbc')
    verbose : bool
        Whether to print detailed output
        
    Returns
    -------
    dict
        Results dictionary with solution information
    """
    
    if verbose:
        print(f"Reading cuOpt JSON file: {json_file_path}")
    
    # Read the JSON file
    try:
        with open(json_file_path, 'r') as f:
            problem_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to read JSON file: {e}")

    # Initialize AMPL
    ampl = AMPL()

    print(f"PROBLEM_START: {time.time()}")
    
    # Handle infinity values
    problem_data = handle_infinity_values(problem_data)
    
    start_time = time.time()
    
    # Create AMPL model
    model_str = create_ampl_model(problem_data, verbose)
    
    setup_time = time.time() - start_time
        
    try:
        if verbose:
            print(f"Model setup completed in {setup_time:.3f} seconds")
        
        # Load the model
        ampl.eval(model_str)
        
        # Set solver if specified
        if solver:
            if verbose:
                print(f"Setting solver to: {solver}")
            ampl.option['solver'] = solver
        else:
            if verbose:
                print("Using default AMPL solver")
        
        # Solve the problem
        solve_start = time.time()
        
        if verbose:
            print("Solving...")
        
        ampl.solve()
        print(f"SOLVE_END_TIME: {time.time()}")        
        solve_time = time.time() - solve_start
        total_time = time.time() - start_time
        
        # Extract results
        solve_result = ampl.get_value("solve_result")
        solve_message = ampl.get_value("solve_message") if ampl.get_parameter("solve_message").value() else "No message"
        
        # Get objective value
        try:
            objective_value = ampl.get_objective('obj').value()
        except:
            objective_value = None
        
        # Get variable values
        variable_values = {}
        try:
            for var in ampl.get_variables():
                var_data = ampl.get_variable(var)
                if var_data.value() is not None:
                    variable_values[var] = var_data.value()
        except:
            pass
        
        # Check for cuOpt solver licensing issues and extract real results
        cuopt_objective = None
        cuopt_status = None
        
        if solve_message and "CUOPT" in solve_message.upper():
            # Parse cuOpt solver message for real results
            # Expected format: "CUOPT 25.5.0: optimal; objective 1811.23654"
            import re
            
            # Extract cuOpt status
            cuopt_status_match = re.search(r'CUOPT.*?:\s*(\w+)', solve_message, re.IGNORECASE)
            if cuopt_status_match:
                cuopt_status_raw = cuopt_status_match.group(1).lower()
                if cuopt_status_raw in ['optimal', 'solved']:
                    cuopt_status = 'Optimal'
                elif cuopt_status_raw in ['infeasible']:
                    cuopt_status = 'Infeasible'
                elif cuopt_status_raw in ['unbounded']:
                    cuopt_status = 'Unbounded'
                else:
                    cuopt_status = cuopt_status_raw.title()
            
            # Extract cuOpt objective value
            cuopt_obj_match = re.search(r'objective\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', solve_message, re.IGNORECASE)
            if cuopt_obj_match:
                try:
                    cuopt_objective = float(cuopt_obj_match.group(1))
                except:
                    pass
        
        # Determine final status and objective - prefer cuOpt results if available
        if cuopt_status and cuopt_objective is not None:
            # Use cuOpt results (more reliable when licensing issues occur)
            status = cuopt_status
            if cuopt_status == 'Optimal':
                objective_value = cuopt_objective
            if verbose:
                print(f"  - Using cuOpt solver results (bypassing AMPL licensing issues)")
        else:
            # Fall back to AMPL results
            if solve_result in ['solved', 'optimal']:
                status = 'Optimal'
            elif solve_result in ['infeasible']:
                status = 'Infeasible'
            elif solve_result in ['unbounded']:
                status = 'Unbounded'
            else:
                status = solve_result if solve_result else 'failure'
        
        results = {
            'status': status,
            'solve_result': solve_result,
            'solve_message': solve_message,
            'objective_value': objective_value,
            'solve_time': solve_time,
            'setup_time': setup_time,
            'total_time': total_time,
            'variable_values': variable_values,
            'solver_used': ampl.option['solver']
        }
        
        if verbose:
            print(f"\nSolution Results:")
            print(f"  - Status: {status}")
            print(f"  - Solve result: {solve_result}")
            print(f"  - Solver used: {ampl.option['solver']}")
            print(f"  - Solve time: {solve_time:.3f} seconds")
            print(f"  - Setup time: {setup_time:.3f} seconds") 
            print(f"  - Total time: {total_time:.3f} seconds")
            
            if objective_value is not None:
                print(f"  - Objective value: {objective_value}")
                
                # Print first few variable values
                if variable_values:
                    print(f"\nVariable values (first 10):")
                    count = 0
                    for name, value in list(variable_values.items())[:10]:
                        if abs(value) > 1e-6:  # Only show non-zero values
                            print(f"  {name}: {value}")
                            count += 1
                    
                    non_zero_count = sum(1 for v in variable_values.values() if abs(v) > 1e-6)
                    print(f"  ({non_zero_count} variables have non-zero values)")
            else:
                print("  - No solution found")
            
            if solve_message and solve_message != "No message":
                print(f"  - Message: {solve_message}")
        
        return results
        
    finally:
        ampl.close()

def list_available_solvers() -> List[str]:
    """
    List available AMPL solvers.
    
    Returns
    -------
    list
        List of available solver names
    """
    try:
        ampl = AMPL()
        try:
            # Try to get available solvers
            # This may not work in all AMPL installations
            ampl.eval("option solver;")
            current_solver = ampl.option['solver']
            
            # Common AMPL solvers
            common_solvers = [
                'cuopt', 'gurobi', 'cplex', 'cbc', 'ipopt', 'minos', 
                'snopt', 'knitro', 'baron', 'couenne', 'bonmin'
            ]
            
            available = [current_solver] if current_solver else []
            
            # Test which solvers are available
            for solver in common_solvers:
                try:
                    ampl.option['solver'] = solver
                    # If no error, solver is available
                    if solver not in available:
                        available.append(solver)
                except:
                    pass
            
            return available
        finally:
            ampl.close()
    except:
        return ['default']

def main():
    """Main function with command line interface."""
    
    parser = argparse.ArgumentParser(
        description='Solve cuOpt LP JSON files using AMPL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cuopt_ampl_solver.py problem.json                    # Use default solver
  python cuopt_ampl_solver.py problem.json --solver cuopt     # Use cuOpt solver
  python cuopt_ampl_solver.py problem.json --solver gurobi    # Use Gurobi
  python cuopt_ampl_solver.py problem.json --quiet            # Minimal output
  python cuopt_ampl_solver.py --list-solvers                  # List available solvers

Common AMPL solvers (if installed):
  cuopt, gurobi, cplex, cbc, ipopt, minos, snopt, knitro
        """
    )
    
    parser.add_argument(
        'json_file',
        nargs='?',
        help='cuOpt LP JSON file to solve'
    )
    
    parser.add_argument(
        '--solver', '-s',
        type=str,
        default='cuopt',
        help='AMPL solver to use (e.g., cuopt, gurobi, cplex, cbc). Default is cuopt.'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output - only show final results'
    )
    
    parser.add_argument(
        '--list-solvers',
        action='store_true',
        help='List available AMPL solvers and exit'
    )
    
    args = parser.parse_args()
    
    # List solvers if requested
    if args.list_solvers:
        print("Available AMPL solvers:")
        try:
            solvers = list_available_solvers()
            for solver in solvers:
                print(f"  - {solver}")
        except Exception as e:
            print(f"Error listing solvers: {e}")
        sys.exit(0)
    
    # Check if file is provided
    if not args.json_file:
        print("ERROR: JSON file argument is required")
        parser.print_help()
        sys.exit(1)
    
    # Check if file exists
    if not os.path.exists(args.json_file):
        print(f"ERROR: File '{args.json_file}' not found!")
        sys.exit(1)
    
    try:
        results = solve_cuopt_json_with_ampl(
            args.json_file, 
            solver=args.solver,
            verbose=not args.quiet
        )
        
        if args.quiet:
            # Minimal output for scripting
            print(f"Status: {results['status']}")
            if results['objective_value'] is not None:
                print(f"Objective: {results['objective_value']}")
            print(f"Time: {results['solve_time']:.6f}")
        
        # Exit code based on solution status
        if results['status'] == 'Optimal':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        if not args.quiet:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 
