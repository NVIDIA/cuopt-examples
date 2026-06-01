# Portfolio Optimization

This folder contains examples of how to use NVIDIA cuOpt to solve portfolio optimization problems. The notebooks solve portfolio optimization problems using the cuOpt Python API.

## Examples

### 1. Portfolio Optimization (CVaR)

The portfolio optimization notebook solves a portfolio optimization problem where:

- The goal is to maximize the expected return of a portfolio while minimizing the risk.

### 2. Portfolio Optimization using QP

- The aim is to balance expected return with the risk of losses

### 3. Portfolio Frontier with Shadow Prices (QP)

- Builds the efficient frontier as a named ε-constraint sweep (following the `cuopt-multi-objective-exploration` skill).
- Adds the return-constraint **dual** — the shadow price d(variance)/d(return) — along the frontier, with the PDLP-tolerance caveat.

### 4. Advanced Portfolio Optimization

For advanced portfolio optimization examples including:
- Efficient frontier construction
- Backtesting strategies
- Turnover optimization
- Mean-CVaR optimization with comprehensive workflows

Please visit the **[NVIDIA Quantitative Portfolio Optimization repository](https://github.com/NVIDIA-AI-Blueprints/quantitative-portfolio-optimization)**
