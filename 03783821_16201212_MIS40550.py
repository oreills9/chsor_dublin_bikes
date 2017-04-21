import networkx as nx
import requests
import json
from math import radians, cos, sin, asin, sqrt
import random
import numpy as np
from heapq import heappush, heappop
import csv

"""
The graph is a closed system representing the flow of Dublin bikes from station to station.
Information is available at each station for the state of every station in the sytem.
A station can be either empty or full. If it is full it is assumed to have no free spaces.
Alternatively, if it is empty it is assumed to have all free spaces and no available bikes.
"""

def create_node_graph_from_api(api_params):
    """
    Function to create a NetworkX directed graph from a set of stations from a
    real-world station list provided by JCDecaux open API
    :param api_params Contains the variables requires to create the graph (and store it)
    """

    # Create directed graph
    G = nx.DiGraph()

    # Connect to the JCDecaux API and retrieve the station JSON data from which we create the graph
    response = requests.get("https://api.jcdecaux.com/vls/v1/stations", params=api_params)
    stations = json.loads(response.text)
    people = 0
    # Create nodes
    for idx, rec in enumerate(stations):
        G.add_node(idx, name=rec['name'], long=rec['position']['lng'], lat=rec['position']['lat'], status=rec['status'], total=rec['bike_stands'], spaces=rec['available_bike_stands'], bikes=rec['available_bikes'], centre_dist=0)
        people += rec['available_bikes']
    # Retrieving co-ordinates for the station locations
    longs = nx.get_node_attributes(G, 'long')
    lats = nx.get_node_attributes(G, 'lat')

    # Calculate the centre point of the graph, this will give us a way of generate the direction of the edges
    centre_x, centre_y = calculate_centre_point(list(longs.values()), list(lats.values()))

    # Add the distance from the centre point as an attribute to the node attribute list
    centre_dist = {}
    for u in G.nodes():
        centre_dist[u] = haversine(longs[u], lats[u] , centre_y, centre_x)
    nx.set_node_attributes(G, 'centre_dist', centre_dist)

    # Create edges using the nodes
    create_edges_for_graph(G)
    return G, people

def create_random_graph(num_nodes, edge_prob):
    """
    Create real world graph or random graph
    :param num_nodes Number of nodes to be in the graph
    :param edge_prob Probability that an edge will be created between two nodes
    """
    return nx.erdos_renyi_graph(num_nodes, edge_prob, directed=True)

def create_edges_for_graph(G):
    """
    Creates directed edges for all nodes, based on the lcation of the station to the centre of the graph
    :param G NetworkX graph
    """

    # Retrieving co-ordinates and centre distance for the station locations
    longs = nx.get_node_attributes(G, 'long')
    lats = nx.get_node_attributes(G, 'lat')
    centre_dist = nx.get_node_attributes(G, 'centre_dist')

    nodes = G.nodes()
    for u in nodes:
        for v in nodes:
            # Determine if the u node is further from the centre of the graph than the v node
            if centre_dist[u] > centre_dist[v]:
                # Calculate distance from the u node to the v node
                dist = haversine(longs[u], lats[u], longs[v], lats[v])
                #Only allow edges to be created if the stations are less than 5km apart i.e. 30 mins away with an average speed of 10kph (otherwise it's a paid joourney)
                if dist <= 5:
                    dur = dist * 6  # Rough estimation of cycling duration, based on an average cycling speed of 10km/ph
                    G.add_edge(u, v, distance=dist, duration=dur)

def calculate_centre_point(longs, lats):
    """
    Function to calculate the centre point of the physical graph, based on the latitude and longitude values of the station locations
    :param lats Latitude values
    :param longs Longitude values
    """
    return np.mean(np.asarray(longs)), np.mean(np.asarray(lats))

def haversine(long1, lat1, long2, lat2):
    """
    Function taken from example found on
    http://stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
    Calculate the great circle distance between two points on the earth (specified in decimal degrees)
    :param long1 First longitude value
    :param lat1 First latitude value
    :param long2 Second longitude value
    :param lat2 Second latitude value
    """
    # convert decimal degrees to radians
    long1, lat1, long2, lat2 = map(radians, [long1, lat1, long2, lat2])

    # haversine formula
    dlong = long2 - long1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlong/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r

