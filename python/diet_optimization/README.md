# Diet Optimization

This folder contains examples of how to use NVIDIA cuOpt **Python API** to solve diet optimization problems.

## Examples

### 1. Diet Optimization (LP)

The diet optimization notebook solves a linear programming problem where:

- The goal is to minimize the cost of a diet while satisfying the nutritional requirements.
- The diet is a mix of different foods.
- The foods have different prices and nutritional values.


### 2. Diet Optimization (MILP)

The different between LP and MILP is that the food serving size can be a fraction in LP, but must be a whole number in MILP.