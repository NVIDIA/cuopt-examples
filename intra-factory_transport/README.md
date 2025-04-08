# Intra-Factory Transport Optimization

This notebook demonstrates how to use NVIDIA cuOpt to solve an intra-factory transport optimization problem using the cuOpt SDK API. The example focuses on optimizing the routes for Autonomous Mobile Robots (AMRs) within a factory environment.

## Problem Overview

The notebook solves a Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW) where:

- Multiple AMRs with fixed capacities transport parts between processing stations
- Each transport order has specific pickup and delivery locations with time windows
- The factory has a defined waypoint graph that AMRs must follow
- AMRs have capacity constraints and must start/end at a depot location

## Key Features

- **Waypoint Graph**: Uses a compressed sparse row (CSR) representation of a weighted graph
- **Transport Orders**: Defines pickup and delivery pairs with associated demands and time windows
- **AMR Fleet**: Configures multiple AMRs with capacity constraints and operational hours
- **Route Optimization**: Solves for optimal routes that minimize total travel time while respecting all constraints

## How to Use

1. Ensure you have the required dependencies installed (see requirements.txt)
2. Run the notebook cells in sequence
3. The notebook will:
   - Set up the problem data structure
   - Configure transport orders and AMR fleet
   - Solve the optimization problem using the cuOpt SDK
   - Display the optimized routes for each AMR

## Expected Output

The notebook outputs:
- The total cost of the routing solution
- The number of vehicles used
- Detailed routes for each AMR showing the sequence of locations visited
- Waypoint-level routes for each AMR

This example is particularly useful for manufacturing environments where parts need to be transported between different processing stations in an efficient manner.
