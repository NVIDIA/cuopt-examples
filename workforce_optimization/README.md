# Workforce Optimization

This section demonstrates how to use NVIDIA cuOpt to solve workforce optimization problems. The notebooks solve workforce optimization problems using the cuOpt Python API.

## Examples

### 1. Workforce Optimization (MILP)

The workforce optimization notebook solves a mixed integer linear programming problem where:

- The goal is to assign workers to shifts while minimizing total labor cost.
- The workers have different availability and different pay rates.
- The shifts have different requirements.

### 2. Workforce Optimization (Multi-Objective)

The multi-objective notebook extends the MILP above into a Pareto frontier, so you see the tradeoff instead of a single plan. It traces two tradeoffs with the ε-constraint method:

- **cost vs. coverage**: sweep a coverage floor as an ε-constraint, then read the marginal cost per shift off the frontier.
- **cost vs. fairness**: sweep the fixed per-worker shift cap, a constraint whose assumed level is a candidate objective.

A MILP has no constraint duals, so the marginal cost is read off the frontier itself.