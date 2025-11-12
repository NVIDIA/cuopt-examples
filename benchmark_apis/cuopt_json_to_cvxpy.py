# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

#!/usr/bin/env python

import argparse
import json
import sys
import cvxpy as cp
import numpy as np
from scipy import sparse
import pickle

import time

def process_bounds(bounds_array, inf_str='inf'):
    """Efficiently process bounds array whether it's list or numpy array."""
    if isinstance(bounds_array, np.ndarray):
        # If already numpy array, just replace strings with inf values
        if bounds_array.dtype.kind in {'U', 'S'}:  # if string array
            result = np.full_like(bounds_array, np.inf, dtype=float)
            ninf_mask = bounds_array == 'ninf'
            inf_mask = bounds_array == 'inf'
            result[ninf_mask] = -np.inf
            result[~(ninf_mask | inf_mask)] = bounds_array[~(ninf_mask | inf_mask)].astype(float)
            return result
        return bounds_array
    else:
        # If list, convert directly to float array
        return np.array([float('-inf') if x == 'ninf' else 
                        float('inf') if x == 'inf' else float(x) 
                        for x in bounds_array])

def create_variables(var_types, var_lb=None, var_ub=None):
    # Check if all types are the same
    if all(t == 'C' for t in var_types):
        # All continuous - create in one call
        if var_lb is not None and var_ub is not None:
            # CVXPY expects bounds as [lower_bounds, upper_bounds]
            bounds = [var_lb, var_ub]
            return cp.Variable(len(var_types), name='x', bounds=bounds)
        else:
            return cp.Variable(len(var_types), name='x')
    elif all(t == 'I' for t in var_types):
        # All integer - create in one call
        if var_lb is not None and var_ub is not None:
            # CVXPY expects bounds as [lower_bounds, upper_bounds]
            bounds = [var_lb, var_ub]
            return cp.Variable(len(var_types), integer=True, name='x', bounds=bounds)
        else:
            return cp.Variable(len(var_types), integer=True, name='x')
    else:
        # Mixed types - create individually
        variables = []
        for i, var_type in enumerate(var_types):
            if var_lb is not None and var_ub is not None:
                bounds = [var_lb[i], var_ub[i]]
            else:
                bounds = None
                
            if var_type == 'C':
                var = cp.Variable(name=f'x_{i}', bounds=bounds)
            elif var_type == 'I':
                var = cp.Variable(integer=True, name=f'x_{i}', bounds=bounds)
            else:
                raise ValueError(f"Unknown variable type: {var_type}")
            variables.append(var)
        return variables
    
