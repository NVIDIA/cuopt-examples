/*
 * SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * cuOpt JSON Solver - A C program that reads cuOpt JSON files and solves them using the C API
 * 
 * This program demonstrates how to:
 * 1. Parse a cuOpt JSON file containing LP/MIP problem data
 * 2. Convert the JSON data to the C API format
 * 3. Solve the problem using the cuOpt C API
 * 4. Display the results
 */

#define _POSIX_C_SOURCE 199309L
#define _DEFAULT_SOURCE  // For gettimeofday on glibc

#include <cuopt/linear_programming/cuopt_c.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <cJSON.h>
#include <time.h>
#include <sys/time.h>  // For gettimeofday and struct timeval

// Global flags to control features (disabled by default)
static int timing_enabled = 0;
static char* mps_output_file = NULL;

// Timing utility functions
typedef struct {
    struct timespec start_time;
    struct timespec end_time;
} Timer;

void start_timer(Timer* timer) {
    if (timing_enabled) {
        clock_gettime(CLOCK_MONOTONIC, &timer->start_time);
    }
}

double end_timer(Timer* timer) {
    if (!timing_enabled) {
        return 0.0;
    }
    clock_gettime(CLOCK_MONOTONIC, &timer->end_time);
    double elapsed = (timer->end_time.tv_sec - timer->start_time.tv_sec) + 
                    (timer->end_time.tv_nsec - timer->start_time.tv_nsec) / 1e9;
    return elapsed;
}

void log_timestamp(const char* phase) {
    if (!timing_enabled) {
        return;
    }
    struct timespec current_time;
    clock_gettime(CLOCK_MONOTONIC, &current_time);
    printf("[TIMESTAMP] %s: %ld.%09ld\n", phase, current_time.tv_sec, current_time.tv_nsec);
}

void log_phase_duration(const char* phase, double duration) {
    if (!timing_enabled) {
        return;
    }
    printf("[DURATION] %s: %.6f seconds\n", phase, duration);
}

// Helper function to convert termination status to string
const char* termination_status_to_string(cuopt_int_t termination_status)
{
    switch (termination_status) {
        case CUOPT_TERIMINATION_STATUS_OPTIMAL:
            return "Optimal";
        case CUOPT_TERIMINATION_STATUS_INFEASIBLE:
            return "Infeasible";
        case CUOPT_TERIMINATION_STATUS_UNBOUNDED:
            return "Unbounded";
        case CUOPT_TERIMINATION_STATUS_ITERATION_LIMIT:
            return "Iteration limit";
        case CUOPT_TERIMINATION_STATUS_TIME_LIMIT:
            return "Time limit";
        case CUOPT_TERIMINATION_STATUS_NUMERICAL_ERROR:
            return "Numerical error";
        case CUOPT_TERIMINATION_STATUS_PRIMAL_FEASIBLE:
            return "Primal feasible";
        case CUOPT_TERIMINATION_STATUS_FEASIBLE_FOUND:
            return "Feasible found";
        default:
            return "Unknown";
    }
}

// Helper function to parse infinity values from JSON
cuopt_float_t parse_numeric_value(cJSON* item) {
    if (cJSON_IsNumber(item)) {
        return item->valuedouble;
    } else if (cJSON_IsString(item)) {
        char* str = item->valuestring;
        if (strcmp(str, "inf") == 0 || strcmp(str, "infinity") == 0) {
            return CUOPT_INFINITY;
        } else if (strcmp(str, "-inf") == 0 || strcmp(str, "-infinity") == 0 || strcmp(str, "ninf") == 0) {
            return -CUOPT_INFINITY;
        } else {
            return strtod(str, NULL);
        }
    }
    return 0.0;
}