def centrality_list(cent_dict, am=True):
    """
    Return sorted list of desc order of node centrality
    :param cent_dict Dictionary of degree centralities for the nodes
    :am If it is morning time then there are a smaller number of central nodes.
    If not am then it is a larger number of outer nodes which have higher centrality
    """
    if am:
        cent = [(b,a) for (a,b) in cent_dict.items()]
    else:
        # Not AM so 1-centrality count and reverse the list
        cent = [(1 - b, a) for (a, b) in cent_dict.items()]
    return(sorted(cent, reverse=True))

def get_centre_count(cent_list, cent_ratio, am=True):
    """
    Get the number of center nodes to use to distribute traffic to.
    The higher the ratio the smaller the number of nodes traffic will flow towards
    :param cent_list: list of nodes with in degree centrality
    :param cent_ratio: the ratio we want to apply to calculate the number of nodes
    :param am: time of day, am or pm, default is AM
    :return: number which represents the number of nodes to be considered the centre
    """
    # Count of most central nodes
    central_count = len(cent_list)//cent_ratio
    if not am:
        # Not AM means we want to to simulate a traffic going to a higher
        # number of outer nodes rather than a smaller number of central.
        # There is no one outer center. So we reverse the flow of the AM
        central_count = len(cent_list) - central_count
    return(central_count)


def run(G, csv_file):
    """
    Main run function which kicks off the simulation
    :param G NetworkX graph
    """

    # Calculate in-degree centrality to represent flow of bikes to centre
    cent = nx.in_degree_centrality(G)
    # Add centrality values to each node
    for u in G.nodes():
        G.node[u]['in_cent'] = cent[u]

    # Get order of centrality with most central at start
    cent_list =  centrality_list(cent, am=False)
    [print(tup) for tup in cent_list]

    # Set up each station at start of run
    bikes_init(G)

    # Get the number of nodes we want to consider as the centre
    centre_num = get_centre_count(cent_list, centre_flow, am=False)
    print(centre_num)

    # Run program for number of steps
    for i in range(nsteps):
        print("STEP %d" % (i))
        bike_flow(G, cent_list, centre_num)
        csv_file.writerow((["REDISTRIBUTE VIA PEOPLE"]))
        [csv_file.writerow((n, i+1, G.node[n]['total'], G.node[n]['spaces'], G.node[n]['full'], G.node[n]['empty'])) for n in G.nodes()]
        empty_list = [(n, G.node[n]['in_cent'], G.node[n]['empty']) for n in G.nodes() if G.node[n]['empty'] >= 1]
        full_list = [(n, G.node[n]['in_cent'], G.node[n]['full']) for n in G.nodes() if G.node[n]['full'] >= 1]
        # Trucks can move bikes from full stations to less full stations
        csv_file.writerow((["REDISTRIBUTE VIA TRUCKS"]))
        #bike_trucks(G, 2, 10, cent_list)
        print("Full Count: %s\nEmpty Count %s" % (empty_list, full_list))

        [csv_file.writerow((n, i+1, G.node[n]['total'], G.node[n]['spaces'], G.node[n]['full'], G.node[n]['empty'])) for n in G.nodes()]

"""
Add bikes to one stations. This does not try and find other stations
It simply checks the chose station an returns true or false depending
on whether there is space to take the relevant action. If not a separate
function can find another suitable station or stations to allocate the bike
"""

