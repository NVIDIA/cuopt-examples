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

import polyline
import folium
import folium.plugins as plugins
import pandas as pd
import requests
import polyline
import folium
import folium.plugins as plugins
import pandas as pd
import requests

def get_map_by_vehicle(curr_route_df, prize_collection):
    
    curr_lat_lon_coords = curr_route_df[["Latitude","Longitude"]].values.tolist()
    if prize_collection == True:
        prize_collection_status = curr_route_df["preferred_members"].to_list()
        m = get_map(curr_lat_lon_coords, prize_collection_status)
    else:
        m = get_map(curr_lat_lon_coords, [])
    
    return m



def get_map(my_lat_longs, prize_collection_status):

    m = folium.Map(location=my_lat_longs[1],
                   zoom_start=12)
    count = 0 
    
    for src_idx in range(len(my_lat_longs))[:-1]:
        dst_idx = src_idx + 1
        
        source = my_lat_longs[src_idx]
        destination = my_lat_longs[dst_idx]
        
        route = get_route(source[1], source[0], destination[1], destination[0])
        
        folium.PolyLine(
                route['route'],
                weight=5,
                color='blue',
                opacity=0.6
            ).add_to(m)
        
        if src_idx == 0:
            folium.Marker(
                location=[my_lat_longs[src_idx][0],my_lat_longs[src_idx][1]],
                icon=folium.Icon(color="green",icon="fa-building", prefix='fa')
            ).add_to(m)
        if prize_collection_status != [] and prize_collection_status[src_idx]==1:
                folium.Marker(
                    location=[my_lat_longs[src_idx][0],my_lat_longs[src_idx][1]],
                    icon=plugins.BeautifyIcon(
                             icon="arrow-down", icon_shape="marker",
                             number=src_idx,
                             border_color= 'blue',
                         )
                ).add_to(m)

        else:
            """
            folium.Marker(
                location=route['start_point'],
                icon=folium.Icon(color="blue",icon="fa-map-pin", prefix='fa')
            ).add_to(m)
            """
            folium.Marker(
                location=[my_lat_longs[src_idx][0],my_lat_longs[src_idx][1]],
                icon=plugins.BeautifyIcon(
                         icon="arrow-down", icon_shape="marker",
                         number=src_idx,
                         border_color= 'green',
                     )
            ).add_to(m)

    return m

def get_route(source_long, source_lat, dest_long, dest_lat):
    loc = "{},{};{},{}".format(source_long, source_lat, dest_long, dest_lat)
    url = "http://router.project-osrm.org/route/v1/driving/"
    r = requests.get(url + loc) 

    res = r.json()   
    routes = polyline.decode(res['routes'][0]['geometry'])
    start_point = [res['waypoints'][0]['location'][1], res['waypoints'][0]['location'][0]]
    end_point = [res['waypoints'][1]['location'][1], res['waypoints'][1]['location'][0]]
    distance = res['routes'][0]['distance']
    
    out = {'route':routes,
        'start_point':start_point,
        'end_point':end_point,
        'distance':distance
    }
    
    return out
