# Supplier Sourcing

This folder demonstrates how to use NVIDIA cuOpt to solve multi-objective supplier sourcing problems with the cuOpt Python API.

## Examples

### 1. Multi-Objective Supplier Sourcing (QP)

The notebook splits one order across suppliers when reliability and diversification conflict — the reliable suppliers cluster, so demanding reliability concentrates the order:

- Minimizes **concentration risk** (a quadratic `wᵀ C w` over the allocation, high within-region correlation) subject to a fully-allocated order, a per-supplier cap, and a unit-cost budget.
- Traces the **concentration vs. reliability** frontier as an ε-constraint sweep (sweep the reliability floor).
- Reads each point's **dual**: the sensitivity d(concentration)/d(reliability), from cuOpt's barrier (interior-point) solver — the diversification given up per point of reliability.
- Builds the dense concentration quadratic from the matrix directly (`QuadraticExpression(qmatrix=...)`) rather than term by term.

This mirrors the ε-constraint + duals recipe in [`portfolio_optimization`](../portfolio_optimization/) on a procurement decision; it is also packaged as the `cuopt-multi-objective-exploration` skill.
