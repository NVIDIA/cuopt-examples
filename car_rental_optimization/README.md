# Car Rental Optimization

This example demonstrates how to solve a car rental optimization problem using cuOpt's GPU-accelerated linear programming solver.

## Problem Description

A car rental company operates across multiple locations and needs to make strategic decisions about:
- **Fleet Size**: How many cars to purchase for their fleet
- **Vehicle Distribution**: Where to position cars each day
- **Transfer Operations**: How many cars to transfer between locations

The objective is to **maximize weekly profit** by:
- Meeting rental demand at each location
- Minimizing transfer costs between locations
- Optimizing vehicle utilization

## Problem Formulation

This is formulated as a **Mixed Integer Linear Program (MILP)** with:

### Decision Variables
- `fleet_size`: Total number of cars to purchase (integer)
- `available[d][l]`: Number of cars available at location `l` on day `d`
- `rented[d][l]`: Number of cars rented at location `l` on day `d`
- `transfer[d][i][j]`: Number of cars transferred from location `i` to `j` on day `d`

### Objective Function
Maximize:
```
Total Revenue - Purchase Costs - Transfer Costs
```

### Constraints
1. **Demand constraint**: Cars rented cannot exceed demand at each location
2. **Availability constraint**: Cars rented cannot exceed available cars
3. **Flow conservation**: Maintains vehicle balance across days and locations
4. **Fleet size constraint**: Total cars in system cannot exceed fleet size

## Files

- **`car_rental_optimization_milp.ipynb`**: Main Jupyter notebook with complete implementation

## Key Features

- ✅ GPU-accelerated optimization using cuOpt
- ✅ Comprehensive visualizations with heatmaps and charts
- ✅ Detailed business insights and performance metrics
- ✅ Transfer operation analysis and cost breakdown
- ✅ Utilization and demand satisfaction tracking

## Example Scenario

The notebook includes a realistic scenario with:
- **4 Locations**: Airport, Downtown, Suburb A, Suburb B
- **7 Days**: Monday through Sunday
- **Variable Demand**: Different demand patterns across locations and days
- **Transfer Costs**: Distance-based costs for moving cars between locations
- **Revenue Optimization**: Different rental rates for different locations

## Results

The optimization provides:

### Financial Insights
- Optimal fleet size recommendation
- Expected profit and ROI
- Revenue breakdown by location
- Transfer cost analysis

### Operational Insights
- Daily vehicle allocation by location
- Transfer schedules between locations
- Utilization rates for each location
- Demand satisfaction metrics

### Visualizations
- Demand heatmaps
- Availability and rental patterns
- Utilization rate analysis
- Revenue breakdown charts

## Prerequisites

- NVIDIA GPU with CUDA support
- cuOpt SDK installed
- Python packages: `numpy`, `pandas`, `matplotlib`, `seaborn`

## Usage

```bash
jupyter notebook car_rental_optimization_milp.ipynb
```

Or run in Google Colab with GPU runtime enabled.

## Inspiration

This example is adapted from the [Gurobi Vehicle Rental Optimization Model](https://www.gurobi.com/jupyter_models/vehicle-rental-optimization/), demonstrating how to solve similar problems with cuOpt's GPU-accelerated solver.

## Extensions

This example can be extended to include:
- Multiple vehicle types (compact, SUV, luxury)
- Seasonal demand variations
- Maintenance schedules and vehicle downtime
- Stochastic demand modeling
- Multi-week or monthly optimization horizons
- Dynamic pricing strategies
- Customer reservation patterns

## Related Examples

- [Diet Optimization](../diet_optimization/) - Another MILP example with cuOpt
- [Workforce Optimization](../workforce_optimization/) - Assignment problem using cuOpt
- [Portfolio Optimization](../portfolio_optimization/) - Financial optimization with cuOpt

## References

- [NVIDIA cuOpt Documentation](https://docs.nvidia.com/cuopt/)
- [Gurobi Vehicle Rental Model](https://www.gurobi.com/jupyter_models/vehicle-rental-optimization/)
- [cuOpt Examples Repository](https://github.com/NVIDIA/cuopt-examples)

