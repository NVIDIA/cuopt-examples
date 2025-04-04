# Vehicle Routing Problem (VRP) with NVIDIA cuOpt

This notebook demonstrates how to solve a Vehicle Routing Problem using NVIDIA cuOpt. The example showcases optimization for last-mile delivery scenarios with multiple vehicles, time windows, and capacity constraints.

## Overview

The notebook `vrp_optimization.ipynb` demonstrates:
- Setting up and solving a VRP problem using NVIDIA cuOpt SDK
- Handling multiple vehicles with different capacities
- Managing time windows for deliveries
- Visualizing routes on a map
- Analyzing solution quality and performance

## Requirements

This notebook requires the following packages:
- cuopt-sdk>=25.02
- numpy>=1.21.0
- pandas>=1.3.0
- folium>=0.12.0
- matplotlib>=3.4.0

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

The notebook includes sample data for demonstration, but can be adapted for real-world delivery scenarios with your own data. 
