# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES.
# All rights reserved.
# SPDX-License-Identifier: MIT
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions: The above copyright
# notice and this permission notice shall be included in all copies or
# substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd


# Used to plot the Co-ordinates
def gen_plot(df):
    """
    Generate a plot with the locations.
    
    Args:
        df: DataFrame with location coordinates (xcord, ycord)
        
    Returns:
        matplotlib plot object
    """
    plt.figure(figsize=(11, 11))
    
    # Plot depot (first location)
    plt.scatter(
        df["xcord"][:1],
        df["ycord"][:1],
        label="Depot",
        color="Green",
        marker="o",
        s=100,
    )
    
    # Plot other locations
    plt.scatter(
        df["xcord"][1:],
        df["ycord"][1:],
        label="Locations",
        color="Red",
        marker="o",
        s=100,
    )
    
    plt.xlabel("x - axis")
    plt.ylabel("y - axis")
    plt.title("Simplified Map")
    plt.legend()

    # Add location labels
    for i, label in enumerate(df.index.values):
        plt.annotate(
            label,
            (df["xcord"][i], df["ycord"][i]),
            fontproperties=fm.FontProperties(size=16),
        )
    
    return plt


# Used to plot arrows
def add_arrows(df, route, plt, color="green"):
    """
    Add directional arrows to the plot to represent a route.
    
    Args:
        df: DataFrame with location coordinates
        route: List of location indices representing the route
        plt: matplotlib plot object
        color: Color for the arrows
        
    Returns:
        matplotlib plot object with arrows added
    """
    prev_cord = ()
    for i, label in enumerate(route):
        if i > 0:
            arrow_props = dict(
                arrowstyle="simple, head_length=0.5, head_width=0.5, tail_width=0.15",
                connectionstyle="arc3",
                color=color,
                mutation_scale=20,
                ec="black",
            )
            plt.annotate(
                "",
                xy=(df["xcord"][label], df["ycord"][label]),
                xytext=prev_cord,
                arrowprops=arrow_props,
                label=f"vehicle-{i}",
            )
        prev_cord = df["xcord"][label], df["ycord"][label]

    return plt


# Convert the solver response to a pandas dataframe for mapping
def get_solution_df(solution):
    """
    Converts a solution object to a pandas DataFrame
    
    Args:
        solution: A cuOpt routing.Solution object
    
    Returns:
        pandas.DataFrame: Contains the route information
    """
    # Check if it's a new API solution object
    if hasattr(solution, 'get_route'):
        # New API solution object
        routes_df = solution.get_route()
        return routes_df.to_pandas() if hasattr(routes_df, 'to_pandas') else routes_df
    
    # Check if it's a dictionary with vehicle_data key (legacy API)
    if isinstance(solution, dict) and "vehicle_data" in solution:
        solution_dict = solution["vehicle_data"]
        df = {}
        df["route"] = []
        df["truck_id"] = []
        df["location"] = []
        types = []

        for vid, route in solution_dict.items():
            df["location"] = df["location"] + route["route"]
            df["truck_id"] = df["truck_id"] + [vid] * len(route["route"])
            if "type" in list(route.keys()):
                types = types + route["type"]
        if len(types) != 0:
            df["types"] = types
        df["route"] = df["location"]

        return pd.DataFrame(df)
    
    # If solution is already a DataFrame, return it directly
    if isinstance(solution, pd.DataFrame):
        return solution
        
    # If we reach here, we don't recognize the format
    raise TypeError("Unrecognized solution format. Must be a Solution object, a response dictionary, or a DataFrame.")


# Prints vehicle routes
def show_vehicle_routes(solution, locations):
    """
    Print the vehicle routes in a readable format.
    
    Args:
        solution: cuOpt routing.Solution object
        locations: List of location names corresponding to indices
    """
    # Get route DataFrame from solution
    routes_df = solution.get_route()
    
    # Convert to pandas if it's a cudf DataFrame
    if hasattr(routes_df, 'to_pandas'):
        routes_df = routes_df.to_pandas()
        
    # Display routes for each vehicle
    for v_id in routes_df['truck_id'].unique():
        vehicle_route = routes_df[routes_df['truck_id'] == v_id]
        route_locations = vehicle_route['route'].tolist()
        
        print(f"For vehicle {v_id} route is:")
        path_parts = [locations[loc] for loc in route_locations]
        route_str = " → ".join(path_parts)
        print(route_str)
        print()


