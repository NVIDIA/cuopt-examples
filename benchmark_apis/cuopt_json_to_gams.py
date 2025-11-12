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

import json
import sys
import gamspy as gp
import numpy as np
from scipy.sparse import csr_matrix
import time
import argparse

def read_cuopt_json(filename):
    """Read and parse the cuopt JSON file."""
    with open(filename, 'r') as f:
        data = json.load(f)
    return data

def parse_csr_matrix(csr_data):
    """Convert CSR format data to scipy sparse matrix."""
    offsets = csr_data["offsets"]
    indices = csr_data["indices"] 
    values = csr_data["values"]
    
    # Determine matrix dimensions
    num_rows = len(offsets) - 1
    num_cols = max(indices) + 1 if indices else 0
    
    # Convert offsets to row pointers for scipy
    indptr = np.array(offsets)
    
    matrix = csr_matrix((values, indices, indptr), shape=(num_rows, num_cols))
    return matrix

def convert_bounds(bounds_list):
    """Convert bound strings to numeric values, handling 'ninf' and 'inf'."""
    converted = []
    for bound in bounds_list:
        if bound == "ninf":
            converted.append(-float('inf'))
        elif bound == "inf":  
            converted.append(float('inf'))
        else:
            converted.append(float(bound))
    return converted

def solve_cuopt_problem(json_filename, timing=False):
    """Main function to solve cuopt JSON problem using gamspy."""
    
    # Start overall timing  
    total_start_time = time.time()
    if timing:
        print(f"🕐 [T+{0.000:.3f}s] Starting cuOpt GAMS solver...")
    
    # Phase 1: GAMS Setup
    setup_start = time.time()
    # Set up GAMS environment (from transport.py)
    # Set log level 4 globally (log to both file and stdout)  
    gp.set_options({
        "SOLVER_VALIDATION": 0
    })
    
    # Create container with GAMS system directory
    m = gp.Container(system_directory="/home/tmckay/gams/gams50.4_linux_x64_64_sfx/")
    setup_time = time.time() - setup_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] GAMS setup completed ({setup_time:.3f}s)")
    
    # Example: Set cuopt solver options
    # You can create and use a cuopt option file
#    cuopt_options = {
#        "time_limit": 3600,        # Time limit in seconds
#        "presolve": 1,             # Enable presolve
#        "method": 1,               # Use PDLP method
#        "pdlp_solver_mode": 1,     # Use stable2 mode
#        "num_cpu_threads": 4,      # Number of CPU threads
#        "crossover": 1,            # Enable crossover to basic solution
#        "absolute_dual_tolerance": 1e-6,
#        "relative_dual_tolerance": 1e-6,
#        "mip_relative_gap": 1e-4   # For MIP problems
#    }
    
    # Write cuopt options to file
