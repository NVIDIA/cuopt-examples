# Last-Mile Delivery Optimization

This section demonstrates how to use NVIDIA cuOpt to solve last-mile delivery optimization problems. The notebooks focus on optimizing routes for delivery vehicles and service technicians to various locations.

## Examples

### 1. Delivery Vehicle Routing (CVRP)

The delivery vehicle routing notebook solves a Capacitated Vehicle Routing Problem (CVRP) where:

- A fleet of delivery vehicles with different capacities must deliver packages from a micro fulfillment center
- Each delivery location has a specific demand that must be fulfilled
- The delivery fleet consists of vehicles with different capacities (trucks and vans)
- The goal is to minimize the total distance traveled by all vehicles while satisfying all delivery demands

#### Key Features

- **Cost Matrix**: Uses a distance-based cost matrix to represent travel costs between locations
- **Demand Modeling**: Incorporates varying demand requirements for different delivery locations
- **Heterogeneous Fleet**: Configures multiple vehicle types with different capacities
- **Constraint Handling**: Demonstrates adding constraints such as minimum vehicle utilization
- **Visualization**: Includes visualization of optimized routes

### 2. Service Team Routing (CVRPTW)

The service team routing notebook (`cvrptw_service_team_routing.ipynb`) solves a Capacitated Vehicle Routing Problem with Time Windows (CVRPTW) where:

- Service technicians with different capabilities must visit customer locations to perform services
- Each service location has specific time windows when service must begin
- Service technicians have different skills (represented as capacity to handle different service types)
- Each technician has limited availability (time windows for their work shifts)
- The goal is to minimize the total travel time while ensuring all services are completed within their respective time windows

#### Key Features

- **Time Windows**: Handles both service location time windows and technician availability windows
- **Multi-Dimensional Capacity**: Models technicians with different capabilities for different service types
- **Service Times**: Incorporates time spent at each service location
- **Skill Matching**: Automatically matches technicians to services they're qualified to perform
- **Visualization**: Includes visualization of optimized routes with respect to time constraints

## How to Use

1. Ensure you have the required dependencies installed (see requirements.txt)
2. Run the notebook cells in sequence
3. The notebooks will:
   - Set up the problem data with locations and demands/service requirements
   - Configure the vehicle/technician fleet with appropriate capacities
   - Define the distance/time matrix between locations
   - Solve the optimization problem using the cuOpt Python API
   - Display and visualize the optimized routes for each vehicle/technician

## Expected Output

The notebooks output:
- The total cost (distance/time) of the routing solution
- The number of vehicles/technicians used in the solution
- Detailed routes for each vehicle/technician showing the sequence of locations visited
- Visual representation of the optimized routes

These examples are particularly useful for:
- Retailers and logistics companies looking to optimize their last-mile delivery operations
- Field service organizations scheduling technicians with different skills
- Any business that needs to schedule visits to customer locations while respecting time windows and capacity constraints 