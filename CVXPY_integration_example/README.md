# CVXPY Integration Example

This folder contains a Jupyter Notebook demonstrating how to integrate NVIDIA cuOpt as a solver backend for optimization problems modeled with CVXPY.

## About CVXPY

[CVXPY](https://www.cvxpy.org/) is a Python-embedded modeling language for convex optimization problems. It allows you to express optimization problems in a natural way that follows the mathematical notation, while automatically transforming the problem into a form that can be solved by various backend solvers.

## Using cuOpt with CVXPY

CVXPY supports cuOpt as a backend solver, allowing you to leverage GPU-accelerated optimization while using CVXPY's intuitive modeling syntax. This integration provides:

- **Familiar API**: Use CVXPY's clean, Pythonic syntax for modeling
- **GPU Acceleration**: Benefit from cuOpt's high-performance GPU-based solving
- **Easy Solver Switching**: Compare different solvers by simply changing the solver parameter

## Example Notebook

### `diet_optimization.ipynb`

This notebook demonstrates the classic diet optimization problem:
- **Problem**: Minimize the cost of food purchases while meeting nutritional requirements
- **Approach**: Model the problem using CVXPY and solve with cuOpt
- **Features**:
  - Setting up decision variables and constraints with CVXPY
  - Solving with `solver="CUOPT"` parameter
  - Analyzing and visualizing results