# Map vehicle routes
def map_vehicle_routes(df, solution, colors):
    """
    Creates a plot visualizing vehicle routes.
    
    Args:
        df: DataFrame with location coordinates
        solution: cuOpt routing.Solution object
        colors: List of colors to use for different vehicles
    
    Returns:
        matplotlib plot object with routes visualized
    """
    # Initialize plot with locations
    plt = gen_plot(df)
    
    # Get routes from solution
    routes_df = solution.get_route()
    
    # Convert to pandas if it's a cudf DataFrame
    if hasattr(routes_df, 'to_pandas'):
        routes_df = routes_df.to_pandas()
        
    # Get unique vehicle IDs
    vehicle_ids = routes_df['truck_id'].unique()
    
    # Create a mapping from vehicle ID to color index
    vid_map = {vid: i % len(colors) for i, vid in enumerate(vehicle_ids)}
    
    # Draw routes for each vehicle
    for v_id in vehicle_ids:
        v_route = routes_df[routes_df['truck_id'] == v_id]
        route_locs = v_route['route'].tolist()
        plt = add_arrows(
            df, 
            route_locs, 
            plt, 
            color=colors[vid_map[v_id]]
        )
    
    return plt


def calculate_route_metrics(solution, cost_matrix, locations=None):
    """
    Calculate metrics for the routes in a solution.
    
    Args:
        solution: cuOpt routing.Solution object
        cost_matrix: Matrix of costs between locations
        locations: Optional list of location names
        
    Returns:
        DataFrame with route metrics
    """
    routes_df = solution.get_route()
    
    # Convert to pandas if it's a cudf DataFrame
    if hasattr(routes_df, 'to_pandas'):
        routes_df = routes_df.to_pandas()
    
    # Convert cost_matrix to pandas DataFrame if it's not already
    if hasattr(cost_matrix, 'to_pandas'):
        cost_matrix = cost_matrix.to_pandas()
    
    results = []
    
    for v_id in routes_df['truck_id'].unique():
        v_route = routes_df[routes_df['truck_id'] == v_id]
        route_locs = v_route['route'].tolist()
        
        # Calculate route distance
        route_distance = 0
        for i in range(len(route_locs) - 1):
            from_loc = route_locs[i]
            to_loc = route_locs[i + 1]
            route_distance += cost_matrix.iloc[from_loc, to_loc]
        
        # Format route as string if location names are provided
        route_str = ""
        if locations:
            route_str = " → ".join([locations[loc] for loc in route_locs])
        
        results.append({
            "vehicle_id": v_id,
            "num_stops": len(route_locs) - 2,  # Exclude depot at start and end
            "route_distance": route_distance,
            "route": route_str
        })
    
    return pd.DataFrame(results)


def print_solution_summary(solution, cost_matrix=None, locations=None):
    """
    Print a summary of the solution.
    
    Args:
        solution: cuOpt routing.Solution object
        cost_matrix: Optional cost matrix to calculate actual distances
        locations: Optional list of location names
    """
    # Get basic solution metrics
    total_objective = solution.get_total_objective()
    vehicle_count = solution.get_vehicle_count()
    
    print(f"Solution Status: {solution.get_status()}")
    print(f"Total Objective Value: {total_objective:.2f}")
    print(f"Vehicles Used: {vehicle_count}")
    print()
    
    # If cost matrix is provided, calculate detailed metrics
    if cost_matrix is not None:
        metrics = calculate_route_metrics(solution, cost_matrix, locations)
        
        print("Route Details:")
        for _, row in metrics.iterrows():
            print(f"Vehicle {row['vehicle_id']}:")
            print(f"  Stops: {row['num_stops']}")
            print(f"  Distance: {row['route_distance']:.2f}")
            if row['route']:
                print(f"  Route: {row['route']}")
            print()
        
        total_dist = metrics['route_distance'].sum()
        print(f"Total Distance: {total_dist:.2f}")


