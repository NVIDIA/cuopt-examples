# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd

# Used to plot the Co-ordinates
def gen_plot(df):
    plt.figure(figsize=(11, 11))
    plt.scatter(
        df["xcord"][:1],
        df["ycord"][:1],
        label="Depot",
        color="Green",
        marker="o",
        s=100,
    )
    plt.scatter(
        df["xcord"][1::],
        df["ycord"][1::],
        label="Locations",
        color="Red",
        marker="o",
        s=100,
    )
    plt.xlabel("x - axis")
    # frequency label
    plt.ylabel("y - axis")
    # plot title
    plt.title("Simplified Map")
    # showing legend
    plt.legend()

    for i, label in enumerate(df.index.values):
        plt.annotate(
            label,
            (df["xcord"][i], df["ycord"][i]),
            fontproperties=fm.FontProperties(size=16),
        )
    return plt


# Used to plot arrows
def add_arrows(df, route, plt, color="green"):
    prev_cord = ()
    for i, label in enumerate(route):
        if i > 0:
            plt.annotate(
                "",
                xy=(df["xcord"][label], df["ycord"][label]),
                xytext=prev_cord,
                arrowprops=dict(
                    arrowstyle="simple, head_length=0.5, head_width=0.5, tail_width=0.15",  # noqa
                    connectionstyle="arc3",
                    color=color,
                    mutation_scale=20,
                    ec="black",
                ),
                label="vehicle-1",
            )
        prev_cord = df["xcord"][label], df["ycord"][label]

    return plt


# Convert the solver response from the server to a cuDF dataframe
# for waypoint graph problems
def get_solution_df(resp):
    solution = resp["vehicle_data"]

    df = {}
    df["route"] = []
    df["truck_id"] = []
    df["location"] = []
    types = []

    for vid, route in solution.items():
        df["location"] = df["location"] + route["route"]
        df["truck_id"] = df["truck_id"] + [vid] * len(route["route"])
        if "type" in list(route.keys()):
            types = types + route["type"]
    if len(types) != 0:
        df["types"] = types
    df["route"] = df["location"]

    return pd.DataFrame(df)


# Prints vehicle routes
def show_vehicle_routes(resp, locations):

    solution = resp["vehicle_data"]
    for id in list(solution.keys()):
        route = solution[id]["route"]
        print("For vehicle -", id, "route is: \n")
        path = ""
        for index, route_id in enumerate(route):
            path += locations[route_id]
            if index != (len(route) - 1):
                path += "->"
        print(path + "\n\n")


# Map vehicle routes
def map_vehicle_routes(df, resp, colors):

    solution = resp["vehicle_data"]

    plt = gen_plot(df)
    veh_ids = list(solution.keys())
    idx = 0
    vid_map = {}
    for v_id in veh_ids:
        vid_map[v_id] = idx
        idx = idx + 1

    for v_id in veh_ids:
        plt = add_arrows(
            df, solution[v_id]["route"], plt, color=colors[vid_map[v_id]]
        )

    return plt


def create_from_file(file_path, is_pdp=False):
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
            # if count == 36:
            #     break

    vehicle_num = int(vehicle_num)
    vehicle_capacity = int(vehicle_capacity)
    df = pd.DataFrame(
        columns=[
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
    )

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
    for veh_id, veh_data in response["vehicle_data"].items():

        print("\nVehicle Id :", veh_id)
        print("Route :", veh_data["route"])
        print("Type :", veh_data["type"])
        print("Task Id :", veh_data["task_id"])
        print("Arrival Stamp :", veh_data["arrival_stamp"])
        print("--------------------------------------------------------")