def add_bikes(G, stations_list, bike_num, person=True):
    for stn in stations_list:
        spaces = G.node[stn[1]]['spaces']
        # Check if all bikes have been redistributed
        if bike_num <= 0:
            return(True)
        if spaces == 0:
            # No space so just go to next station
            continue
        elif spaces <= bike_num:
            # If there are some space drop some bikes and
            # go to next station with remaining bikes
            bike_num -= spaces
            # There are no spaces now so set this to zero
            G.node[stn[1]]['spaces'] = 0
            # If this is a truck moving bikes then ignore
            # Otherwise count it as person that cant add bike
            if person:
                G.node[stn[1]]['full'] += 1
            print("Put some bikes in %s, remaining %s" % (stn[1], bike_num))
        else:
            # There are more spaces than bikes so drop all bike
            # and reset station number
            G.node[stn[1]]['spaces'] -= bike_num
            bike_num = 0
            print("Put all bikes in %s, remaining %s" % (stn[1], bike_num))

def remove_bikes(G, stations_list, bike_num, person=True):
    """
    Function to remove bikes from the clculated station based on its centrality
    :param G NetworkX graph
    :param stations_list
    :param bike_num
    :param person
    """

    for stn in stations_list:
        spaces = G.node[stn[1]]['spaces']
        total = G.node[stn[1]]['total']
        spare_bikes = total - spaces
        # Check is all bikes have been redistributed
        if bike_num <= 0:
            return(True)
        if spare_bikes == 0:
            # Then there are no bikes, station is empty
            continue
        elif spare_bikes <= bike_num:
            # This means there are some bikes available
            # so take some bikes and move to next station
            bike_num -= spare_bikes
            # Reset station spaces
            G.node[stn[1]]['spaces'] += spare_bikes
            print("Removed some bikes in %s, remaining %s" % (stn[1], bike_num))
            # If truck is moving bikes it does not count
            # Only care is people cannot find a bike
            if person:
                G.node[stn[1]]['empty']+=1
        else:
            # There are more spare bikes than we need so
            # we can take all bikes from this station
            G.node[stn[1]]['spaces'] += bike_num
            bike_num = 0
            print("Removed all bikes in %s, remaining %s" % (stn[1], bike_num))

def bike_trucks(G, runs, num, central_list):
    """
    Trucks can collect bikes from full stations and move them to other stations
    First find stations with no free stations, then move to other, less central
    stations
    runs is the number of runs the truck can do, e.g. 1 run means it can move bikes from
    one station to another
    num is the number of bikes, in percentage, to move from station, e.g. 10 is 10% and so on
    """
    emptyq = []
    [heappush(emptyq, (-(graph.node[n]['in_cent']), n)) for n in graph.nodes() if graph.node[n]['full'] >= 1]
    for run in range(runs):
        if len(emptyq) > 0:
            station = heappop(emptyq)
            bikes = (G.node[station[1]]['total']*num)//100
            # pick up bikes from full station
            print("TRUCK: %d, %d, %d" % (station[1], G.node[station[1]]['spaces'], bikes))
            if check_station(graph, station[1], bikes, False, False):
                print("TRUCK COLLECT: %d, %d" % (station[1], G.node[station[1]]['spaces']))
                # Now move bikes to non central stations
                add_bikes(G, sorted(central_list, reverse=True), bikes, False)
    return(True)

def bikes_init(G):
    """
    Initialize each station at the start so that is have 50% spaces available
    """
    # Initial setup, create stations relative to centrality
    # and populate with 50% empty spaces
    for u in G.nodes():
        if "total" not in G.node[u]: # Check if total is populated already
            G.node[u]["total"] = int(10*G.node[u]['in_cent'])*10
        if "spaces" not in G.node[u]:# Check if spaces is populated already
            G.node[u]["spaces"] = int(G.node[u]["total"]/2)
        # Track how many times someone tried to take bike from station
        # and it was not available
        G.node[u]["empty"] = 0
        # Track how many times someone tried to put a bike in station
        # and there was no room
        G.node[u]["full"] = 0

