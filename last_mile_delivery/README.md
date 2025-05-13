# Last-Mile Delivery Optimization

This notebook demonstrates how to use NVIDIA cuOpt to solve a last-mile delivery optimization problem. The example focuses on optimizing the routes for delivery vehicles from a micro fulfillment center (MFC) to various delivery locations.

## Problem Overview

The notebook solves a Capacitated Vehicle Routing Problem (CVRP) where:

- A fleet of delivery vehicles with different capacities must deliver packages from a micro fulfillment center
- Each delivery location has a specific demand that must be fulfilled
- The delivery fleet consists of vehicles with different capacities (trucks and vans)
- The goal is to minimize the total distance traveled by all vehicles while satisfying all delivery demands

## Key Features

- **Cost Matrix**: Uses a distance-based cost matrix to represent travel costs between locations
- **Demand Modeling**: Incorporates varying demand requirements for different delivery locations
- **Heterogeneous Fleet**: Configures multiple vehicle types with different capacities
- **Constraint Handling**: Demonstrates adding constraints such as minimum vehicle utilization
- **Visualization**: Includes visualization of optimized routes

## How to Use

1. Ensure you have the required dependencies installed (see requirements.txt)
2. Run the notebook cells in sequence
3. The notebook will:
   - Set up the problem data with delivery locations and demands
   - Configure the delivery fleet with appropriate capacities
   - Define the distance matrix between locations
   - Solve the optimization problem using the cuOpt SDK
   - Display and visualize the optimized routes for each vehicle

## Expected Output

The notebook outputs:
- The total cost (distance) of the routing solution
- The number of vehicles used in the solution
- Detailed routes for each vehicle showing the sequence of locations visited
- Visual representation of the optimized routes
- Demonstrates how adding constraints (like minimum vehicle usage) affects the solution

This example is particularly useful for retailers and logistics companies looking to optimize their last-mile delivery operations to reduce costs and improve efficiency. 