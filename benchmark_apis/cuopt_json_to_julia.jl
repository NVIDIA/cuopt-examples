#!/usr/bin/env julia

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
cuOpt LP JSON to Julia JuMP Solver

This script reads a cuOpt JSON problem file and converts it to solve using Julia's JuMP with cuOpt.

The cuOpt JSON format contains:
- CSR constraint matrix (offsets, indices, values)  
- Constraint bounds with separate lower_bounds and upper_bounds arrays
- Objective coefficients
- Variable bounds and types
- Variable names

Usage: julia cuopt_julia_solver.jl <json_file_path> [--quiet]
"""

using JSON
using JuMP
using cuOpt
using Printf

function handle_infinity_values(data)
    """
    Convert string representations of infinity back to float values.
    
    cuOpt JSON files may contain "inf" and "ninf" strings that need to be 
    converted back to Inf and -Inf.
    """
    function transform_value(x)
        if x == "inf"
            return Inf
        elseif x == "ninf"
            return -Inf
        elseif x === nothing
            # Handle null values from JSON - treat as unbounded (Inf for upper bounds, -Inf for lower bounds)
            # This will be context-dependent, but we'll return nothing and handle it in the calling code
            return nothing
        else
            return x
        end
    end
    
    function transform_recursive(obj)
        if isa(obj, Dict)
            return Dict(k => transform_recursive(v) for (k, v) in obj)
        elseif isa(obj, Array)
            return [transform_value(x) for x in obj]
        else
            return obj
        end
    end
    
    return transform_recursive(data)
end

function solve_cuopt_json_with_julia(json_file_path::String; verbose::Bool=true)
    """
    Read a cuOpt JSON file and solve using Julia JuMP with cuOpt.
    
    Parameters
    ----------
    json_file_path : String
        Path to the cuOpt JSON file
    verbose : Bool
        Whether to print detailed output
        
    Returns
    -------
    Dict
        Results dictionary with solution information
    """
    
    # Start timing
    script_start = time()
    timing_data = Dict{String, Float64}()
    
    if verbose
        println("Reading cuOpt JSON file: $json_file_path")
    end
    
    # Time JSON parsing
    json_start = time()
    try
        problem_data = JSON.parsefile(json_file_path)
    catch e
        error("Failed to read JSON file: $e")
    end
    timing_data["json_parse_time"] = time() - json_start
    
    # Time data processing
    processing_start = time()
    
    # Handle infinity values
    problem_data = handle_infinity_values(problem_data)
    
    # Extract data from JSON structure
    csr_matrix = problem_data["csr_constraint_matrix"]
    constraint_bounds = problem_data["constraint_bounds"] 
    objective_data = problem_data["objective_data"]
    variable_bounds = problem_data["variable_bounds"]
    variable_types = get(problem_data, "variable_types", String[])
    variable_names = get(problem_data, "variable_names", String[])
    maximize = get(problem_data, "maximize", false)
    
    num_vars = length(variable_bounds["lower_bounds"])
    num_constraints = length(constraint_bounds["lower_bounds"])
    
    timing_data["data_processing_time"] = time() - processing_start
    
    if verbose
        println("Problem dimensions:")
        println("  - Variables: $num_vars")
        println("  - Constraints: $num_constraints")
        println("  - Objective sense: $(maximize ? "MAXIMIZE" : "MINIMIZE")")
    end
    
    # Time model creation
    model_start = time()
    
    # Create JuMP model with cuOpt
    if maximize
        model = Model(cuOpt.Optimizer)
        @objective(model, Max, 0)  # Will be updated
    else
        model = Model(cuOpt.Optimizer)
        @objective(model, Min, 0)  # Will be updated
    end
    
    # Suppress solver output unless verbose
    if !verbose
        set_silent(model)
    end
    
    timing_data["model_creation_time"] = time() - model_start
    
    # Time variable setup
    var_start = time()
    
    # Create variable names if not provided
    if isempty(variable_names)
        variable_names = ["x_$i" for i in 0:num_vars-1]
    end
    
    # Add variables
    variables = []
    
    for i in 1:num_vars
        lb = variable_bounds["lower_bounds"][i]
        ub = variable_bounds["upper_bounds"][i]
        
        # Handle nothing values from JSON null
        # For lower bounds, nothing means unbounded below (-Inf)
        # For upper bounds, nothing means unbounded above (Inf)
        if lb === nothing
            lb = -Inf
        end
        if ub === nothing  
            ub = Inf
        end
        
        # Determine variable type
        var_type = "C"  # Default continuous
        if i <= length(variable_types)
            var_type = variable_types[i]
        end
        
        # Variable name
        var_name = (i <= length(variable_names)) ? variable_names[i] : "x_$(i-1)"
        
        # Create variable with appropriate bounds
        if var_type == "I"
            # Integer variable
            if lb == -Inf && ub == Inf
                # No bounds
                var = @variable(model, integer=true, base_name=var_name)
            elseif lb == -Inf
                # Only upper bound
                var = @variable(model, integer=true, upper_bound=ub, base_name=var_name)
            elseif ub == Inf
                # Only lower bound
                var = @variable(model, integer=true, lower_bound=lb, base_name=var_name)
            else
                # Both bounds
                var = @variable(model, integer=true, lower_bound=lb, upper_bound=ub, base_name=var_name)
            end
        else
            # Continuous variable
            if lb == -Inf && ub == Inf
                # No bounds
                var = @variable(model, base_name=var_name)
            elseif lb == -Inf
                # Only upper bound
                var = @variable(model, upper_bound=ub, base_name=var_name)
            elseif ub == Inf
                # Only lower bound
                var = @variable(model, lower_bound=lb, base_name=var_name)
            else
                # Both bounds
                var = @variable(model, lower_bound=lb, upper_bound=ub, base_name=var_name)
            end
        end
        
        push!(variables, var)
    end
    
    timing_data["variable_creation_time"] = time() - var_start
    
    # Time objective setup
    obj_start = time()
    
    # Set objective
    obj_coeffs = objective_data["coefficients"]
    obj_offset = get(objective_data, "offset", 0.0)
    
    println("objective offset: $(obj_offset)")


    # Build objective expression
    obj_expr = sum(obj_coeffs[i] * variables[i] for i in 1:min(length(obj_coeffs), num_vars) if obj_coeffs[i] != 0)
    obj_expr += obj_offset
    
    if maximize
        @objective(model, Max, obj_expr)
    else
        @objective(model, Min, obj_expr)
    end
    
    timing_data["objective_setup_time"] = time() - obj_start
    
    # Time constraint setup
    const_start = time()
    
    # Add constraints from CSR matrix
    offsets = csr_matrix["offsets"]
    indices = csr_matrix["indices"]
    values = csr_matrix["values"]
    
    # Convert to 1-based indexing for Julia
    indices_1based = [idx + 1 for idx in indices]
    
    lower_bounds = constraint_bounds["lower_bounds"]
    upper_bounds = constraint_bounds["upper_bounds"]
    
    # Pre-compute masks for different constraint types
    equality_mask = [lower_bounds[i] == upper_bounds[i] && 
                    lower_bounds[i] != -Inf && 
                    upper_bounds[i] != Inf for i in 1:num_constraints]
    
    upper_mask = [upper_bounds[i] != Inf && !equality_mask[i] for i in 1:num_constraints]
    lower_mask = [lower_bounds[i] != -Inf && !equality_mask[i] for i in 1:num_constraints]
    
    if verbose
        println("Constraint analysis:")
        println("  - Equality constraints: $(sum(equality_mask))")
        println("  - Upper bound constraints: $(sum(upper_mask))")
        println("  - Lower bound constraints: $(sum(lower_mask))")
    end
    
    # Create constraints
    constraint_count = 0
    
    for i in 1:num_constraints
        # Get the range of non-zeros for this constraint
        start_idx = offsets[i] + 1  # Convert to 1-based
        end_idx = offsets[i + 1]    # This is exclusive in 0-based, so correct for 1-based
        
        if start_idx > end_idx
            continue  # Skip empty constraints
        end
        
        # Build the linear expression for this constraint
        constraint_vars = []
        constraint_coeffs = []
        
        for j in start_idx:end_idx
            var_idx = indices_1based[j]
            coeff = values[j]
            if 1 <= var_idx <= num_vars  # Safety check
                push!(constraint_vars, variables[var_idx])
                push!(constraint_coeffs, coeff)
            end
        end
        
        if isempty(constraint_vars)  # Skip empty constraints
            continue
        end
        
        expr = sum(constraint_coeffs[k] * constraint_vars[k] for k in 1:length(constraint_vars))
        
        # Add constraints based on bound analysis
        if equality_mask[i]
            # Equality constraint: expr == bound
            @constraint(model, expr == lower_bounds[i])
            constraint_count += 1
        else
            # Add upper bound constraint if finite upper bound
            if upper_mask[i]
                @constraint(model, expr <= upper_bounds[i])
                constraint_count += 1
            end
            
            # Add lower bound constraint if finite lower bound  
            if lower_mask[i]
                @constraint(model, expr >= lower_bounds[i])
                constraint_count += 1
            end
        end
    end
    
    timing_data["constraint_creation_time"] = time() - const_start
    setup_time = time() - model_start  # Total model setup time
    
    if verbose
        println("Problem setup completed in $(@sprintf("%.3f", setup_time)) seconds")
        println("Created $constraint_count constraints")
    end
    
    # Solve the problem
    solve_start = time()
    
    if verbose
        println("Solving with cuOpt...")
    end
    
    optimize!(model)
    
    # Try to get actual solver time from JuMP
    solve_time = time() - solve_start  # Default to wall clock time
    
    # Check if we can get the actual solver time from the model
    try
        # Try to get solver time from JuMP's solve_time attribute
        solver_solve_time = JuMP.solve_time(model)
        if solver_solve_time !== nothing && solver_solve_time > 0
            solve_time = solver_solve_time
        end
    catch
        # If JuMP doesn't provide solver time, keep wall clock time
        # This happens when the solver doesn't report timing information
    end
    
    timing_data["solve_time"] = solve_time
    timing_data["solve_wall_time"] = time() - solve_start
    
    # Time result extraction
    result_start = time()
    
    # Extract results
    status = string(termination_status(model))
    
    # Get objective value
    objective_value = nothing
    if status == "OPTIMAL"
        try
            objective_value = JuMP.objective_value(model)
        catch
            objective_value = nothing
        end
    end
    
    # Get variable values
    variable_values = Dict{String, Float64}()
    if status == "OPTIMAL"
        try
            for (i, var) in enumerate(variables)
                var_name = (i <= length(variable_names)) ? variable_names[i] : "x_$(i-1)"
                val = value(var)
                if !isnothing(val)
                    variable_values[var_name] = val
                end
            end
        catch
            # Handle case where solution is not available
        end
    end
    
    # Determine problem type
    problem_type = any(is_integer(var) for var in variables) ? "MIP" : "LP"
    
    timing_data["result_extraction_time"] = time() - result_start
    total_time = time() - script_start
    timing_data["total_time"] = total_time
    
    results = Dict(
        "status" => status,
        "objective_value" => objective_value,
        "solve_time" => solve_time,
        "setup_time" => setup_time,
        "total_time" => total_time,
        "variable_values" => variable_values,
        "num_variables" => num_vars,
        "num_constraints" => constraint_count,
        "problem_type" => problem_type,
        "timing_breakdown" => timing_data
    )
    
    if verbose
        try
            println("\nSolution Results:")
            println("  - Status: $status")
            println("  - Solve time: $(@sprintf("%.3f", solve_time)) seconds")
            println("  - Setup time: $(@sprintf("%.3f", setup_time)) seconds") 
            println("  - Total time: $(@sprintf("%.3f", total_time)) seconds")
            
            if !isnothing(objective_value)
                println("  - Objective value: $objective_value")
                
                # Print first few variable values
                if !isempty(variable_values)
                    println("\nVariable values (first 10):")
                    count = 0
                    for (name, val) in variable_values
                        if count >= 10
                            break
                        end
                        if abs(val) > 1e-6  # Only show non-zero values
                            println("  $name: $val")
                            count += 1
                        end
                    end
                    
                    # Count non-zero variables (skip if causing issues)
                    try
                        non_zero_vars = [v for v in values(variable_values) if abs(v) > 1e-6]
                        println("  ($(length(non_zero_vars)) variables have non-zero values)")
                    catch
                        println("  (variable count calculation skipped)")
                    end
                end
            else
                println("  - No solution found")
            end
        catch e
            println("\nSolution Results:")
            println("  - Status: $status")
            println("  - Solve time: $(@sprintf("%.3f", solve_time)) seconds") 
            if !isnothing(objective_value)
                println("  - Objective value: $objective_value")
            end
            println("  (detailed output skipped due to formatting error)")
        end
    end
    
    return results
end

function main()
    # Simple command line parsing
    if length(ARGS) < 1
        println("Usage: julia cuopt_julia_solver.jl <json_file> [OPTIONS]")
        println("")
        println("Arguments:")
        println("  json_file           cuOpt LP JSON file to solve")
        println("")
        println("Options:")
        println("  --quiet, -q         Minimal output - only show final results")
        println("  --timing            Include detailed timing breakdown in output")
        println("  --help, -h          Show this help message")
        exit(1)
    end
    
    # Check for help
    if any(arg -> arg in ["--help", "-h"], ARGS)
        println("cuOpt Julia Solver - Solve LP/MIP problems using Julia JuMP with cuOpt")
        println("")
        println("Usage: julia cuopt_julia_solver.jl <json_file> [OPTIONS]")
        println("")
        println("Arguments:")
        println("  json_file           cuOpt LP JSON file to solve")
        println("")
        println("Options:")
        println("  --quiet, -q         Minimal output - only show final results")
        println("  --timing            Include detailed timing breakdown in output")
        println("  --help, -h          Show this help message")
        println("")
        println("Examples:")
        println("  julia cuopt_julia_solver.jl problem.json")
        println("  julia cuopt_julia_solver.jl problem.json --quiet")
        println("  julia cuopt_julia_solver.jl problem.json --quiet --timing")
        exit(0)
    end
    
    json_file = ARGS[1]
    quiet = any(arg -> arg in ["--quiet", "-q"], ARGS)
    show_timing = any(arg -> arg in ["--timing"], ARGS)
    verbose = !quiet
    
    # Check if file exists
    if !isfile(json_file)
        println("ERROR: File '$json_file' not found!")
        exit(1)
    end
    
    try
        results = solve_cuopt_json_with_julia(json_file, verbose=verbose)
        
        if quiet
            # Minimal output for scripting
            println("Status: $(results["status"])")
            if !isnothing(results["objective_value"])
                println("Objective: $(results["objective_value"])")
            end
            println("Time: $(@sprintf("%.6f", results["solve_time"]))")
            
            # Add timing breakdown only if requested
            if show_timing
                timing = results["timing_breakdown"]
                println("TIMING:json_parse_time:$(@sprintf("%.6f", timing["json_parse_time"]))")
                println("TIMING:data_processing_time:$(@sprintf("%.6f", timing["data_processing_time"]))")
                println("TIMING:model_creation_time:$(@sprintf("%.6f", timing["model_creation_time"]))")
                println("TIMING:variable_creation_time:$(@sprintf("%.6f", timing["variable_creation_time"]))")
                println("TIMING:objective_setup_time:$(@sprintf("%.6f", timing["objective_setup_time"]))")
                println("TIMING:constraint_creation_time:$(@sprintf("%.6f", timing["constraint_creation_time"]))")
                println("TIMING:solve_time:$(@sprintf("%.6f", timing["solve_time"]))")
                println("TIMING:solve_wall_time:$(@sprintf("%.6f", timing["solve_wall_time"]))")
                println("TIMING:result_extraction_time:$(@sprintf("%.6f", timing["result_extraction_time"]))")
                println("TIMING:total_time:$(@sprintf("%.6f", timing["total_time"]))")
            end
        end
        
        # Exit code based on solution status
        if results["status"] == "OPTIMAL"
            exit(0)
        else
            exit(1)
        end
        
    catch e
        println("ERROR: $e")
        if verbose
            # Print the backtrace in a safe way
            bt = catch_backtrace()
            Base.show_backtrace(stderr, bt)
            println()
        end
        exit(1)
    end
end

if abspath(PROGRAM_FILE) == @__FILE__
    main()
end 
