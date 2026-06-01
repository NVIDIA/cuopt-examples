# Workforce Optimization

This section demonstrates how to use NVIDIA cuOpt to solve workforce optimization problems. The notebooks solve workforce optimization problems using the cuOpt Python API.

## Examples

### 1. Workforce Optimization (MILP)

The workforce optimization notebook solves a mixed integer linear programming problem where:

- The goal is to assign workers to shifts while minimizing total labor cost.
- The workers have different availability and different pay rates.
- The shifts have different requirements.

### 2. Workforce Optimization (Multi-Objective)

Extends the MILP above into a Pareto frontier — choose the tradeoff instead of getting one plan:

- **cost vs. coverage** — sweep a coverage floor as an ε-constraint; read the marginal cost per shift off the frontier.
- **cost vs. fairness** — promote the fixed per-worker shift cap into a swept objective (a constraint treated as a candidate objective).

Follows the `cuopt-multi-objective-exploration` skill. A MILP has no constraint duals, so the marginal cost comes from the frontier itself.