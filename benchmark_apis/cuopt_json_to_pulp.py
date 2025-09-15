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
cuOpt LP JSON to PuLP Solver

This script reads a cuOpt JSON problem file and converts it to solve using PuLP.

The cuOpt JSON format contains:
- CSR constraint matrix (offsets, indices, values)  
- Constraint bounds with separate lower_bounds and upper_bounds arrays
- Objective coefficients
- Variable bounds and types
- Variable names

Usage: python cuopt_pulp_solver.py <json_file_path>
"""

import json
import sys
import os
import time
import argparse
from typing import Dict, Any, List, Optional

try:
    import pulp
    import numpy as np
except ImportError as e:
    print(f"ERROR: Missing required package: {e}")
    print("Make sure PuLP and NumPy are installed in your conda environment")
    sys.exit(1)

def handle_infinity_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert string representations of infinity back to float values.
    
    cuOpt JSON files may contain "inf", "ninf", "-inf", or null strings that need to be 
    converted back to float('inf') and float('-inf').
    """
    def transform_list(lst):
        result = []
        for x in lst:
            if x == "inf" or x == "infinity":
                result.append(float('inf'))
            elif x == "ninf" or x == "-inf" or x == "-infinity":
                result.append(float('-inf'))
            elif x is None:
                # Handle null values - context dependent
                result.append(None)
            else:
                result.append(x)
        return result
    
    def transform_recursive(obj):
        if isinstance(obj, dict):
            return {k: transform_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return transform_list(obj)
        else:
            return obj
    
    return transform_recursive(data)

def solve_cuopt_json_with_pulp(json_file_path: str, solver_name: Optional[str] = None, verbose: bool = True, timing: bool = False) -> Dict:
    """
    Read a cuOpt JSON file and solve using PuLP.
    
    Parameters
    ----------
    json_file_path : str
        Path to the cuOpt JSON file
    solver_name : str, optional
        PuLP solver to use (e.g., 'PULP_CBC_CMD', 'GUROBI_CMD', 'CPLEX_CMD')
    verbose : bool
        Whether to print detailed output
    timing : bool
        Whether to show detailed timing analysis
        
    Returns
    -------
    dict
        Results dictionary with solution information
    """
    
    # Start overall timing
    total_start_time = time.time()
    if timing:
        print(f"🕐 [T+{0.000:.3f}s] Starting PuLP cuOpt solver...")
    
    if verbose:
        print(f"Reading cuOpt JSON file: {json_file_path}")
    
    # Phase 1: JSON Reading
    read_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Reading JSON file...")
    
    try:
        with open(json_file_path, 'r') as f:
            problem_data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to read JSON file: {e}")

    print(f"PROBLEM_START: {time.time()}")
    
    read_time = time.time() - read_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] JSON reading completed ({read_time:.3f}s)")
    
    # Phase 2: Data Preprocessing
    preprocess_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Processing infinity values...")
    
    problem_data = handle_infinity_values(problem_data)
    
    preprocess_time = time.time() - preprocess_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Data preprocessing completed ({preprocess_time:.3f}s)")
    
    # Extract data from JSON structure
    csr_matrix = problem_data["csr_constraint_matrix"]
    constraint_bounds = problem_data["constraint_bounds"] 
    objective_data = problem_data["objective_data"]
    variable_bounds = problem_data["variable_bounds"]
    variable_types = problem_data.get("variable_types", [])
    variable_names = problem_data.get("variable_names", [])
    maximize = problem_data.get("maximize", False)
    
    if verbose:
        print(f"Problem dimensions:")
        print(f"  - Variables: {len(variable_bounds['lower_bounds'])}")
        print(f"  - Constraints: {len(constraint_bounds['lower_bounds'])}")
        print(f"  - Objective sense: {'MAXIMIZE' if maximize else 'MINIMIZE'}")
    
    # Phase 3: Problem Setup
    setup_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating PuLP problem object...")
    
    prob_name = os.path.splitext(os.path.basename(json_file_path))[0]
    sense = pulp.LpMaximize if maximize else pulp.LpMinimize
    prob = pulp.LpProblem(prob_name, sense)
    
    problem_setup_time = time.time() - setup_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Problem setup completed ({problem_setup_time:.3f}s)")
    
    # Phase 4: Variable Creation
    vars_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {len(variable_bounds['lower_bounds'])} variables...")
    
    num_vars = len(variable_bounds["lower_bounds"])
    variables = []
    
    for i in range(num_vars):
        lb = variable_bounds["lower_bounds"][i]
        ub = variable_bounds["upper_bounds"][i]
        
        # Handle infinity bounds
        if lb == float('-inf'):
            lb = None
        if ub == float('inf'):
            ub = None
            
        # Determine variable type
        if i < len(variable_types):
            var_type = variable_types[i]
            if isinstance(var_type, bytes):
                var_type = var_type.decode('utf-8')
        else:
            var_type = 'C'  # Default to continuous
            
        cat = pulp.LpInteger if var_type == 'I' else pulp.LpContinuous
        
        # Variable name
        if i < len(variable_names):
            name = variable_names[i]
        else:
            name = f"x_{i}"
            
        var = pulp.LpVariable(name, lowBound=lb, upBound=ub, cat=cat)
        variables.append(var)
    
    vars_time = time.time() - vars_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Variable creation completed ({vars_time:.3f}s)")
    
    # Phase 5: Objective Setup
    obj_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Setting up objective function...")
    
    obj_coeffs = objective_data["coefficients"]
    obj_offset = objective_data.get("offset", 0.0)
    
    # Build objective expression
    obj_expr = pulp.lpSum([obj_coeffs[i] * variables[i] for i in range(len(obj_coeffs)) if i < len(variables)])
    if obj_offset != 0:
        obj_expr += obj_offset
    
    prob += obj_expr, "Objective"
    
    obj_time = time.time() - obj_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Objective setup completed ({obj_time:.3f}s)")
    
    # Phase 6: Constraint Preprocessing  
    bounds_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Processing constraint bounds...")
    
    offsets = csr_matrix["offsets"]
    indices = csr_matrix["indices"] 
    values = csr_matrix["values"]
    
    # Convert bounds to numpy arrays with proper handling of None values
    try:
        lower_bounds_list = constraint_bounds["lower_bounds"]
        upper_bounds_list = constraint_bounds["upper_bounds"]
        
        # Replace None with appropriate infinity values for constraint bounds
        processed_lower = [float('-inf') if x is None else x for x in lower_bounds_list]
        processed_upper = [float('inf') if x is None else x for x in upper_bounds_list]
        
        lower_bounds = np.array(processed_lower, dtype=float)
        upper_bounds = np.array(processed_upper, dtype=float)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Error processing constraint bounds: {e}. Check for unconverted infinity strings.")
    
    num_constraints = len(offsets) - 1
    
    # Pre-compute masks for different constraint types  
    # Use np.isinf() for more reliable infinity detection
    equality_mask = (lower_bounds == upper_bounds) & np.isfinite(lower_bounds) & np.isfinite(upper_bounds)
    upper_mask = np.isfinite(upper_bounds) & ~equality_mask
    lower_mask = np.isfinite(lower_bounds) & ~equality_mask
    
    bounds_time = time.time() - bounds_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint bounds processed ({bounds_time:.3f}s)")
    
    if verbose:
        print(f"Constraint analysis:")
        print(f"  - Equality constraints: {np.sum(equality_mask)}")
        print(f"  - Upper bound constraints: {np.sum(upper_mask)}")
        print(f"  - Lower bound constraints: {np.sum(lower_mask)}")
    
    # Phase 7: Constraint Creation (POTENTIAL BOTTLENECK)
    constraints_start = time.time() 
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {num_constraints} constraints...")
    
    constraint_count = 0
    
    for i in range(num_constraints):
        # Get the range of non-zeros for this constraint
        start_idx = offsets[i]
        end_idx = offsets[i + 1]
        
        # Build the linear expression for this constraint
        constraint_vars = []
        constraint_coeffs = []
        
        for j in range(start_idx, end_idx):
            var_idx = indices[j]
            coeff = values[j]
            if var_idx < len(variables):  # Safety check
                constraint_vars.append(variables[var_idx])
                constraint_coeffs.append(coeff)
        
        if not constraint_vars:  # Skip empty constraints
            continue
            
        expr = pulp.lpSum([constraint_coeffs[k] * constraint_vars[k] for k in range(len(constraint_vars))])
        
        # Add constraints based on bound analysis
        if equality_mask[i]:
            # Equality constraint: expr == bound
            prob += expr == lower_bounds[i], f"C_{i}_eq"
            constraint_count += 1
        else:
            # Add upper bound constraint if finite upper bound
            if upper_mask[i]:
                prob += expr <= upper_bounds[i], f"C_{i}_up"
                constraint_count += 1
            
            # Add lower bound constraint if finite lower bound  
            if lower_mask[i]:
                prob += expr >= lower_bounds[i], f"C_{i}_low"
                constraint_count += 1
    
    constraints_time = time.time() - constraints_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint creation completed ({constraints_time:.3f}s)")
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Created {constraint_count} constraint expressions")
    
    if verbose:
        print(f"Created {constraint_count} constraints")
    
    # Phase 8: Solving
    solve_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Starting solver...")
    
    if solver_name:
        if verbose:
            print(f"Solving with {solver_name}...")
        try:
            solver = getattr(pulp, solver_name)()
            prob.solve(solver)
        except AttributeError:
            if verbose:
                print(f"Warning: Solver {solver_name} not found, using default")
            prob.solve()
    else:
        if verbose:
            print("Solving with default PuLP solver...")
        prob.solve()
    print(f"SOLVE_END_TIME: {time.time()}")

    solve_time = time.time() - solve_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Solving completed ({solve_time:.3f}s)")
    
    # Phase 9: Result Extraction
    results_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Extracting results...")
    
    status = pulp.LpStatus[prob.status]
    objective_value = pulp.value(prob.objective) if prob.status == pulp.LpStatusOptimal else None
    
    # Get variable values
    variable_values = {}
    if prob.status == pulp.LpStatusOptimal:
        for var in variables:
            variable_values[var.name] = var.varValue
    
    results_time = time.time() - results_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Result extraction completed ({results_time:.3f}s)")
    
    # Final timing summary
    total_time = time.time() - total_start_time
    setup_time = total_time - solve_time  # For backwards compatibility
    
    if timing:
        print(f"\n" + "="*80)
        print(f"PULP TIMING SUMMARY - Total Time: {total_time:.3f}s")
        print(f"="*80)
        print(f"Phase 1  - JSON Reading:       {read_time:8.3f}s ({read_time/total_time*100:5.1f}%)")
        print(f"Phase 2  - Data Preprocessing: {preprocess_time:8.3f}s ({preprocess_time/total_time*100:5.1f}%)")
        print(f"Phase 3  - Problem Setup:      {problem_setup_time:8.3f}s ({problem_setup_time/total_time*100:5.1f}%)")
        print(f"Phase 4  - Variable Creation:  {vars_time:8.3f}s ({vars_time/total_time*100:5.1f}%)")
        print(f"Phase 5  - Objective Setup:    {obj_time:8.3f}s ({obj_time/total_time*100:5.1f}%)")
        print(f"Phase 6  - Bounds Processing:  {bounds_time:8.3f}s ({bounds_time/total_time*100:5.1f}%)")
        print(f"Phase 7  - Constraints:        {constraints_time:8.3f}s ({constraints_time/total_time*100:5.1f}%)")
        print(f"Phase 8  - SOLVING:            {solve_time:8.3f}s ({solve_time/total_time*100:5.1f}%) ⭐")
        print(f"Phase 9  - Results:            {results_time:8.3f}s ({results_time/total_time*100:5.1f}%)")
        print(f"="*80)
        
        # Identify potential bottlenecks
        bottleneck_threshold = 0.10 * total_time  # 10% of total time
        print(f"BOTTLENECK ANALYSIS (phases >10% of total time):")
        bottlenecks = []
        if vars_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Variable Creation: {vars_time:.3f}s ({vars_time/total_time*100:.1f}%)")
        if constraints_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Constraint Creation: {constraints_time:.3f}s ({constraints_time/total_time*100:.1f}%) [POTENTIAL OPTIMIZATION TARGET]")
        if solve_time > bottleneck_threshold:
            bottlenecks.append(f"  ⭐ Actual Solving: {solve_time:.3f}s ({solve_time/total_time*100:.1f}%) [Expected]")
        
        if not bottlenecks:
            print(f"  ✅ No significant bottlenecks detected (all phases <10%)")
        else:
            for bottleneck in bottlenecks:
                print(bottleneck)
        
        print(f"\nOPTIMIZATION OPPORTUNITIES:")
        if constraints_time > bottleneck_threshold:
            print(f"  🎯 Constraint creation loop may benefit from optimization")
            print(f"  💡 Consider batch constraint creation similar to GAMS optimization")
        else:
            print(f"  ✅ Performance looks good - no obvious optimization targets")
    
    results = {
        'status': status,
        'objective_value': objective_value,
        'solve_time': solve_time,
        'setup_time': setup_time,
        'total_time': total_time,
        'variable_values': variable_values,
        'num_variables': len(variables),
        'num_constraints': constraint_count,
        'problem_type': 'MIP' if any(var.cat == pulp.LpInteger for var in variables) else 'LP'
    }
    
    if verbose:
        print(f"\nSolution Results:")
        print(f"  - Status: {status}")
        print(f"  - Solve time: {solve_time:.3f} seconds")
        print(f"  - Setup time: {setup_time:.3f} seconds") 
        print(f"  - Total time: {total_time:.3f} seconds")
        
        if objective_value is not None:
            print(f"  - Objective value: {objective_value}")
            
            # Print first few variable values
            if variable_values:
                print(f"\nVariable values (first 10):")
                count = 0
                for name, value in variable_values.items():
                    if count >= 10:
                        break
                    if abs(value) > 1e-6:  # Only show non-zero values
                        print(f"  {name}: {value}")
                        count += 1
                
                non_zero_count = sum(1 for v in variable_values.values() if abs(v) > 1e-6)
                print(f"  ({non_zero_count} variables have non-zero values)")
        else:
            print("  - No solution found")
    
    return results

