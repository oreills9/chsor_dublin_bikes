import networkx as nx
import requests
import json
import pandas as pd
import os.path as path
from math import radians, cos, sin, asin, sqrt

api_params = {"contract": "dublin", "apiKey": "52c182bc479e090926da33062b01aba1adc8e18c"}

def create_node_graph_from_API(contract, apiKey):
    G = nx.Graph()
    response = requests.get("https://api.jcdecaux.com/vls/v1/stations", params = api_params)
    stations = json.loads(response.text)
    for rec in stations:
        G.add_node(rec['number'], name=rec['name'], lat=rec['position']['lat'], long=rec['position']['lng'], status=rec['status'], bike_stands=rec['bike_stands'], available_bike_stands=rec['available_bike_stands'], available_bikes=rec['available_bikes'])

    return G

def create_edges_for_graph(G, useRoads, cacheFile=None, apiKey=None):
    edges = ()
    if useRoads == True:                # Use Google Distance Matrix distance
        if path.isFile(cacheFile):  # Call Google Distance Matrix API and store in location cache file
            read_cached_data(G, cacheFile)
        else:               # Use API location cache file
            if apiKey == None:
                print("Invalid Google Distance Matrix API key...exiting program...")
                return
            for n in G.nodes():
                return
            api_params = {"units": "metric", "travel_modes": "bicycling", "origins": origins,
                          "destinations": calculate_destinations(G, currentNode), "apiKey": apiKey}
            #response = requests.get("https://maps.googleapis.com/maps/api/distancematrix/json", params=api_params)
            #distances = json.loads(response.text)

    else:                               # Use straight line distance
        if path.isFile(cacheFile):
            read_cached_data(G, cacheFile)
        else:
            read_write_cached_data(G, cacheFile)

def calculate_destinations(G, u):
    return 0

def read_cached_data(G, source):
    data = pd.read_csv(source, sep=",", header=None)
    for u, v, dist, dur in data.iterrows():
        G.add_edge(u, v, distance=dist, duration=dur)

def read_write_cached_data(G, source):
    edges = []
    for u in G.nodes().sort():
        for v in G.nodes().sort():
            if u >= v:
                dist = haversine(u['lat'], u['long'], v['lat'], v['long'])
                dur = dist * 4  # Rough estimation of cycling duration, based on an average cycling speed of 15km/ph
                G.add_edge(u, v, distance=dist, duration=dur)
                edges.append([u, v, dist, dur])
    pd.to_csv(edges, map)

#Function taken from example found on http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

if __name__ == "__main__":

    api_params = {"contract": "dublin", "apiKey": "52c182bc479e090926da33062b01aba1adc8e18c"}
    G = create_node_graph_from_API(api_params['contract'], api_params['apiKey'])
    print(G.number_of_nodes())
    create_edges_for_graph(G, False, "latLongDist.csv", None)