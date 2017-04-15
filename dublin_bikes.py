import networkx as nx
import random

"""
The graph is a closed system representing the flow of Dublin bikes from station to station.
Information is available at each station for the state of every station in the sytem.
A station can be either empty or full. If it is full it is assumed to have no free spaces.
Alternatively, if it is empty it is assumed to have all free spaces and no available bikes.
"""
total_bikes = 2000
centre_radius = 1 # radius distance in km which is considered to be city centre
centre_prob = 0.1 # Probabilty to add/sub bike from centre locations
nsteps = 20 # How many time steps to run

def get_central_dist():
    dist=0
    """Need to check how close node is to city centre"""
    return(dist)

def change_spaces(node_data, change, add=True):
    if add:
        if node_data['spaces'] >= change:
            node_data['spaces'] -= change
            return(True)
    else:
        if node_data['spaces'] <= change:
            node_data['spaces'] += change
            return(True)

def am_cycle(G):
    """
    One cycle in AM where bikes flow towards central nodes
    This is one step to allocate a random number of bikes
    """
    # Get random number of bikes to move
    bike_count = random.randrange(1, 5)
    for node, data in G.nodes(data=True):
        if get_central_dist(data['spaces']) < centre_radius:
            # It is in city centre perimeter so move bikes accordingly
            if random.random() > centre_prob:
                # Add bike to station if possible
                if change_spaces(data, bike_count, True):
                    for neigh, neigh_data in G.neighbours(node):
                        # Need to remove same bike count from other nodes
                        # Since this is assumed to be a fully connected graph
                        # And a closed system for counts, then one of the neighbours
                        # will have to have space for these bikes.
                        change_spaces(neigh_data, bike_count, True)
                else:
                    #Check for amount of times station was full
                    if data['spaces'] = 0:
                        data['empty']+=1
            else:
                # Remove bike from  station
                if change_spaces(data, bike_count, False):
                    for neigh, neigh_data in G.neighbours(node):
                        # Need to remove same bike count from other nodes
                        change_spaces(neigh_data, bike_count, False)


def run():
    # Get real world graph or random graph
    G = generate_bike_graph()

    #Run program for number of steps
    for i in range(nsteps):
        am_cycle(G)
        empty_count = sum(G.node[i]["empty"] for i in G.nodes())
        print("%2d %.2f" % (i, empty_count))


if __name__ == "__main__":
    run()