// Structure to hold parsed JSON data
typedef struct {
    // CSR matrix data
    cuopt_int_t* row_offsets;
    cuopt_int_t* column_indices;
    cuopt_float_t* matrix_values;
    cuopt_int_t num_constraints;
    cuopt_int_t num_variables;
    cuopt_int_t nnz;
    
    // Objective data
    cuopt_float_t* objective_coefficients;
    cuopt_float_t objective_offset;
    cuopt_int_t objective_sense;  // CUOPT_MINIMIZE or CUOPT_MAXIMIZE
    
    // Constraint bounds
    cuopt_float_t* constraint_lower_bounds;
    cuopt_float_t* constraint_upper_bounds;
    
    // Variable bounds
    cuopt_float_t* variable_lower_bounds;
    cuopt_float_t* variable_upper_bounds;
    
    // Variable types
    char* variable_types;
    
} ProblemData;

// Function to free allocated memory
void free_problem_data(ProblemData* data) {
    if (data) {
        free(data->row_offsets);
        free(data->column_indices);
        free(data->matrix_values);
        free(data->objective_coefficients);
        free(data->constraint_lower_bounds);
        free(data->constraint_upper_bounds);
        free(data->variable_lower_bounds);
        free(data->variable_upper_bounds);
        free(data->variable_types);
        memset(data, 0, sizeof(ProblemData));
    }
}