def solve_lp_from_dict(problem_dict, solver, matrix_variable_bounds, solver_mode, solver_method, verbose, solver_verbose, timing=False):
    """Create and solve LP from dictionary representation."""

    # Start overall timing
    total_start_time = time.time()
    if timing:
        print(f"🕐 [T+{0.000:.3f}s] Starting CVXPY cuOpt solver...")
    
    # Phase 1: Problem Analysis
    analysis_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Analyzing problem dimensions...")
    
    n_variables = len(problem_dict['variable_types'])
    n_constraints = len(problem_dict['constraint_bounds']['lower_bounds'])
    
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Problem: {n_variables} variables, {n_constraints} constraints")
    
    analysis_time = time.time() - analysis_start
    
    # Phase 2: Variable Bounds Processing
    bounds_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Processing variable bounds...")
    
    var_lb = process_bounds(problem_dict['variable_bounds']['lower_bounds'])
    var_ub = process_bounds(problem_dict['variable_bounds']['upper_bounds'])
    
    bounds_time = time.time() - bounds_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Variable bounds processed ({bounds_time:.3f}s)")
    
    # Phase 3: Variable Creation
    vars_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {n_variables} variables...")
    
    if not matrix_variable_bounds:
        x = create_variables(problem_dict['variable_types'],
                             var_lb,
                             var_ub)
    else:
        x = create_variables(problem_dict['variable_types'])
    
    vars_time = time.time() - vars_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Variable creation completed ({vars_time:.3f}s)")

    # Phase 4: Objective Setup
    obj_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Setting up objective function...")
    
    obj_coeffs = (np.array(problem_dict['objective_data']['coefficients']) 
                 if not isinstance(problem_dict['objective_data']['coefficients'], np.ndarray)
                 else problem_dict['objective_data']['coefficients'])
    obj_offset = problem_dict['objective_data']['offset']
    objective = (cp.Minimize if not problem_dict['maximize'] else cp.Maximize)(obj_coeffs @ x + obj_offset)
    
    obj_time = time.time() - obj_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Objective setup completed ({obj_time:.3f}s)")

    # Phase 5: Constraint Matrix Creation
    matrix_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating constraint matrix...")
    
    A = sparse.csr_matrix(
        (problem_dict['csr_constraint_matrix']['values'],
         problem_dict['csr_constraint_matrix']['indices'],
         problem_dict['csr_constraint_matrix']['offsets']),
        shape=(n_constraints, n_variables)
    )
    
    matrix_time = time.time() - matrix_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint matrix created ({matrix_time:.3f}s)")
    
    # Phase 6: Constraint Bounds Processing
    cbounds_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Processing constraint bounds...")
    
    lower_bounds = process_bounds(problem_dict['constraint_bounds']['lower_bounds'])
    upper_bounds = process_bounds(problem_dict['constraint_bounds']['upper_bounds'])
    
    cbounds_time = time.time() - cbounds_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint bounds processed ({cbounds_time:.3f}s)")
    # Phase 7: Constraint Creation (POTENTIAL BOTTLENECK)
    constraints_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating constraints...")
    
    constraints = []
    
    # Pre-compute masks for different constraint types
    equality_mask = (lower_bounds == upper_bounds) & (lower_bounds != -np.inf) & (upper_bounds != np.inf)
    upper_mask = (upper_bounds != np.inf) & ~equality_mask
    lower_mask = (lower_bounds != -np.inf) & ~equality_mask
    
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint analysis: {np.sum(equality_mask)} equality, {np.sum(upper_mask)} upper, {np.sum(lower_mask)} lower")
    
    # Check if x is a list (mixed variable types) or single variable
    if isinstance(x, list):
        # Handle mixed variable types - create constraints manually
        for i in range(n_constraints):
            if equality_mask[i]:
                row = A[i, :]
                expr = sum(row[0, j] * x[j] for j in row.indices)
                constraints.append(expr == lower_bounds[i])
            else:
                if upper_mask[i]:
                    row = A[i, :]
                    expr = sum(row[0, j] * x[j] for j in row.indices)
                    constraints.append(expr <= upper_bounds[i])
                if lower_mask[i]:
                    row = A[i, :]
                    expr = sum(row[0, j] * x[j] for j in row.indices)
                    constraints.append(expr >= lower_bounds[i])
    else:
        # Handle uniform variable types - use vectorized operations where possible
        if np.any(equality_mask):
            eq_indices = np.where(equality_mask)[0]
            for i in eq_indices:
                constraints.append(A[i, :] @ x == lower_bounds[i])
        
        if np.any(upper_mask):
            up_indices = np.where(upper_mask)[0]
            constraints.append(A[up_indices, :] @ x <= upper_bounds[up_indices])
        
        if np.any(lower_mask):
            low_indices = np.where(lower_mask)[0]
            constraints.append(A[low_indices, :] @ x >= lower_bounds[low_indices])

    constraints_time = time.time() - constraints_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint creation completed ({constraints_time:.3f}s)")
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Created {len(constraints)} constraint groups")

    # Phase 8: Variable Bounds Constraints (if applicable)
    vbounds_start = time.time()
    if matrix_variable_bounds:
        if timing:
            print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Adding variable bounds as constraints...")
    else:
        if timing:
            print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Skipping variable bounds (included in variable definitions)")

    if matrix_variable_bounds:
        # Pre-compute masks for variable bounds
        var_eq_mask = (var_lb == var_ub) & (var_lb != -np.inf) & (var_ub != np.inf)
        var_lb_mask = (var_lb != -np.inf) & ~var_eq_mask
        var_ub_mask = (var_ub != np.inf) & ~var_eq_mask
        
        # Add equality constraints for variables
        if np.any(var_eq_mask):
            eq_indices = np.where(var_eq_mask)[0]
            for i in eq_indices:
                constraints.append(x[i] == var_lb[i])
        
        # Add bound constraints
        if isinstance(x, list):
            # Mixed variable types - individual constraints
            if np.any(var_lb_mask):
                lb_indices = np.where(var_lb_mask)[0]
                for i in lb_indices:
                    constraints.append(x[i] >= var_lb[i])
            if np.any(var_ub_mask):
                ub_indices = np.where(var_ub_mask)[0]
                for i in ub_indices:
                    constraints.append(x[i] <= var_ub[i])
        else:
            # Uniform variable types - vectorized
            if np.any(var_lb_mask):
                constraints.append(x[var_lb_mask] >= var_lb[var_lb_mask])
            if np.any(var_ub_mask):
                constraints.append(x[var_ub_mask] <= var_ub[var_ub_mask])
    
    vbounds_time = time.time() - vbounds_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Variable bounds processing completed ({vbounds_time:.3f}s)")
            
    # Phase 9: Problem Setup
    problem_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating CVXPY problem...")
    
    prob = cp.Problem(objective, constraints)
    
    problem_time = time.time() - problem_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Problem creation completed ({problem_time:.3f}s)")
    
    # Phase 10: Solving
    solve_start = time.time()
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Starting solver...")
    
    for i in range(1):
        if solver == "CUOPT":
            try: 
                result = prob.solve(solver=solver,
                                    verbose=verbose,
                                    solver_verbose=verbose or solver_verbose,
                                    pdlp_solver_mode=solver_mode,
                                    solver_method=solver_method)
            except Exception:
                import traceback
                traceback.print_exc()
        else:
            try:
                result = prob.solve(verbose=verbose,
                                    solver_verbose=verbose or solver_verbose)
            except Exception:
                pass
    print(f"SOLVE_END_TIME: {time.time()}")

    solve_time = time.time() - solve_start
    if timing:
        print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Solving completed ({solve_time:.3f}s)")

    # Final Timing Summary
    total_time = time.time() - total_start_time
    if timing:
        print(f"\n" + "="*80)
        print(f"CVXPY TIMING SUMMARY - Total Time: {total_time:.3f}s")
        print(f"="*80)
        print(f"Phase 1  - Problem Analysis:      {analysis_time:8.3f}s ({analysis_time/total_time*100:5.1f}%)")
        print(f"Phase 2  - Variable Bounds:       {bounds_time:8.3f}s ({bounds_time/total_time*100:5.1f}%)")
        print(f"Phase 3  - Variable Creation:     {vars_time:8.3f}s ({vars_time/total_time*100:5.1f}%)")
        print(f"Phase 4  - Objective Setup:       {obj_time:8.3f}s ({obj_time/total_time*100:5.1f}%)")
        print(f"Phase 5  - Matrix Creation:       {matrix_time:8.3f}s ({matrix_time/total_time*100:5.1f}%)")
        print(f"Phase 6  - Constraint Bounds:     {cbounds_time:8.3f}s ({cbounds_time/total_time*100:5.1f}%)")
        print(f"Phase 7  - Constraints:           {constraints_time:8.3f}s ({constraints_time/total_time*100:5.1f}%)")
        print(f"Phase 8  - Variable Bound Constr: {vbounds_time:8.3f}s ({vbounds_time/total_time*100:5.1f}%)")
        print(f"Phase 9  - Problem Setup:         {problem_time:8.3f}s ({problem_time/total_time*100:5.1f}%)")
        print(f"Phase 10 - SOLVING:               {solve_time:8.3f}s ({solve_time/total_time*100:5.1f}%) ⭐")
        print(f"="*80)
        
        # Identify potential bottlenecks
        bottleneck_threshold = 0.10 * total_time  # 10% of total time
        print(f"BOTTLENECK ANALYSIS (phases >10% of total time):")
        bottlenecks = []
        if vars_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Variable Creation: {vars_time:.3f}s ({vars_time/total_time*100:.1f}%)")
        if constraints_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Constraint Creation: {constraints_time:.3f}s ({constraints_time/total_time*100:.1f}%) [POTENTIAL OPTIMIZATION TARGET]")
        if vbounds_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Variable Bounds Constraints: {vbounds_time:.3f}s ({vbounds_time/total_time*100:.1f}%)")
        if solve_time > bottleneck_threshold:
            bottlenecks.append(f"  ⭐ Actual Solving: {solve_time:.3f}s ({solve_time/total_time*100:.1f}%) [Expected]")
        
        if not bottlenecks:
            print(f"  ✅ No significant bottlenecks detected (all phases <10%)")
        else:
            for bottleneck in bottlenecks:
                print(bottleneck)
        
        print(f"\nOPTIMIZATION OPPORTUNITIES:")
        if constraints_time > bottleneck_threshold:
            print(f"  🎯 Constraint creation loop in {'mixed variable' if isinstance(x, list) else 'uniform variable'} mode")
            print(f"  💡 Consider vectorized constraint creation or batch operations")
        elif vars_time > bottleneck_threshold:
            print(f"  🎯 Variable creation may benefit from optimization")
        else:
            print(f"  ✅ Performance looks good - no obvious optimization targets")

    return prob, x

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process LP file with solver options.')
    
    # Required FILE argument
    parser.add_argument('file', metavar='FILE', type=str,
                       help='cuopt LP json file')
    
    # Optional solver argument
    parser.add_argument('-s', '--solver', type=str, default='CUOPT',
                       help='solver to use (default: CUOPT)')

    parser.add_argument('--matrix_variable_bounds', action="store_true", default=False,
                        help='Add variable bounds to the constraint matrix instead of via bounded variables. '
                        'If not set, bounds are declared on the variables and the cvxpy API is used to pass '
                        'variable bounds to the solver. Default is False.')

    parser.add_argument('--verbose', action='store_true', default=False,
                        help='Set the verbose option for both cvxpy itself and the solver. Default is False.')

    parser.add_argument('--solver_verbose', action='store_true', default=False,
                        help='Set the verbose option for the solver only. Default is False.')
    
    parser.add_argument('--timing', action='store_true', default=False,
                        help='Show detailed timing breakdown for performance analysis. Default is False.')
    
    # 0 Stable1
    # 1 Stable2
    # 2 Methodical1
    # 3 Fast1
    parser.add_argument('-m', "--solver_mode", type=str, default="Stable2",
                        help='PDLP solver mode for CUOPT (Stable1, Stable2, Methodical1, Fast1). Default is Stable2.')
                        
    # 0 concurrent
    # 1 PDLP
    # 2 DualSimplex
    parser.add_argument('-e', "--solver_method", type=str, default="concurrent",
                        help='solver method for CUOPT (concurrent, PDLP, DualSimplex). Default is concurrent.')    
    args = parser.parse_args()    
    
    # Read problem from JSON file
    if args.file.endswith(".pickle"):
        import pickle
        with open(args.file, 'rb') as f:
            problem_dict = pickle.load(f)
    else:            
        with open(args.file, "r") as f:
            problem_dict = json.load(f)

    print(f"PROBLEM_START: {time.time()}")
    # Solve problem
    start_time = time.time()
    try:
        prob, x = solve_lp_from_dict(problem_dict,
                                     args.solver,
                                     args.matrix_variable_bounds,
                                     args.solver_mode,
                                     args.solver_method,
                                     args.verbose,
                                     args.solver_verbose,
                                     args.timing)
    except Exception:
        import traceback
        traceback.print_exc()
 
    # Print results
    print('Status:', prob.status)
    print('Optimal value:', prob.value)
 
    # Handle solution printing for both uniform and mixed variable types
    if isinstance(x, list):
        # Mixed variable types - extract only non-zero values
        solution = [(i, var.value) for i, var in enumerate(x) if var.value is not None and abs(var.value) > 1e-10]
        print('Solution (non-zero variables):', solution)
    else:
        # Uniform variable types - single variable
        print('Solution:', x.value)