def check_station(G, node, change, add=True, person=True):
    """
    Main run function which kicks off the simulation
    :param G NetworkX graph
    """

    spaces = G.node[node]['spaces']
    total = G.node[node]['total']
    spare_bikes = total - spaces
    #print("check station spaces: %s, total: %s, station: %s, bikes: %s" % (spaces, total, node, change))
    if add:
        if spaces >= change:
            G.node[node]['spaces'] -= change
            # If this is a truck moving bikes then ignore
            # Otherwise count it as person that cant add bike
            if person:
                if G.node[node]['spaces'] == 0:
                    G.node[node]['full'] += 1
            return(True)
        else:
            return(False)
    else:
        if spare_bikes >= change:
            G.node[node]['spaces'] += change
            # If truck is moving bikes it does not count
            # Only care if people cannot find a bike
            if person:
                if (total - G.node[node]['spaces']) == 0:
                    G.node[node]['empty'] += 1
            return(True)
        else:
            return(False)

def bike_flow(G, central_list, central_count):
    """
    One flow of number of bikes flow towards central nodes.
    This is one step to allocate a random number of bikes.
    Assume in-degree of centrality relates to flow of bikes.
    e.g. in morning this is toward high centrality, but in evening
    towards low centrality outer nodes.
    """
    # Get random number of bikes to move
    bike_count = random.randrange(1, 2)


    print("CENTRAL COUNT %d" % central_count)
    for person in range(people):
        print("PERSON: %d" % (person))
        [print(x) for x in G.nodes(data=True)]
        print("\n")
        # Bikes flow from less central nodes to more central in-degree nodes
        # We want to have more flow to these nodes i.e. adding bikes
        rand = random.uniform(0.1, 0.99)
        print(rand, central_list[central_count][0])
        if rand <= central_list[central_count][0]:
            # Randomly choose from most central stations
            node = random.randrange(0, central_count)
            print("NODE:%s" % node)
            # Add bikes to randomly selected station
            if check_station(G, node, bike_count, True):
                # There was room in destination station
                pass
            else:
                # Random station was empty so start with most central and work through
                # list to find a station to put the bike in
                add_bikes(G, central_list, bike_count)
        else:
            # Randomly add bikes to least central nodes
            node = random.randrange(central_count+1, len(central_list)-1)
            print("NON-CENTRAL-NODE:%s" % node)
            # Add bike to non central station based on random probability range
            if check_station(G, node, bike_count, True):
                # There was room in destination station
                pass
        # This is a closed system so need to remove corresponding bikes
        # from another less central station
        for neigh in G.neighbors(node):
            # Need to remove same bike count from other nodes
            # Since this is assumed to be a fully connected graph
            # And a closed system for counts, then one of the neighbours
            # will have to have space for these bikes.
            if check_station(G, neigh, bike_count, False):
                # We found station to remove a bike from so can move onto next step
                break

    print("Total - Spaces - Full - Empty")
    print(nx.get_node_attributes(G, 'total'))
    print(nx.get_node_attributes(G, 'spaces'))
    print(nx.get_node_attributes(G, 'full'))
    print(nx.get_node_attributes(G, 'empty'))
if __name__ == "__main__":

    # Adjustable parameters
    station_count = 10
    edge_prob = 0.4  # per-edge probability of existing
    total_bikes = 200
    centre_radius = 1  # radius distance in km which is considered to be city centre
    centre_prob = 0.1  # Probability to add/sub bike from centre locations
    nsteps = 20  # How many time steps to run
    centre_flow = 3  # % centrality we want traffic to flow to
    people = 20  # Number of people using scheme per run
    api_params = {"contract": "dublin", "apiKey": "52c182bc479e090926da33062b01aba1adc8e18c"}
    output_file = "bike_share.csv"
    file = open(output_file, 'wt')
    try:
        writer = csv.writer(file)
        writer.writerow(("Stations", "Bikes", "Steps", "People"))
        writer.writerow(("Node", "Run", "Total Spaces", "Remaining Spaces", "Full Count", "Empty Count"))

        #G1 = create_node_graph_from_api(api_params)
        G2 = create_random_graph(station_count, edge_prob)

        #print("G1 No. of nodes: %i" % G1.number_of_nodes())
        #print("G1 No. of edges: %i" % G1.number_of_edges())

        print("G2 No. of nodes: %i" % G2.number_of_nodes())
        print("G2 No. of edges: %i" % G2.number_of_edges())

        #run(G1, writer)
        run(G2, writer)
    finally:
        file.close()
