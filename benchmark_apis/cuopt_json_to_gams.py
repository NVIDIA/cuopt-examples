import json
import sys
import gamspy as gp
import numpy as np
from scipy.sparse import csr_matrix

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

def solve_cuopt_problem(json_filename):
    """Main function to solve cuopt JSON problem using gamspy."""
    
    # Set up GAMS environment (from transport.py)
    # Set log level 4 globally (log to both file and stdout)  
    gp.set_options({
        "SOLVER_VALIDATION": 0
    })
    
    # Create container with GAMS system directory
    m = gp.Container(system_directory="/home/tmckay/gams/gams50.4_linux_x64_64_sfx/")
    
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
    
    # Read and parse the JSON data
    print(f"Reading cuopt problem from {json_filename}...")
    data = read_cuopt_json(json_filename)
    
    # Parse the constraint matrix
    A = parse_csr_matrix(data["csr_constraint_matrix"])
    
    # Get problem data
    num_variables = A.shape[1]
    num_constraints = A.shape[0]
    
    # Objective coefficients
    obj_coeffs = data["objective_data"]["coefficients"]
    maximize = data["maximize"]
    
    print(f"Problem dimensions: {A.shape[0]} constraints, {A.shape[1]} variables")
    print(f"Constraint matrix non-zeros: {A.nnz}")
    print(f"Objective coefficients range: [{min(obj_coeffs):.3f}, {max(obj_coeffs):.3f}]")
    
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
    
    print(f"Constraint analysis (matching cuopt_json_to_api2.py):")
    print(f"  - Equality constraints: {np.sum(equality_mask)}")
    print(f"  - Upper bound constraints: {np.sum(upper_mask)}")
    print(f"  - Lower bound constraints: {np.sum(lower_mask)}")
    
    # Create gamspy sets for variables and constraints  
    var_set = gp.Set(m, name="vars", records=[f"x{i}" for i in range(num_variables)])
    con_set = gp.Set(m, name="cons", records=[f"c{i}" for i in range(num_constraints)])
    
    # Create variable bounds parameters
    var_lb_data = [(f"x{i}", var_lower[i]) for i in range(num_variables)]
    var_ub_data = [(f"x{i}", var_upper[i]) for i in range(num_variables)]
    
    var_lb_param = gp.Parameter(m, name="var_lb", domain=[var_set], records=var_lb_data)
    var_ub_param = gp.Parameter(m, name="var_ub", domain=[var_set], records=var_ub_data)
    
    # Create constraint matrix parameter
    matrix_data = []
    A_dense = A.toarray()
    for i in range(num_constraints):
        for j in range(num_variables):
            if abs(A_dense[i, j]) > 1e-10:  # Only include non-zero elements
                matrix_data.append((f"c{i}", f"x{j}", A_dense[i, j]))
    
    A_param = gp.Parameter(m, name="A", domain=[con_set, var_set], records=matrix_data)
    
    # We'll create constraint parameters dynamically based on constraint types
    # No need for separate RHS parameter since we use bounds directly
    
    # Create objective coefficients parameter
    obj_data = [(f"x{i}", obj_coeffs[i]) for i in range(num_variables)]
    obj_param = gp.Parameter(m, name="obj_coeff", domain=[var_set], records=obj_data)
    
    # Define variables with bounds
    x = gp.Variable(m, name="x", domain=[var_set], type="Free")
    
    # Set variable bounds
    x.lo[var_set] = var_lb_param[var_set]
    x.up[var_set] = var_ub_param[var_set]
    
    # Create constraint equations using the same logic as cuopt_json_to_api2.py
    # We create separate constraint lists for different types
    equality_constraints = []
    upper_constraints = []
    lower_constraints = []
    
    # Create constraints based on bounds analysis (matching cuopt_json_to_api2.py logic)
    for i in range(num_constraints):
        con_name = f"c{i}"
        
        # Build constraint expression: sum of A[i,j] * x[j] 
        lhs_expr = gp.Sum(var_set, A_param[con_name, var_set] * x[var_set])
        
        if equality_mask[i]:
            # Equality constraint: expr == lower_bounds[i] (same as upper_bounds[i])
            eq_constraint = gp.Equation(m, name=f"eq_constraint_{i}", domain=[])
            eq_constraint[...] = lhs_expr == lower_bounds[i]
            equality_constraints.append(eq_constraint)
        else:
            # Add upper bound constraint if finite upper bound
            if upper_mask[i]:
                up_constraint = gp.Equation(m, name=f"up_constraint_{i}", domain=[])
                up_constraint[...] = lhs_expr <= upper_bounds[i]
                upper_constraints.append(up_constraint)
            
            # Add lower bound constraint if finite lower bound
            if lower_mask[i]:
                low_constraint = gp.Equation(m, name=f"low_constraint_{i}", domain=[])
                low_constraint[...] = lhs_expr >= lower_bounds[i]
                lower_constraints.append(low_constraint)
    
    # Combine all constraints for the model
    all_constraints = equality_constraints + upper_constraints + lower_constraints
    print(f"Total constraint equations created: {len(all_constraints)}")
    print(f"Variable bounds: lower=[{min(var_lower):.3f}, {max(var_lower):.3f}], upper=[{min(var_upper):.3f}, {max(var_upper):.3f}]")
    
    # Define objective function
    objective_expr = gp.Sum(var_set, obj_param[var_set] * x[var_set])
    objective_expr += data["objective_data"]["offset"]  # Add offset if present
    
    # Create and solve the model
    sense = gp.Sense.MAX if maximize else gp.Sense.MIN
    model = gp.Model(m, name="cuopt_problem", equations=all_constraints,
                     problem="LP", sense=sense, objective=objective_expr)
    
    print(f"Solving {'maximization' if maximize else 'minimization'} problem with cuopt solver...")
    # Solve with cuopt solver (optfile is set globally via environment variable)
    model.solve("cuopt", output=sys.stdout)
    
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
        
    # Show model statistics
    print(f"\nModel Statistics:")
    print(f"  Problem type: {'Maximization' if maximize else 'Minimization'}")
    print(f"  Variables: {num_variables}")
    print(f"  Constraints: {num_constraints}")
    print(f"  Matrix non-zeros: {A.nnz}")
    
    if model.status != gp.ModelStatus.OptimalGlobal and model.status != gp.ModelStatus.OptimalLocal:
        print(f"\nWarning: Model status is {model.status}")
        print("This may indicate an issue with the problem formulation or solver configuration.")
    
    return model

if __name__ == "__main__":
    # Check for command line argument
    if len(sys.argv) != 2:
        print("Usage: python cuopt_solver.py <json_filename>")
        print("Example: python cuopt_solver.py afiro.json")
        sys.exit(1)
    
    json_filename = sys.argv[1]
    
    # Check if file exists
    import os
    if not os.path.exists(json_filename):
        print(f"Error: File '{json_filename}' not found.")
        sys.exit(1)
    
    # Solve the cuopt problem from JSON file
    try:
        model = solve_cuopt_problem(json_filename)
        print(f"\nProblem solved successfully from {json_filename}!")
    except Exception as e:
        print(f"Error solving problem: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
