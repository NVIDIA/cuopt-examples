# Workforce Optimization

This section demonstrates how to use NVIDIA cuOpt to solve workforce optimization problems. The notebooks solve workforce optimization problems using the cuOpt Python API.

## Examples

### 1. Workforce Optimization (MILP)

The workforce optimization notebook solves a mixed integer linear programming problem where:

- The goal is to assign workers to shifts while minimizing total labor cost.
- The workers have different availability and different pay rates.
- The shifts have different requirements.