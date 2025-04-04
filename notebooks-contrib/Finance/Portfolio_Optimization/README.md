# Portfolio Optimization with NVIDIA cuOpt

This notebook demonstrates how to optimize investment portfolios using NVIDIA cuOpt. The example shows how to maximize returns while managing risk through efficient frontier optimization.

## Overview

The notebook `portfolio_optimization.ipynb` demonstrates:
- Setting up and solving portfolio optimization problems using NVIDIA cuOpt SDK
- Implementing mean-variance optimization
- Computing efficient frontier
- Risk-return analysis
- Visualizing optimization results

## Requirements

This notebook requires the following packages:
- cuopt-sdk>=25.02
- numpy>=1.21.0
- pandas>=1.3.0
- matplotlib>=3.4.0
- cuClarabel>=1.0
- cvxpy>=1.6.0

Install the requirements using:
```bash
pip install -r requirements.txt
```

## NVIDIA cuOpt SDK

This example uses the NVIDIA cuOpt SDK for local execution. Make sure you have:
1. NVIDIA GPU with appropriate drivers
2. CUDA toolkit installed
3. NVIDIA cuOpt SDK properly installed and configured

## Data

The notebook uses historical stock data from Yahoo Finance for demonstration. You can modify the code to use your own financial data sources. 
