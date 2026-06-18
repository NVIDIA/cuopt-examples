# Diet Optimization

This folder contains examples of how to use NVIDIA cuOpt **Python API** to solve diet optimization problems.

## Examples

### 1. Diet Optimization (LP)

The diet optimization notebook solves a linear programming problem where:

- The goal is to minimize the cost of a diet while satisfying the nutritional requirements.
- The diet is a mix of different foods.
- The foods have different prices and nutritional values.

The notebook also demonstrates **sensitivity analysis** on the solved LP: reading constraint
**dual values** (`DualValue`) and variable **reduced costs** (`ReducedCost`) to see which
nutritional requirements drive the cost and how far each unused food is from entering the diet,
then adding a constraint and reading *its* dual value (the marginal cost of the cap).


### 2. Diet Optimization (MILP)

The different between LP and MILP is that the food serving size can be a fraction in LP, but must be a whole number in MILP.