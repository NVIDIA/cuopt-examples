# Car Rental Optimization

A Mixed Integer Linear Program (MILP) example for optimizing fleet size, vehicle distribution, and transfer operations to maximize weekly profit.

**Adapted from**: [Gurobi's Vehicle Rental Optimization Model](https://www.gurobi.com/jupyter_models/vehicle-rental-optimization/)

## Problem Overview

A car rental company needs to determine:
- How many cars to have in their fleet
- Where to position cars each day across multiple locations
- How many cars to transfer between locations

**Goal**: Maximize weekly profit while meeting demand and minimizing costs

## Model Assumptions

**Important**: This model uses simplified assumptions suitable for same-day rental operations:

1. **Same-day rentals**: All cars rented are returned to the same location by end of day
2. **Daily optimization**: Decisions made on a 7-day planning horizon
3. **Known demand**: Rental demand is deterministic
4. **Homogeneous fleet**: All vehicles are identical
5. **Overnight transfers**: Car movements happen overnight

This formulation works well for:
- Car-sharing services (Zipcar, Car2Go)
- Airport shuttle operations
- Daily urban rental businesses

**Note**: Traditional multi-day rentals with one-way returns require additional variables and constraints (see notebook conclusion for extensions).

## Notebook Contents

### Setup & Data
- 4 locations (Airport, Downtown, 2 Suburbs)
- 7-day demand patterns
- Revenue rates by location ($75-$120/rental)
- Weekly operational cost ($240/car)
- Transfer costs between locations

### Optimization
- **Decision Variables**: Fleet size (integer), availability, rentals, transfers (continuous)
- **Objective**: Maximize revenue - operational costs - transfer costs
- **Constraints**: Demand limits, availability, flow conservation, fleet capacity

### Results & Analysis
- Optimal fleet size and allocation
- Financial metrics (profit, margins, costs)
- Utilization rates by location
- Demand satisfaction tracking
- Transfer operation schedules
- Interactive visualizations (heatmaps, charts)

## Quick Start

```bash
jupyter notebook car_rental_optimization_milp.ipynb
```

## Possible Extensions

**Multi-day Rentals** (see notebook for details):
- Track rental duration and expected returns
- Model one-way rentals between locations
- Add reservation system with time windows

**Additional**:
- Multiple vehicle classes
- Seasonal demand patterns
- Maintenance scheduling
- Stochastic demand
- Dynamic pricing