// Function to parse cuOpt JSON file
int parse_cuopt_json(const char* filename, ProblemData* data) {
    Timer timer;
    log_timestamp("JSON_PARSE_START");
    start_timer(&timer);
    
    log_timestamp("FILE_READ_START");
    Timer file_timer;
    start_timer(&file_timer);
    
    FILE* file = fopen(filename, "r");
    if (!file) {
        printf("Error: Cannot open file %s\n", filename);
        return -1;
    }
    
    // Read file content
    fseek(file, 0, SEEK_END);
    long file_size = ftell(file);
    fseek(file, 0, SEEK_SET);
    
    char* file_content = malloc(file_size + 1);
    if (!file_content) {
        printf("Error: Memory allocation failed\n");
        fclose(file);
        return -1;
    }
    
    size_t bytes_read = fread(file_content, 1, file_size, file);
    file_content[bytes_read] = '\0';
    fclose(file);
    
    double file_read_time = end_timer(&file_timer);
    log_timestamp("FILE_READ_END");
    log_phase_duration("FILE_READ", file_read_time);
    
    if (bytes_read != (size_t)file_size) {
        printf("Warning: Only read %zu bytes out of %ld expected\n", bytes_read, file_size);
    }

    struct timeval tv;
    gettimeofday(&tv, NULL);
    double timestamp = (double)tv.tv_sec + (double)tv.tv_usec / 1000000.0;
    printf("PROBLEM_START: %.6f\n", timestamp);

    // Parse JSON
    log_timestamp("JSON_PARSE_STRUCTURE_START");
    Timer json_parse_timer;
    start_timer(&json_parse_timer);
    
    cJSON* json = cJSON_Parse(file_content);
    free(file_content);
    
    double json_parse_time = end_timer(&json_parse_timer);
    log_timestamp("JSON_PARSE_STRUCTURE_END");
    log_phase_duration("JSON_PARSE_STRUCTURE", json_parse_time);
    
    if (!json) {
        printf("Error: Failed to parse JSON\n");
        return -1;
    }
    
    // Parse CSR constraint matrix
    log_timestamp("CSR_MATRIX_PARSE_START");
    Timer csr_timer;
    start_timer(&csr_timer);
    
    cJSON* csr_matrix = cJSON_GetObjectItem(json, "csr_constraint_matrix");
    if (!csr_matrix) {
        printf("Error: Missing csr_constraint_matrix in JSON\n");
        cJSON_Delete(json);
        return -1;
    }
    
    cJSON* offsets = cJSON_GetObjectItem(csr_matrix, "offsets");
    cJSON* indices = cJSON_GetObjectItem(csr_matrix, "indices");
    cJSON* values = cJSON_GetObjectItem(csr_matrix, "values");
    
    if (!offsets || !indices || !values) {
        printf("Error: Invalid CSR matrix format\n");
        cJSON_Delete(json);
        return -1;
    }
    
    data->num_constraints = cJSON_GetArraySize(offsets) - 1;
    data->nnz = cJSON_GetArraySize(indices);
    
    // Allocate memory for CSR data
    data->row_offsets = malloc((data->num_constraints + 1) * sizeof(cuopt_int_t));
    data->column_indices = malloc(data->nnz * sizeof(cuopt_int_t));
    data->matrix_values = malloc(data->nnz * sizeof(cuopt_float_t));
    
    // Parse CSR data - OPTIMIZED VERSION
    // Use cJSON_ArrayForEach for O(n) complexity instead of O(n²)
    int i = 0;
    cJSON* offset_item;
    cJSON_ArrayForEach(offset_item, offsets) {
        data->row_offsets[i] = offset_item->valueint;
        i++;
    }
    
    i = 0;
    cJSON* index_item;
    cJSON_ArrayForEach(index_item, indices) {
        data->column_indices[i] = index_item->valueint;
        i++;
    }
    
    i = 0;
    cJSON* value_item;
    cJSON_ArrayForEach(value_item, values) {
        data->matrix_values[i] = value_item->valuedouble;
        i++;
    }
    
    double csr_time = end_timer(&csr_timer);
    log_timestamp("CSR_MATRIX_PARSE_END");
    log_phase_duration("CSR_MATRIX_PARSE", csr_time);
    
    // Parse objective data
    log_timestamp("OBJECTIVE_PARSE_START");
    Timer objective_timer;
    start_timer(&objective_timer);
    
    cJSON* objective_data = cJSON_GetObjectItem(json, "objective_data");
    if (!objective_data) {
        printf("Error: Missing objective_data in JSON\n");
        cJSON_Delete(json);
        return -1;
    }
    
    cJSON* obj_coeffs = cJSON_GetObjectItem(objective_data, "coefficients");
    data->num_variables = cJSON_GetArraySize(obj_coeffs);
    
    data->objective_coefficients = malloc(data->num_variables * sizeof(cuopt_float_t));
    // OPTIMIZED: Use cJSON_ArrayForEach for O(n) complexity
    i = 0;
    cJSON* coeff_item;
    cJSON_ArrayForEach(coeff_item, obj_coeffs) {
        data->objective_coefficients[i] = coeff_item->valuedouble;
        i++;
    }
    
    cJSON* offset = cJSON_GetObjectItem(objective_data, "offset");
    data->objective_offset = offset ? offset->valuedouble : 0.0;
    // Print the objective offset value
    printf("Objective offset: %g\n", data->objective_offset);   

    // Parse maximize flag
    cJSON* maximize = cJSON_GetObjectItem(json, "maximize");
    data->objective_sense = (maximize && cJSON_IsTrue(maximize)) ? CUOPT_MAXIMIZE : CUOPT_MINIMIZE;
    
    double objective_time = end_timer(&objective_timer);
    log_timestamp("OBJECTIVE_PARSE_END");
    log_phase_duration("OBJECTIVE_PARSE", objective_time);
    
    // Parse constraint bounds
    log_timestamp("CONSTRAINT_BOUNDS_PARSE_START");
    Timer constraint_timer;
    start_timer(&constraint_timer);
    
    cJSON* constraint_bounds = cJSON_GetObjectItem(json, "constraint_bounds");
    if (constraint_bounds) {
        data->constraint_lower_bounds = malloc(data->num_constraints * sizeof(cuopt_float_t));
        data->constraint_upper_bounds = malloc(data->num_constraints * sizeof(cuopt_float_t));
        
        cJSON* lower_bounds = cJSON_GetObjectItem(constraint_bounds, "lower_bounds");
        cJSON* upper_bounds = cJSON_GetObjectItem(constraint_bounds, "upper_bounds");
        
        if (lower_bounds && upper_bounds) {
            // OPTIMIZED: Use cJSON_ArrayForEach for O(n) complexity
            i = 0;
            cJSON* lower_item;
            cJSON_ArrayForEach(lower_item, lower_bounds) {
                data->constraint_lower_bounds[i] = parse_numeric_value(lower_item);
                i++;
            }
            
            i = 0;
            cJSON* upper_item;
            cJSON_ArrayForEach(upper_item, upper_bounds) {
                data->constraint_upper_bounds[i] = parse_numeric_value(upper_item);
                i++;
            }
        } else {
            // Fallback to bounds and types format
            cJSON* bounds = cJSON_GetObjectItem(constraint_bounds, "bounds");
            cJSON* types = cJSON_GetObjectItem(constraint_bounds, "types");
            
            if (bounds && types) {
                // OPTIMIZED: Use parallel iteration with cJSON_ArrayForEach
                i = 0;
                cJSON* bound_item = bounds->child;
                cJSON* type_item = types->child;
                while (bound_item && type_item && i < data->num_constraints) {
                    cuopt_float_t bound_value = parse_numeric_value(bound_item);
                    char* type = type_item->valuestring;
                    
                    if (strcmp(type, "L") == 0) {  // Less than or equal
                        data->constraint_lower_bounds[i] = -CUOPT_INFINITY;
                        data->constraint_upper_bounds[i] = bound_value;
                    } else if (strcmp(type, "G") == 0) {  // Greater than or equal
                        data->constraint_lower_bounds[i] = bound_value;
                        data->constraint_upper_bounds[i] = CUOPT_INFINITY;
                    } else if (strcmp(type, "E") == 0) {  // Equal
                        data->constraint_lower_bounds[i] = bound_value;
                        data->constraint_upper_bounds[i] = bound_value;
                    }
                    
                    bound_item = bound_item->next;
                    type_item = type_item->next;
                    i++;
                }
            }
        }
    }
    
    double constraint_time = end_timer(&constraint_timer);
    log_timestamp("CONSTRAINT_BOUNDS_PARSE_END");
    log_phase_duration("CONSTRAINT_BOUNDS_PARSE", constraint_time);
    
    // Parse variable bounds
    log_timestamp("VARIABLE_BOUNDS_PARSE_START");
    Timer variable_bounds_timer;
    start_timer(&variable_bounds_timer);
    
    cJSON* variable_bounds = cJSON_GetObjectItem(json, "variable_bounds");
    if (variable_bounds) {
        data->variable_lower_bounds = malloc(data->num_variables * sizeof(cuopt_float_t));
        data->variable_upper_bounds = malloc(data->num_variables * sizeof(cuopt_float_t));
        
        cJSON* var_lower = cJSON_GetObjectItem(variable_bounds, "lower_bounds");
        cJSON* var_upper = cJSON_GetObjectItem(variable_bounds, "upper_bounds");
        
        // OPTIMIZED: Use cJSON_ArrayForEach for O(n) complexity
        i = 0;
        cJSON* var_lower_item;
        cJSON_ArrayForEach(var_lower_item, var_lower) {
            data->variable_lower_bounds[i] = parse_numeric_value(var_lower_item);
            i++;
        }
        
        i = 0;
        cJSON* var_upper_item;
        cJSON_ArrayForEach(var_upper_item, var_upper) {
            data->variable_upper_bounds[i] = parse_numeric_value(var_upper_item);
            i++;
        }
    }
    
    double variable_bounds_time = end_timer(&variable_bounds_timer);
    log_timestamp("VARIABLE_BOUNDS_PARSE_END");
    log_phase_duration("VARIABLE_BOUNDS_PARSE", variable_bounds_time);
    
    // Parse variable types
    log_timestamp("VARIABLE_TYPES_PARSE_START");
    Timer variable_types_timer;
    start_timer(&variable_types_timer);
    
    cJSON* variable_types = cJSON_GetObjectItem(json, "variable_types");
    if (variable_types) {
        data->variable_types = malloc(data->num_variables * sizeof(char));
        // OPTIMIZED: Use cJSON_ArrayForEach for O(n) complexity
        i = 0;
        cJSON* type_item;
        cJSON_ArrayForEach(type_item, variable_types) {
            char* type_str = type_item->valuestring;
            if (strcmp(type_str, "I") == 0) {
                data->variable_types[i] = CUOPT_INTEGER;
            } else {
                data->variable_types[i] = CUOPT_CONTINUOUS;
            }
            i++;
        }
    } else {
        // Default to continuous variables
        data->variable_types = malloc(data->num_variables * sizeof(char));
        for (int i = 0; i < data->num_variables; i++) {
            data->variable_types[i] = CUOPT_CONTINUOUS;
        }
    }
    
    double variable_types_time = end_timer(&variable_types_timer);
    log_timestamp("VARIABLE_TYPES_PARSE_END");
    log_phase_duration("VARIABLE_TYPES_PARSE", variable_types_time);
    
    cJSON_Delete(json);
    
    double total_parse_time = end_timer(&timer);
    log_timestamp("JSON_PARSE_END");
    log_phase_duration("JSON_PARSE_TOTAL", total_parse_time);
    
    return 0;
}

