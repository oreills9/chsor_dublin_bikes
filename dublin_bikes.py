import networkx as nx
import random
from heapq import heappush, heappop

"""
The graph is a closed system representing the flow of Dublin bikes from station to station.
Information is available at each station for the state of every station in the sytem.
A station can be either empty or full. If it is full it is assumed to have no free spaces.
Alternatively, if it is empty it is assumed to have all free spaces and no available bikes.
"""
station_count = 40
edge_prob = 0.9 # per-edge probability of existing
total_bikes = 2000
centre_radius = 1 # radius distance in km which is considered to be city centre
centre_prob = 0.1 # Probabilty to add/sub bike from centre locations
nsteps = 200 # How many time steps to run
centre_flow = 2 # % centrality we want traffic to flow to
people = 50 # Number of people using scheme per step

def move_bikes(graph, stations_list, bike_num):
    for stn in stations_list:
        avail = graph.node[stn[1]]['spaces']
        # Check is all bikes have been redistributed
        if bike_num<=0:
            return(True)
        if avail == 0:
            # No space so just go to next station
            continue
        elif avail < bike_num:
            # If there are some space drop some bikes and
            # go to next station with remaining
            bike_num -= avail
            # Reset station spaces
            avail = 0
            print("Put some bikes in %s, remaining %s" % (stn[1], bike_num))
        else:
            # There are more spaces than bikes so drop all bike
            # and reset station number
            avail -= bike_num
            bike_num = 0
            print("Put all bikes in %s, remaining %s" % (stn[1], bike_num))

def bike_trucks(graph, runs, num, central_list):
    """
    Trucks can collect bikes from full stations and move them to other stations
    First find stations with no free stations, then move to other, less central
    stations
    runs is the number of runs the truck can do, e.g. 1 run means it can move bikes from
    one station to another
    num is the number of bikes, in percentage, to move from station, e.g. 10 is 10% and so on
    """
    emptyq = []
    [heappush(emptyq, (-(graph.node[n]['in_cent']), n)) for n in graph.nodes() if graph.node[n]['empty'] >= 1]
    for run in range(runs):
        if len(emptyq) > 0:
            station = heappop(emptyq)
            bikes = (graph.node[station[1]]['total']*num)//100
            # pick up bikes from full station
            print("TRUCK: %d, %d" % (station[1], graph.node[station[1]]['spaces']))
            if change_spaces(graph, station[1], bikes, False):
                print("TRUCK COLLECT: %d, %d" % (station[1], graph.node[station[1]]['spaces']))
                # Now move bikes to non central stations
                move_bikes(graph, sorted(central_list, reverse=True), bikes)
    return(True)



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
            return(False)
    else:
        if graph.node[node]['spaces'] <= change:
            graph.node[node]['spaces'] += change
            return(True)
        else:
            return(False)

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
    bike_count = random.randrange(1, 2)
    # Count of most central nodes
    central_count = len(centrality)//centre_flow
    for person in range(people):
        # Bikes flow from less central nodes to more central in-degree nodes
        # We want to have more flow to these nodes i.e. adding bikes
        if random.uniform(0.55, 0.99) <= centrality[central_count][0]:
            # Randomly add bikes to most central nodes
            node = random.randrange(0, central_count)
            if change_spaces(G, node, bike_count, True):
                for neigh in G.neighbors(node):
                    # Need to remove same bike count from other nodes
                    # Since this is assumed to be a fully connected graph
                    # And a closed system for counts, then one of the neighbours
                    # will have to have space for these bikes.
                    if change_spaces(G, neigh, bike_count, False):
                        # We found station to remove a bike from so can move onto next step
                        break
            # Check for amount of times station was full
            if G.node[node]['spaces'] == 0:
                G.node[node]['empty'] += 1
        else:
            # Randomly add bikes to least central nodes
            node = random.randrange(central_count+1, len(centrality)-1)
            # Add bike to non central station at lower frequency (i.e. probablity)
            if change_spaces(G, node, bike_count, True):
                for neigh in G.neighbors(node):
                    # Need to remove same bike count from other nodes
                    if change_spaces(G, neigh, bike_count, False):
                        break
            # Check for amount of times station was full
            if G.node[node]['spaces'] == 0:
                G.node[node]['empty'] += 1

def run():
    # Create real world graph or random graph
    G = nx.erdos_renyi_graph(station_count, edge_prob, directed=True)
    # Calculate in-degree centrality to represent flow of bikes to centre
    cent = nx.in_degree_centrality(G)
    # Add centrality values to each node
    for u in G.nodes():
        G.node[u]['in_cent'] = cent[u]

    # Get order of centrality with most central at start
    cent_list = centrality_list(cent)
    print(cent_list)

    # Set up each station at start of run
    bikes_refresh(G, init=True)

    # Run program for number of steps
    for i in range(nsteps):
        am_cycle(G, cent_list)
        empty_list = [(n, G.node[n]['in_cent'], G.node[n]['empty']) for n in G.nodes() if G.node[n]['empty'] >= 1]
        # Trucks can move bikes from full stations to less full stations
        bike_trucks(G, 2, 10, cent_list)
        print("%s" % (empty_list))

if __name__ == "__main__":
    run()

