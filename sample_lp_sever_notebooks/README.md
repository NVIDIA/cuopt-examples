# LP and MILP Optimization with cuOpt Server

This section demonstrates how to use NVIDIA cuOpt to solve math optimization problems. The notebooks solve simple LP and MILP problems using the cuOpt service and a local client to submit problems and receive results.

## Platform Compatibility

If you are running on a platform where cuOpt is not installed, please un-comment the installation cell in the notebook for cuopt.

## Examples

### 1. Linear Programming

Solves a simple linear system with continuous variables

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify objective function
- Build the problem as a Python dictionary to submit to the cuOpt server

### 2. Linear Programming with DataModel

Solves a simple linear system with continuous variables using DataModel object

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify objective function
- Build the problem using the DataModel API and convert to a Python dictionary before submitting to the cuOpt server

### 3. Mixed Integer Linear Programming

Solves a simple linear system with one continuous and one integer variable

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify variable types
- Specify objective function
- Build the problem as a Python dictionary to submit to the cuOpt server

### 4. Mixed Integer Linear Programming with DataModel

Solves a simple linear system with one continuous and one integer variable using DataModel object

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify variable types
- Specify objective function
- Build the problem using the DataModel API and convert to a Python dictionary before submitting to the cuOpt server

## How to Use

1. Ensure you have the required dependencies installed
   - cuopt_sh_client pip package
   - cuOpt service running at localhost:5000
2. Run the notebook cells in sequence
3. The notebooks will:
   - Set up the problem data
   - Solve the optimization problem using the cuOpt service API
   - Display the solution