// Function to solve the problem using cuOpt C API
int solve_problem(const ProblemData* data) {
    Timer timer;
    log_timestamp("SOLVE_START");
    start_timer(&timer);
    
    cuOptOptimizationProblem problem = NULL;
    cuOptSolverSettings settings = NULL;
    cuOptSolution solution = NULL;
    cuopt_int_t status;
    
    printf("Creating and solving problem...\n");
    printf("Problem size: %d constraints, %d variables, %d nonzeros\n", 
           data->num_constraints, data->num_variables, data->nnz);
    
    // Create the problem using ranged formulation
    log_timestamp("PROBLEM_CREATION_START");
    Timer problem_timer;
    start_timer(&problem_timer);
    
    status = cuOptCreateRangedProblem(data->num_constraints,
                                     data->num_variables,
                                     data->objective_sense,
                                     data->objective_offset,
                                     data->objective_coefficients,
                                     data->row_offsets,
                                     data->column_indices,
                                     data->matrix_values,
                                     data->constraint_lower_bounds,
                                     data->constraint_upper_bounds,
				     data->variable_lower_bounds,
				     data->variable_upper_bounds,
                                     data->variable_types,
                                     &problem);
    
    double problem_time = end_timer(&problem_timer);
    log_timestamp("PROBLEM_CREATION_END");
    log_phase_duration("PROBLEM_CREATION", problem_time);
    
    if (status != CUOPT_SUCCESS) {
        printf("Error creating problem: %d\n", status);
        goto CLEANUP;
    }
    
    // Create solver settings
    log_timestamp("SOLVER_SETTINGS_START");
    Timer settings_timer;
    start_timer(&settings_timer);
    
    status = cuOptCreateSolverSettings(&settings);
    if (status != CUOPT_SUCCESS) {
        printf("Error creating solver settings: %d\n", status);
        goto CLEANUP;
    }
    
    // Set solver parameters (you can adjust these as needed)
    status = cuOptSetFloatParameter(settings, CUOPT_ABSOLUTE_PRIMAL_TOLERANCE, 1e-6);
    if (status != CUOPT_SUCCESS) {
        printf("Warning: Could not set primal tolerance: %d\n", status);
    }
    
    status = cuOptSetFloatParameter(settings, CUOPT_TIME_LIMIT, 300.0);  // 5 minute limit
    if (status != CUOPT_SUCCESS) {
        printf("Warning: Could not set time limit: %d\n", status);
    }
    
    // Set MPS output file if requested
    if (mps_output_file) {
        status = cuOptSetParameter(settings, CUOPT_USER_PROBLEM_FILE, mps_output_file);
        if (status != CUOPT_SUCCESS) {
            printf("Warning: Could not set MPS output file: %d\n", status);
        } else {
            printf("MPS file will be written to: %s\n", mps_output_file);
        }
    }
    
    double settings_time = end_timer(&settings_timer);
    log_timestamp("SOLVER_SETTINGS_END");
    log_phase_duration("SOLVER_SETTINGS", settings_time);
    
    // Solve the problem
    log_timestamp("SOLVER_EXECUTION_START");
    Timer solve_timer;
    start_timer(&solve_timer);
    
    status = cuOptSolve(problem, settings, &solution);
    struct timeval tv;
    gettimeofday(&tv, NULL);
    double timestamp = (double)tv.tv_sec + (double)tv.tv_usec / 1000000.0;
    printf("SOLVE_END_TIME: %.6f\n", timestamp);
	
    double solve_time_measured = end_timer(&solve_timer);
    log_timestamp("SOLVER_EXECUTION_END");
    log_phase_duration("SOLVER_EXECUTION", solve_time_measured);
    
    if (status != CUOPT_SUCCESS) {
        printf("Error solving problem: %d\n", status);
        goto CLEANUP;
    }
    
    // Get and display results
    log_timestamp("RESULT_EXTRACTION_START");
    Timer results_timer;
    start_timer(&results_timer);
    
    cuopt_float_t solve_time;
    cuopt_int_t termination_status;
    cuopt_float_t objective_value;
    
    status = cuOptGetSolveTime(solution, &solve_time);
    if (status != CUOPT_SUCCESS) {
        printf("Error getting solve time: %d\n", status);
        goto CLEANUP;
    }
    
    status = cuOptGetTerminationStatus(solution, &termination_status);
    if (status != CUOPT_SUCCESS) {
        printf("Error getting termination status: %d\n", status);
        goto CLEANUP;
    }
    
    status = cuOptGetObjectiveValue(solution, &objective_value);
    if (status != CUOPT_SUCCESS) {
        printf("Error getting objective value: %d\n", status);
        goto CLEANUP;
    }
    
    // Print results
    printf("\nResults:\n");
    printf("--------\n");
    printf("Termination status: %s (%d)\n", termination_status_to_string(termination_status), termination_status);
    printf("Solve time: %f seconds\n", solve_time);
    printf("Objective value: %f\n", objective_value);
    
    // Get and print solution variables (first 20 or fewer)
    log_timestamp("SOLUTION_EXTRACTION_START");
    Timer solution_timer;
    start_timer(&solution_timer);
    
    cuopt_float_t* solution_values = malloc(data->num_variables * sizeof(cuopt_float_t));
    status = cuOptGetPrimalSolution(solution, solution_values);
    if (status == CUOPT_SUCCESS) {
        printf("\nPrimal Solution (showing first %d variables):\n", 
               data->num_variables < 20 ? data->num_variables : 20);
        for (int i = 0; i < (data->num_variables < 20 ? data->num_variables : 20); i++) {
            printf("x%d = %f\n", i, solution_values[i]);
        }
        if (data->num_variables > 20) {
            printf("... (showing only first 20 of %d variables)\n", data->num_variables);
        }
    } else {
        printf("Error getting solution values: %d\n", status);
    }
    free(solution_values);
    
    double solution_time = end_timer(&solution_timer);
    log_timestamp("SOLUTION_EXTRACTION_END");
    log_phase_duration("SOLUTION_EXTRACTION", solution_time);
    
    // Check if this is a MIP and get MIP-specific information
    cuopt_int_t is_mip;
    status = cuOptIsMIP(problem, &is_mip);
    if (status == CUOPT_SUCCESS && is_mip) {
        cuopt_float_t mip_gap;
        status = cuOptGetMIPGap(solution, &mip_gap);
        if (status == CUOPT_SUCCESS) {
            printf("MIP Gap: %f\n", mip_gap);
        }
        
        cuopt_float_t solution_bound;
        status = cuOptGetSolutionBound(solution, &solution_bound);
        if (status == CUOPT_SUCCESS) {
            printf("Solution Bound: %f\n", solution_bound);
        }
    }
    
    double results_time = end_timer(&results_timer);
    log_timestamp("RESULT_EXTRACTION_END");
    log_phase_duration("RESULT_EXTRACTION", results_time);

CLEANUP:
    log_timestamp("CLEANUP_START");
    Timer cleanup_timer;
    start_timer(&cleanup_timer);
    
    cuOptDestroyProblem(&problem);
    cuOptDestroySolverSettings(&settings);
    cuOptDestroySolution(&solution);
    
    double cleanup_time = end_timer(&cleanup_timer);
    log_timestamp("CLEANUP_END");
    log_phase_duration("CLEANUP", cleanup_time);
    
    double total_solve_time = end_timer(&timer);
    log_timestamp("SOLVE_END");
    log_phase_duration("SOLVE_TOTAL", total_solve_time);
    
    return status;
}

