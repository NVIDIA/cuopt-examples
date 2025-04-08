# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import time
import datetime
import pandas as pd


def get_minutes_from_datetime(str_timestamp):
    
    try:
        formater = "%Y-%m-%dT%H:%M:%S"
        timestamp = datetime.datetime.strptime(str_timestamp, formater)
    except ValueError as e:
        pass
    
    try:
        formater = "%Y-%m-%dT%H:%M:%S"
        timestamp = datetime.datetime.strptime(str_timestamp, formater)
    except ValueError as e:
        pass
    
    if (timestamp.hour * 60 + timestamp.minute) == 0:
        return 1440
    
    return timestamp.hour * 60 + timestamp.minute

# Prints vehicle routes
def show_vehicle_routes(resp, locations):

    solution = resp["vehicle_data"]
    for id in list(solution.keys()):
        route = solution[id]["route"]
        print("For vehicle -", id, "route is: \n")
        path = ""
        for index, route_id in enumerate(route):
            path += str(locations[route_id])
            if index != (len(route) - 1):
                path += "->"
        print(path + "\n\n")
        
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