def main():
    """Main function with command line interface."""
    
    parser = argparse.ArgumentParser(
        description='Solve cuOpt LP JSON files using PuLP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cuopt_json_to_pulp.py problem.json                   # Use default solver
  python cuopt_json_to_pulp.py problem.json --solver GUROBI_CMD # Use specific solver
  python cuopt_json_to_pulp.py problem.json --quiet           # Minimal output
  python cuopt_json_to_pulp.py problem.json --timing          # Show detailed timing analysis

Available PuLP solvers (if installed):
  PULP_CBC_CMD, GUROBI_CMD, CPLEX_CMD, GLPK_CMD, COIN_CMD
        """
    )
    
    parser.add_argument(
        'json_file',
        help='cuOpt LP JSON file to solve'
    )
    
    parser.add_argument(
        '--solver', '-s',
        type=str,
        default='CUOPT',
        help='PuLP solver to use (e.g., PULP_CBC_CMD, GUROBI_CMD). Default is CUOPT.'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output - only show final results'
    )
    
    parser.add_argument(
        '--timing', '-t',
        action='store_true',
        help='Show detailed timing breakdown for performance analysis'
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.json_file):
        print(f"ERROR: File '{args.json_file}' not found!")
        sys.exit(1)
    
    try:
        results = solve_cuopt_json_with_pulp(
            args.json_file, 
            solver_name=args.solver,
            verbose=not args.quiet,
            timing=args.timing
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