def create_from_file(file_path, is_pdp=False):
    """
    Create a DataFrame from a problem file.
    
    Args:
        file_path: Path to the problem file
        is_pdp: Whether the file is a pickup and delivery problem
        
    Returns:
        Tuple of (df, vehicle_capacity, vehicle_num)
    """
    node_list = []
    with open(file_path, "rt") as f:
        count = 1
        for line in f:
            if is_pdp and count == 1:
                vehicle_num, vehicle_capacity, speed = line.split()
            elif not is_pdp and count == 5:
                vehicle_num, vehicle_capacity = line.split()
            elif is_pdp:
                node_list.append(line.split())
            elif count >= 10:
                node_list.append(line.split())
            count += 1

    vehicle_num = int(vehicle_num)
    vehicle_capacity = int(vehicle_capacity)
    
    columns = [
        "vertex",
        "xcord",
        "ycord",
        "demand",
        "earliest_time",
        "latest_time",
        "service_time",
        "pickup_index",
        "delivery_index",
    ]
    df = pd.DataFrame(columns=columns)

    for item in node_list:
        row = {
            "vertex": int(item[0]),
            "xcord": float(item[1]),
            "ycord": float(item[2]),
            "demand": int(item[3]),
            "earliest_time": int(item[4]),
            "latest_time": int(item[5]),
            "service_time": int(item[6]),
        }
        if is_pdp:
            row["pickup_index"] = int(item[7])
            row["delivery_index"] = int(item[8])
        df = pd.concat([df, pd.DataFrame(row, index=[0])], ignore_index=True)

    return df, vehicle_capacity, vehicle_num


def print_data(data, completed_tasks):
    print("Completed tasks :", completed_tasks)
    print("Pending tasks :", data["task_locations"])
    print("Pickup indices :", data["pickup_indices"])
    print("Delivery indices :", data["delivery_indices"])
    print("Task Earliest :", data["task_earliest_time"])
    print("Task Latest :", data["task_latest_time"])
    print("Task Service :", data["task_service_time"])
    print("Vehicle locations :", data["vehicle_locations"])
    print("Vehicle earliest :", data["vehicle_earliest"])
    print("Order vehicle match :", data["order_vehicle_match"])


def print_vehicle_data(response):
    """
    Print detailed vehicle data from solution
    
    Args:
        response: Either a cuOpt routing.Solution object or a dictionary response
    """
    # Handle new API solution object
    if hasattr(response, 'get_route'):
        routes_df = response.get_route()
        
        # Convert to pandas if it's a cudf DataFrame
        if hasattr(routes_df, 'to_pandas'):
            routes_df = routes_df.to_pandas()
            
        # Group by truck_id and print information
        for vehicle_id in routes_df['truck_id'].unique():
            vehicle_route = routes_df[routes_df['truck_id'] == vehicle_id]
            
            print(f"\nVehicle Id: {vehicle_id}")
            print(f"Route: {vehicle_route['route'].tolist()}")
            if 'type' in vehicle_route.columns:
                print(f"Type: {vehicle_route['type'].tolist()}")
            if 'arrival_time' in vehicle_route.columns:
                print(f"Arrival Time: {vehicle_route['arrival_time'].tolist()}")
            print("--------------------------------------------------------")
        return
    
    # Check if it's a dictionary with vehicle_data key (legacy API)
    if isinstance(response, dict) and "vehicle_data" in response:
        for veh_id, veh_data in response["vehicle_data"].items():
            print("\nVehicle Id :", veh_id)
            print("Route :", veh_data["route"])
            print("Type :", veh_data["type"])
            print("Task Id :", veh_data["task_id"])
            print("Arrival Stamp :", veh_data["arrival_stamp"])
            print("--------------------------------------------------------")
        return
    
    # If response is a DataFrame, process it directly
    if isinstance(response, pd.DataFrame) and 'truck_id' in response.columns and 'route' in response.columns:
        for vehicle_id in response['truck_id'].unique():
            vehicle_route = response[response['truck_id'] == vehicle_id]
            
            print(f"\nVehicle Id: {vehicle_id}")
            print(f"Route: {vehicle_route['route'].tolist()}")
            if 'type' in vehicle_route.columns:
                print(f"Type: {vehicle_route['type'].tolist()}")
            if 'arrival_time' in vehicle_route.columns:
                print(f"Arrival Time: {vehicle_route['arrival_time'].tolist()}")
            print("--------------------------------------------------------")
        return
    
    # If we reach here, we don't recognize the format
    raise TypeError("Unrecognized solution format. Must be a Solution object, a response dictionary, or a DataFrame.")