#    with open("cuopt.opt", "w") as f:
#        for option, value in cuopt_options.items():
#            f.write(f"{option} = {value}\n")
    
    # Phase 2: File Reading and JSON Parsing
    read_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Reading cuopt problem from {json_filename}...")
    data = read_cuopt_json(json_filename)
    print(f"PROBLEM_START {time.time()}")
    
    read_time = time.time() - read_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] JSON file read completed ({read_time:.3f}s)")
    
    # Phase 3: Matrix Parsing and Data Preprocessing
    matrix_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Parsing constraint matrix...")
    A = parse_csr_matrix(data["csr_constraint_matrix"])
    
    # Get problem data
    num_variables = A.shape[1]
    num_constraints = A.shape[0]
    
    # Objective coefficients
    obj_coeffs = data["objective_data"]["coefficients"]
    maximize = data["maximize"]
    
    matrix_time = time.time() - matrix_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Matrix parsing completed ({matrix_time:.3f}s)")
    print(f"Problem dimensions: {A.shape[0]} constraints, {A.shape[1]} variables")
    print(f"Constraint matrix non-zeros: {A.nnz}")
    print(f"Objective coefficients range: [{min(obj_coeffs):.3f}, {max(obj_coeffs):.3f}]")
    
    # Phase 4: Bounds Processing
    bounds_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Processing bounds...")
    
    # Variable bounds
    var_lower = convert_bounds(data["variable_bounds"]["lower_bounds"])
    var_upper = convert_bounds(data["variable_bounds"]["upper_bounds"])
    
    # Constraint bounds - use the same logic as cuopt_json_to_api2.py
    # Extract lower and upper bounds for constraints directly
    # Use only lower_bounds and upper_bounds, ignore constraint_bounds["bounds"]
    constraint_lower = convert_bounds(data["constraint_bounds"]["lower_bounds"])
    constraint_upper = convert_bounds(data["constraint_bounds"]["upper_bounds"])
    
    # Convert to numpy arrays for mask operations
    import numpy as np
    lower_bounds = np.array(constraint_lower)
    upper_bounds = np.array(constraint_upper)
    
    # Pre-compute masks for different constraint types (analogous to cvxpy logic)
    equality_mask = (lower_bounds == upper_bounds) & (lower_bounds != -np.inf) & (upper_bounds != np.inf)
    upper_mask = (upper_bounds != np.inf) & ~equality_mask
    lower_mask = (lower_bounds != -np.inf) & ~equality_mask
    
    bounds_time = time.time() - bounds_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Bounds processing completed ({bounds_time:.3f}s)")
    print(f"Constraint analysis (matching cuopt_json_to_api2.py):")
    print(f"  - Equality constraints: {np.sum(equality_mask)}")
    print(f"  - Upper bound constraints: {np.sum(upper_mask)}")
    print(f"  - Lower bound constraints: {np.sum(lower_mask)}")
    
    # Phase 5: GAMS Sets Creation
    sets_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating GAMS sets...")
    
    # Create gamspy sets for variables and constraints  
    var_set = gp.Set(m, name="vars", records=[f"x{i}" for i in range(num_variables)])
    con_set = gp.Set(m, name="cons", records=[f"c{i}" for i in range(num_constraints)])
    
    sets_time = time.time() - sets_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] GAMS sets created ({sets_time:.3f}s)")
    
    # Phase 6: Parameter Creation
    params_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating GAMS parameters...")
    
    # Create variable bounds parameters
    var_lb_data = [(f"x{i}", var_lower[i]) for i in range(num_variables)]
    var_ub_data = [(f"x{i}", var_upper[i]) for i in range(num_variables)]
    
    var_lb_param = gp.Parameter(m, name="var_lb", domain=[var_set], records=var_lb_data)
    var_ub_param = gp.Parameter(m, name="var_ub", domain=[var_set], records=var_ub_data)
    
    # Create constraint matrix parameter (POTENTIAL BOTTLENECK)
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Converting sparse matrix to dense format...")
    matrix_data_start = time.time()
    
    # Convert sparse matrix to dense - this could be slow for large matrices
    A_dense = A.toarray()
    dense_conversion_time = time.time() - matrix_data_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Dense conversion completed ({dense_conversion_time:.3f}s)")
    
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Building matrix parameter data...")
    matrix_data = []
    for i in range(num_constraints):
        for j in range(num_variables):
            if abs(A_dense[i, j]) > 1e-10:  # Only include non-zero elements
                matrix_data.append((f"c{i}", f"x{j}", A_dense[i, j]))
    
    matrix_build_time = time.time() - matrix_data_start - dense_conversion_time
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Matrix data built, {len(matrix_data)} non-zeros ({matrix_build_time:.3f}s)")
    
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating GAMS matrix parameter...")
    matrix_param_start = time.time()
    A_param = gp.Parameter(m, name="A", domain=[con_set, var_set], records=matrix_data)
    matrix_param_time = time.time() - matrix_param_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] GAMS matrix parameter created ({matrix_param_time:.3f}s)")
    
    # We'll create constraint parameters dynamically based on constraint types
    # No need for separate RHS parameter since we use bounds directly
    
    # Create objective coefficients parameter
    obj_data = [(f"x{i}", obj_coeffs[i]) for i in range(num_variables)]
    obj_param = gp.Parameter(m, name="obj_coeff", domain=[var_set], records=obj_data)
    
    params_time = time.time() - params_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] All parameters created ({params_time:.3f}s)")
    
    # Phase 7: Variable Creation
    vars_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating GAMS variables...")
    
    # Define variables with bounds
    x = gp.Variable(m, name="x", domain=[var_set], type="Free")
    
    # Set variable bounds
    x.lo[var_set] = var_lb_param[var_set]
    x.up[var_set] = var_ub_param[var_set]
    
    vars_time = time.time() - vars_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Variables created ({vars_time:.3f}s)")
    
    # Phase 8: Optimized Batch Constraint Creation (Fixed Domain Issues)
    constraints_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating constraint equations (OPTIMIZED BATCH MODE v2)...")
    
    # Create constraint type sets for batch operations
    eq_indices = [i for i in range(num_constraints) if equality_mask[i]]
    up_indices = [i for i in range(num_constraints) if not equality_mask[i] and upper_mask[i]]
    low_indices = [i for i in range(num_constraints) if not equality_mask[i] and lower_mask[i]]
    
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Constraint groups: {len(eq_indices)} equality, {len(up_indices)} upper, {len(low_indices)} lower")
    
    all_constraints = []
    
    # OPTIMIZATION 1: Batch create equality constraints using conditional sum
    if eq_indices:
        eq_batch_start = time.time()
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {len(eq_indices)} equality constraints...")
        
        # Create binary parameter to identify equality constraints
        eq_mask_data = [(f"c{i}", 1 if i in eq_indices else 0) for i in range(num_constraints)]
        eq_mask_param = gp.Parameter(m, name="eq_mask", domain=[con_set], records=eq_mask_data)
        
        # Create parameter for equality RHS values (0 for non-equality constraints)
        eq_rhs_data = [(f"c{i}", lower_bounds[i] if i in eq_indices else 0) for i in range(num_constraints)]
        eq_rhs_param = gp.Parameter(m, name="eq_rhs", domain=[con_set], records=eq_rhs_data)
        
        # Create batch equality constraints using conditional
        eq_constraints = gp.Equation(m, name="eq_constraints", domain=[con_set])
        eq_constraints[con_set].where[eq_mask_param[con_set] == 1] = (
            gp.Sum(var_set, A_param[con_set, var_set] * x[var_set]) == eq_rhs_param[con_set]
        )
        all_constraints.append(eq_constraints)
        
        eq_batch_time = time.time() - eq_batch_start
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Equality constraints created ({eq_batch_time:.3f}s)")
    
    # OPTIMIZATION 2: Batch create upper bound constraints
    if up_indices:
        up_batch_start = time.time()
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {len(up_indices)} upper bound constraints...")
        
        # Create binary parameter to identify upper bound constraints
        up_mask_data = [(f"c{i}", 1 if i in up_indices else 0) for i in range(num_constraints)]
        up_mask_param = gp.Parameter(m, name="up_mask", domain=[con_set], records=up_mask_data)
        
        # Create parameter for upper bound RHS values
        up_rhs_data = [(f"c{i}", upper_bounds[i] if i in up_indices else 0) for i in range(num_constraints)]
        up_rhs_param = gp.Parameter(m, name="up_rhs", domain=[con_set], records=up_rhs_data)
        
        # Create batch upper bound constraints using conditional
        up_constraints = gp.Equation(m, name="up_constraints", domain=[con_set])
        up_constraints[con_set].where[up_mask_param[con_set] == 1] = (
            gp.Sum(var_set, A_param[con_set, var_set] * x[var_set]) <= up_rhs_param[con_set]
        )
        all_constraints.append(up_constraints)
        
        up_batch_time = time.time() - up_batch_start
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Upper bound constraints created ({up_batch_time:.3f}s)")
    
    # OPTIMIZATION 3: Batch create lower bound constraints  
    if low_indices:
        low_batch_start = time.time()
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating {len(low_indices)} lower bound constraints...")
        
        # Create binary parameter to identify lower bound constraints
        low_mask_data = [(f"c{i}", 1 if i in low_indices else 0) for i in range(num_constraints)]
        low_mask_param = gp.Parameter(m, name="low_mask", domain=[con_set], records=low_mask_data)
        
        # Create parameter for lower bound RHS values
        low_rhs_data = [(f"c{i}", lower_bounds[i] if i in low_indices else 0) for i in range(num_constraints)]
        low_rhs_param = gp.Parameter(m, name="low_rhs", domain=[con_set], records=low_rhs_data)
        
        # Create batch lower bound constraints using conditional
        low_constraints = gp.Equation(m, name="low_constraints", domain=[con_set])
        low_constraints[con_set].where[low_mask_param[con_set] == 1] = (
            gp.Sum(var_set, A_param[con_set, var_set] * x[var_set]) >= low_rhs_param[con_set]
        )
        all_constraints.append(low_constraints)
        
        low_batch_time = time.time() - low_batch_start
        if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Lower bound constraints created ({low_batch_time:.3f}s)")
    
    constraints_time = time.time() - constraints_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] OPTIMIZED constraint equations created ({constraints_time:.3f}s)")
    print(f"Total constraint groups created: {len(all_constraints)} (instead of {num_constraints} individual)")
    print(f"Variable bounds: lower=[{min(var_lower):.3f}, {max(var_lower):.3f}], upper=[{min(var_upper):.3f}, {max(var_upper):.3f}]")
    
    # Phase 9: Model Creation and Objective
    model_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Creating model and objective...")
    
    # Define objective function
    objective_expr = gp.Sum(var_set, obj_param[var_set] * x[var_set])
    objective_expr += data["objective_data"]["offset"]  # Add offset if present
    
    # Create the model
    sense = gp.Sense.MAX if maximize else gp.Sense.MIN
    model = gp.Model(m, name="cuopt_problem", equations=all_constraints,
                     problem="LP", sense=sense, objective=objective_expr)
    
    model_time = time.time() - model_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Model created ({model_time:.3f}s)")
    
    # Phase 10: Solving (THE CRITICAL PHASE)
    solve_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Solving {'maximization' if maximize else 'minimization'} problem with cuopt solver...")
    # Solve with cuopt solver (optfile is set globally via environment variable)
    model.solve("cuopt", output=sys.stdout)
    print(f"SOLVE_END_TIME {time.time()}")
    
    solve_time = time.time() - solve_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Solving completed ({solve_time:.3f}s)")
    
    # Phase 11: Result Extraction
    results_start = time.time()
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Extracting results...")
    
    # Display results
    print(f"\nOptimal objective value: {model.objective_value}")
    print(f"Solver status: {model.status}")
    print("\nVariable values:")
    
    # Print variable values
    try:
        x_values = x.toDict()
        if x_values:
            print("Variable values:")
            for var_name, value in x_values.items():
                if abs(value) > 1e-8:  # Only show significant values
                    print(f"  {var_name}: {value:.6f}")
            
            # Count non-zero variables
            non_zero_count = sum(1 for v in x_values.values() if abs(v) > 1e-8)
            print(f"Non-zero variables: {non_zero_count} out of {len(x_values)}")
        else:
            print("No variable values available")
    except Exception as e:
        print(f"Error retrieving variable values: {e}")
    
    results_time = time.time() - results_start
    if timing: print(f"🕐 [T+{time.time() - total_start_time:.3f}s] Results extracted ({results_time:.3f}s)")
        
    # Show model statistics
    print(f"\nModel Statistics:")
    print(f"  Problem type: {'Maximization' if maximize else 'Minimization'}")
    print(f"  Variables: {num_variables}")
    print(f"  Constraints: {num_constraints}")
    print(f"  Matrix non-zeros: {A.nnz}")
    
    if model.status != gp.ModelStatus.OptimalGlobal and model.status != gp.ModelStatus.OptimalLocal:
        print(f"\nWarning: Model status is {model.status}")
        print("This may indicate an issue with the problem formulation or solver configuration.")
    
    # Final Timing Summary (conditional on quiet flag)
    total_time = time.time() - total_start_time
    if timing:
        print(f"\n" + "="*80)
        print(f"TIMING SUMMARY - Total Time: {total_time:.3f}s")
        print(f"="*80)
        print(f"Phase 1  - GAMS Setup:        {setup_time:8.3f}s ({setup_time/total_time*100:5.1f}%)")
        print(f"Phase 2  - JSON Reading:      {read_time:8.3f}s ({read_time/total_time*100:5.1f}%)")
        print(f"Phase 3  - Matrix Parsing:    {matrix_time:8.3f}s ({matrix_time/total_time*100:5.1f}%)")
        print(f"Phase 4  - Bounds Processing: {bounds_time:8.3f}s ({bounds_time/total_time*100:5.1f}%)")
        print(f"Phase 5  - GAMS Sets:         {sets_time:8.3f}s ({sets_time/total_time*100:5.1f}%)")
        print(f"Phase 6  - Parameters:        {params_time:8.3f}s ({params_time/total_time*100:5.1f}%)")
        print(f"         └─ Dense conversion:  {dense_conversion_time:8.3f}s ({dense_conversion_time/total_time*100:5.1f}%)")
        print(f"         └─ Matrix build:      {matrix_build_time:8.3f}s ({matrix_build_time/total_time*100:5.1f}%)")
        print(f"         └─ Matrix parameter:  {matrix_param_time:8.3f}s ({matrix_param_time/total_time*100:5.1f}%)")
        print(f"Phase 7  - Variables:         {vars_time:8.3f}s ({vars_time/total_time*100:5.1f}%)")
        print(f"Phase 8  - Constraints (OPT): {constraints_time:8.3f}s ({constraints_time/total_time*100:5.1f}%)")
        print(f"Phase 9  - Model Creation:    {model_time:8.3f}s ({model_time/total_time*100:5.1f}%)")
        print(f"Phase 10 - SOLVING:           {solve_time:8.3f}s ({solve_time/total_time*100:5.1f}%) ⭐")
        print(f"Phase 11 - Results:           {results_time:8.3f}s ({results_time/total_time*100:5.1f}%)")
        print(f"="*80)
    
        # Identify potential bottlenecks
        bottleneck_threshold = 0.10 * total_time  # 10% of total time
        print(f"BOTTLENECK ANALYSIS (phases >10% of total time):")
        bottlenecks = []
        if setup_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 GAMS Setup: {setup_time:.3f}s ({setup_time/total_time*100:.1f}%)")
        if params_time > bottleneck_threshold:
            bottlenecks.append(f"  🐌 Parameter Creation: {params_time:.3f}s ({params_time/total_time*100:.1f}%)")
            if dense_conversion_time > bottleneck_threshold/2:
                bottlenecks.append(f"    └─ Sparse→Dense conversion: {dense_conversion_time:.3f}s")
            if matrix_build_time > bottleneck_threshold/2:
                bottlenecks.append(f"    └─ Matrix data building: {matrix_build_time:.3f}s")
            if matrix_param_time > bottleneck_threshold/2:
                bottlenecks.append(f"    └─ GAMS parameter creation: {matrix_param_time:.3f}s")
        if constraints_time > bottleneck_threshold:
            bottlenecks.append(f"  🚀 OPTIMIZED Constraint Creation: {constraints_time:.3f}s ({constraints_time/total_time*100:.1f}%) [Batch Mode]")
        if solve_time > bottleneck_threshold:
            bottlenecks.append(f"  ⭐ Actual Solving: {solve_time:.3f}s ({solve_time/total_time*100:.1f}%) [Expected]")
        
        if not bottlenecks:
            print(f"  ✅ No significant bottlenecks detected (all phases <10%)")
        else:
            for bottleneck in bottlenecks:
                print(bottleneck)
        
        # Performance improvement analysis
        print(f"\nOPTIMIZATION STATUS:")
        if constraints_time < bottleneck_threshold:
            print(f"  🎉 SUCCESS: Constraint creation time reduced to {constraints_time:.3f}s ({constraints_time/total_time*100:.1f}%)")
            print(f"  🚀 BATCH MODE: Using {len(all_constraints)} constraint groups instead of {num_constraints} individual constraints")
        else:
            print(f"  ⚠️  Constraint creation still dominant: {constraints_time:.3f}s ({constraints_time/total_time*100:.1f}%)")
        print(f"  💡 Further optimization may be needed")
    
    return model

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Solve cuOpt problems using GAMS interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cuopt_json_to_gams.py problem.json                    # Normal output (no timing)
  python cuopt_json_to_gams.py problem.json --timing           # Show detailed timing analysis
        """
    )
    
    parser.add_argument('json_filename', help='JSON file containing the cuOpt problem')
    parser.add_argument('--timing', action='store_true', 
                       help='Show detailed timing breakdown for performance analysis')
    
    args = parser.parse_args()
    
    # Check if file exists
    import os
    if not os.path.exists(args.json_filename):
        print(f"Error: File '{args.json_filename}' not found.")
        sys.exit(1)
    
    # Solve the cuopt problem from JSON file
    try:
        overall_start = time.time()
        model = solve_cuopt_problem(args.json_filename, timing=args.timing)
        overall_time = time.time() - overall_start
        print(f"\nProblem solved successfully from {args.json_filename} in {overall_time:.3f}s!")
    except Exception as e:
        print(f"Error solving problem: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