int main(int argc, char* argv[]) {
    char* json_file = NULL;
    
    // Parse command-line arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--timing") == 0 || strcmp(argv[i], "-t") == 0) {
            timing_enabled = 1;
        } else if (strcmp(argv[i], "--mps-output") == 0) {
            if (i + 1 >= argc) {
                printf("Error: --mps-output requires a filename\n");
                return 1;
            }
            mps_output_file = argv[++i];
        } else if (argv[i][0] == '-') {
            printf("Error: Unknown option '%s'\n", argv[i]);
            printf("Usage: %s [--timing|-t] [--mps-output <file>] <cuopt_json_file>\n", argv[0]);
            printf("\nOptions:\n");
            printf("  --timing, -t           Enable detailed performance timing output\n");
            printf("  --mps-output <file>    Write problem to MPS file\n");
            printf("\nThis program reads a cuOpt JSON file and solves it using the cuOpt C API.\n");
            printf("The JSON file should contain LP or MIP problem data in cuOpt format.\n");
            return 1;
        } else if (json_file == NULL) {
            json_file = argv[i];
        } else {
            printf("Error: Multiple JSON files specified\n");
            printf("Usage: %s [--timing|-t] [--mps-output <file>] <cuopt_json_file>\n", argv[0]);
            return 1;
        }
    }
    
    if (json_file == NULL) {
        printf("Usage: %s [--timing|-t] [--mps-output <file>] <cuopt_json_file>\n", argv[0]);
        printf("\nOptions:\n");
        printf("  --timing, -t           Enable detailed performance timing output\n");
        printf("  --mps-output <file>    Write problem to MPS file\n");
        printf("\nThis program reads a cuOpt JSON file and solves it using the cuOpt C API.\n");
        printf("The JSON file should contain LP or MIP problem data in cuOpt format.\n");
        return 1;
    }
    
    log_timestamp("PROGRAM_START");
    Timer main_timer;
    start_timer(&main_timer);
    
    log_timestamp("INITIALIZATION_START");
    Timer init_timer;
    start_timer(&init_timer);
    
    ProblemData data;
    memset(&data, 0, sizeof(ProblemData));
    
    printf("cuOpt JSON Solver\n");
    printf("=================\n");
    printf("Reading JSON file: %s\n", json_file);
    
    double init_time = end_timer(&init_timer);
    log_timestamp("INITIALIZATION_END");
    log_phase_duration("INITIALIZATION", init_time);
    
    // Parse the JSON file
    if (parse_cuopt_json(json_file, &data) != 0) {
        printf("Failed to parse JSON file\n");
        free_problem_data(&data);
        return 1;
    }
    
    printf("Successfully parsed JSON file\n");
    
    // Solve the problem
    cuopt_int_t solve_status = solve_problem(&data);
    
    // Clean up
    log_timestamp("MAIN_CLEANUP_START");
    Timer main_cleanup_timer;
    start_timer(&main_cleanup_timer);
    
    free_problem_data(&data);
    
    double main_cleanup_time = end_timer(&main_cleanup_timer);
    log_timestamp("MAIN_CLEANUP_END");
    log_phase_duration("MAIN_CLEANUP", main_cleanup_time);
    
    double total_program_time = end_timer(&main_timer);
    log_timestamp("PROGRAM_END");
    log_phase_duration("PROGRAM_TOTAL", total_program_time);
    
    if (solve_status == CUOPT_SUCCESS) {
        printf("\nSolver completed successfully!\n");
        return 0;
    } else {
        printf("\nSolver failed with status: %d\n", solve_status);
        return 1;
    }
} 
