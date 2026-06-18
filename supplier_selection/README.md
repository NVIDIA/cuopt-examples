# Supplier Sourcing

This folder contains examples of how to use NVIDIA cuOpt to solve supplier sourcing problems. The notebooks solve supplier sourcing problems using the cuOpt Python API.

## Examples

### 1. Multi-Objective Supplier Sourcing (QP)

The notebook splits one order across suppliers when reliability and diversification conflict — the reliable suppliers cluster, so demanding reliability concentrates the order:

- Minimizes **concentration risk** (a quadratic `wᵀ C w` over the allocation, high within-region correlation) subject to a fully-allocated order, a per-supplier cap, and a unit-cost budget.
- Traces the **concentration vs. reliability** frontier as an ε-constraint sweep (sweep the reliability floor).
- Reads each point's **dual**: the sensitivity d(concentration)/d(reliability) — the diversification given up per point of reliability.
- Builds the dense concentration quadratic from the matrix directly (`QuadraticExpression(qmatrix=...)`) rather than term by term.
