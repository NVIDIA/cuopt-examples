# LP and MILP Optimization with cuOpt Server

This section demonstrates how to use NVIDIA cuOpt to solve math optimization problems. The notebooks solve simple LP and MILP problems using the cuOpt gRPC server and the gRPC client to submit problems and receive results.

## Platform Compatibility

If you are running on a platform where cuOpt is not installed, please un-comment the installation cell in the notebook for cuopt.

## Examples

### 1. Linear Programming

Solves a simple linear system with continuous variables

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify objective function
- Build the problem with the `Problem` algebraic API and submit it to the gRPC server

### 2. Linear Programming with DataModel

Solves a simple linear system with continuous variables using DataModel object

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify objective function
- Build the problem using the DataModel API and submit the `DataModel` directly to the gRPC server

### 3. Mixed Integer Linear Programming

Solves a simple linear system with one continuous and one integer variable

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify variable types
- Specify objective function
- Build the problem with the `Problem` algebraic API and submit it to the gRPC server

### 4. Mixed Integer Linear Programming with DataModel

Solves a simple linear system with one continuous and one integer variable using DataModel object

- Specify constraint matrix and bounds
- Specify variable bounds
- Specify variable types
- Specify objective function
- Build the problem using the DataModel API and submit the `DataModel` directly to the gRPC server

## How to Use

1. Ensure you have the required dependencies installed
   - `cuopt-cu12` or `cuopt-cu13` pip package, which provides the gRPC client and the `cuopt_grpc_server` executable
   - The notebooks start `cuopt_grpc_server` on localhost:5001 if it is not already running
2. Run the notebook cells in sequence
3. The notebooks will:
   - Set up the problem data
   - Solve the optimization problem using the gRPC client
   - Display the solution