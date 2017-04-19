import networkx as nx
import requests
import json
import pandas as pd
import os.path as osp
from math import radians, cos, sin, asin, sqrt
import random
import numpy as np

api_params = {"contract": "dublin", "apiKey": "52c182bc479e090926da33062b01aba1adc8e18c"}

def create_node_graph_from_api(contract, apiKey):
    """
    """
    G = nx.DiGraph()
    response = requests.get("https://api.jcdecaux.com/vls/v1/stations", params = api_params)
    stations = json.loads(response.text)
    for rec in stations:
        G.add_node(rec['number'], name=rec['name'], lat=rec['position']['lat'], long=rec['position']['lng'], status=rec['status'], bike_stands=rec['bike_stands'], available_bike_stands=rec['available_bike_stands'], available_bikes=rec['available_bikes'], centre_dist=0)

    lats = nx.get_node_attributes(G, 'lat')
    longs = nx.get_node_attributes(G, 'long')
    centreX, centreY = calculate_centre_point(list(lats.values()), list(longs.values()))
    centre_dist = {}
    for u in G.nodes():
        centre_dist[u] = haversine(lats[u], longs[u], centreX, centreY)
    nx.set_node_attributes(G, 'centre_dist', centre_dist)

    create_edges_for_graph(G, False, 'latlong.csv', None)
    return G

def create_random_graph(num_nodes, edge_prob):
    """
    """
    return nx.erdos_renyi_graph(num_nodes, edge_prob, directed=True)

def create_edges_for_graph(G, useRoads, cacheFile, apiKey=None):
    """
    """
    if osp.isfile(cacheFile):
        read_cached_data(G, cacheFile)
    else:
        read_write_cached_data(G, cacheFile)

def read_cached_data(G, source):
    """
    """
    data = pd.read_csv(source, sep=",", header=None)
    for u, v, dist, dur in data.iterrows():
        G.add_edge(u, v, distance=dist, duration=dur)

def calculate_centre_point(lats, longs):
    return np.mean(np.asarray(lats)), np.mean(np.asarray(longs))

def read_write_cached_data(G, source):
    """
    """
    lats = nx.get_node_attributes(G, 'lat')
    longs = nx.get_node_attributes(G, 'long')
    centre_dist = nx.get_node_attributes(G, 'centre_dist')
    nodes = G.nodes()
    for u in nodes:
        for v in nodes:
            if centre_dist[u] > centre_dist[v]:
                dist = haversine(lats[u], longs[u], lats[v], longs[v])
                if dist <= 5:
                    dur = dist * 6  # Rough estimation of cycling duration, based on an average cycling speed of 10km/ph
                    G.add_edge(u, v, distance=dist, duration=dur)

#
def haversine(lon1, lat1, lon2, lat2):
    """
    Function taken from example found on
    http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
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

def calculate_graph_centrality_list(G):
    # Calculate in-degree centrality to represent flow of bikes to centre
    cent = nx.in_degree_centrality(G)
    # Add centrality values to each node
    for u in G.nodes():
        G.node[u]['in_cent'] = cent[u]

    # Get order of centrality with most central at start
    return centrality_list(cent)


def run(G):
    cent_list = calculate_graph_centrality_list(G)

    # Set up each station at start of run
    bikes_refresh(G, init=True)

    # Run program for number of steps
    for i in range(nsteps):
        am_cycle(G, cent_list)
        empty_count = sum(G.node[i]["empty"] for i in G.nodes())
        print("%2d %.2d" % (i, empty_count))

def bikes_refresh(G, station=0, new_count=0, init=False):
    """
    Refresh bikes at a station or all stations.
    station is the node you want to reset
    spaces is the new available spaces for that node
    init, optional, if set to True then reset all stations
    """
    if init:
        # Initial setup, create stations relative to centrality
        # and populate with 50% empty spaces
        for u in G.nodes():
            G.node[u]["total"] = int(10*G.node[u]['in_cent'])*10
            G.node[u]["spaces"] = G.node[u]["total"]/2
            G.node[u]["empty"] = 0
    else:
        # Reset specifc station, e.g. due to truck distribution
        station['spaces'] = new_count


def change_spaces(graph, node, change, add=True):
    if add:
        if graph.node[node]['spaces'] >= change:
            graph.node[node]['spaces'] -= change
            return(True)
    else:
        if graph.node[node]['spaces'] <= change:
            graph.node[node]['spaces'] += change
            return(True)

def centrality_list(cent_dict):
    """Return sorted list of desc order of node centrality"""
    cent = [(b,a) for (a,b) in cent_dict.items()]
    return(sorted(cent, reverse=True))

def am_cycle(G, centrality):
    """
    One cycle in AM where bikes flow towards central nodes
    This is one step to allocate a random number of bikes.
    Assume in-degree of centrality relates to flow of bikes.
    e.g. in morning this is toward high centrality, but in evening
    towards low centrality
    """
    # Get random number of bikes to move
    bike_count = random.randrange(1, 5)
    # Go through the nodes until we
    for node, data in G.nodes(data=True):
        # Check if it is in top 30% of centrality weighting
        # We want to have more flow to these nodes i.e. adding bikes
        if random.random() >= centrality[len(centrality)//3][0]:
            # Add bike to station if possible
            if change_spaces(G, node, bike_count, True):
                for neigh in G.neighbors(node):
                    # Need to remove same bike count from other nodes
                    # Since this is assumed to be a fully connected graph
                    # And a closed system for counts, then one of the neighbours
                    # will have to have space for these bikes.
                    change_spaces(G, neigh, bike_count, True)
                else:
                    #Check for amount of times station was full
                    if data['spaces'] == 0:
                        data['empty'] += 1
            else:
                # Remove bike from  station
                if change_spaces(G, node, bike_count, False):
                    for neigh in G.neighbors(node):
                        # Need to remove same bike count from other nodes
                        change_spaces(G, neigh, bike_count, False)

if __name__ == "__main__":

    # Adjustable parameters
    centre_radius = 1  # radius distance in km which is considered to be city centre
    centre_prob = 0.1  # Probabilty to add/sub bike from centre locations
    nsteps = 20  # How many time steps to run
    centre_flow = 3  # % centrality we want traffic to flow to
    api_params = {"contract": "dublin", "apiKey": "52c182bc479e090926da33062b01aba1adc8e18c"}

    G1 = create_node_graph_from_api(api_params['contract'], api_params['apiKey'])
    #print("G1 No. of nodes: %i" % G1.number_of_nodes())
    #print("G1 No. of edges: %i" % G1.number_of_edges())

    G2 = create_random_graph(100, 0.4) # 0.4 generated from the approx. stops that a cyclist can get to in 30 mins, assuming a 10kph speed on average
    #print("G2 No. of nodes: %i" % G2.number_of_nodes())
    #print("G2 No. of edges: %i" % G2.number_of_edges())

    run(G1)
    run(G2)