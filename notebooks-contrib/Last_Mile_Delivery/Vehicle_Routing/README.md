# Vehicle Routing Problem (VRP) with cuOpt

This notebook demonstrates how to solve a Vehicle Routing Problem using NVIDIA cuOpt. The example showcases optimization for last-mile delivery scenarios with multiple vehicles, time windows, and capacity constraints.

## Overview

The notebook `vrp_optimization.ipynb` demonstrates:
- Setting up and solving a VRP problem using cuOpt Server API
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

## cuOpt Server API

This example uses the cuOpt Server API. Make sure you have:
1. Valid cuOpt Server API credentials
2. Access to cuOpt Server endpoint
3. Proper environment variables set for authentication

## Data

The notebook includes sample data for demonstration, but can be adapted for real-world delivery scenarios with your own data. 
