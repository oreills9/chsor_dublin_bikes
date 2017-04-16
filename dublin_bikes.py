import networkx as nx
import random

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
nsteps = 20 # How many time steps to run
centre_flow = 3 # % centrality we want traffic to flow to


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

    # Set up each station at start of run
    bikes_refresh(G, init=True)

    # Run program for number of steps
    for i in range(nsteps):
        am_cycle(G, cent_list)
        empty_count = sum(G.node[i]["empty"] for i in G.nodes())
        print("%2d %.2d" % (i, empty_count))

if __name__ == "__main__":
    run()
