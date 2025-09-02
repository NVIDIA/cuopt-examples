# cuOpt JSON to C API

A C program that reads cuOpt JSON files containing Linear Programming (LP) and Mixed Integer Programming (MIP) problems and solves them using the NVIDIA cuOpt C API.

## Features

- **JSON Parsing**: Reads cuOpt JSON format for LP/MIP problems
- **Full API Integration**: Uses the complete cuOpt C API for solving optimization problems
- **Flexible Input**: Supports both LP and MIP problems with various constraint types
- **Comprehensive Output**: Displays detailed solution information including objective value, solve time, and solution variables
- **Error Handling**: Robust error handling and memory management
- **Auto-detection**: Automatically detects cuOpt installation paths

## JSON Format

The program expects JSON files in the cuOpt format with the following structure:

```json
{
  "csr_constraint_matrix": {
    "offsets": [0, 2, 4],
    "indices": [0, 1, 0, 1],
    "values": [3.0, 4.0, 2.7, 10.1]
  },
  "objective_data": {
    "coefficients": [-0.2, 0.1],
    "scalability_factor": 1.0,
    "offset": 0.0
  },
  "constraint_bounds": {
    "upper_bounds": [5.4, 4.9],
    "lower_bounds": ["-inf", "-inf"]
  },
  "variable_bounds": {
    "upper_bounds": ["inf", "inf"],
    "lower_bounds": [0.0, 0.0]
  },
  "maximize": false,
  "variable_types": ["C", "C"],
  "variable_names": ["x1", "x2"]
}
```

### JSON Field Descriptions

- **`csr_constraint_matrix`**: Constraint matrix in Compressed Sparse Row format
  - `offsets`: Row offsets array (size: num_constraints + 1)
  - `indices`: Column indices of non-zero elements
  - `values`: Values of non-zero elements

- **`objective_data`**: Objective function information
  - `coefficients`: Objective coefficients for each variable
  - `offset`: Constant offset added to objective (optional, default: 0.0)
  - `scalability_factor`: Scaling factor (optional, default: 1.0)

- **`constraint_bounds`**: Constraint bounds
  - `upper_bounds`: Upper bounds for constraints
  - `lower_bounds`: Lower bounds for constraints
  - Alternative format: `bounds` array with `types` array ("L", "G", "E")

- **`variable_bounds`**: Variable bounds
  - `upper_bounds`: Upper bounds for variables (use "inf" for infinity)
  - `lower_bounds`: Lower bounds for variables (use "-inf" for negative infinity)

- **`maximize`**: Boolean flag for maximization (optional, default: false)

- **`variable_types`**: Array of variable types (optional, default: all continuous)
  - `"C"`: Continuous variable
  - `"I"`: Integer variable

- **`variable_names`**: Array of variable names (optional)

## Prerequisites

### System Requirements
- Linux system with CUDA support
- NVIDIA cuOpt library installed
- C compiler (gcc or clang)
- cJSON library for JSON parsing

### Dependencies
- **libcjson-dev**: JSON parsing library
- **libcuopt**: NVIDIA cuOpt library

#### Installing Dependencies (Ubuntu/Debian)
```bash
# Install cJSON library
sudo apt-get update
sudo apt-get install libcjson-dev

# Or use the Makefile target
make install-deps
```

## Building

**⚠️ Build Issues with Conda?** If you encounter `cannot find -lcjson` errors when building in conda environments, see [BUILD_GUIDE.md](BUILD_GUIDE.md) for solutions, or use the quick fix:

### Build Troubleshooting

If you encounter build issues:

1. **Check paths**: Use `make print-vars` to see detected paths
2. **Manual paths**: Set `CUOPT_INCLUDE_PATH` and `CUOPT_LIBRARY_PATH`
3. **Dependencies**: Ensure libcjson-dev is installed
4. **cuOpt library**: Ensure libcuopt.so is built and accessible

## Usage

### Basic Usage
```bash
# Clean output (default)
./cuopt_json_to_c_api problem.json

# With performance timing (for analysis)
./cuopt_json_to_c_api --timing problem.json
# or
./cuopt_json_to_c_api -t problem.json
```
