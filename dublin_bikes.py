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
centre_flow = 3# % centrality we want traffic to flow to
people = 50 # Number of people using scheme per step

def add_bikes(graph, stations_list, bike_num, person=True):
    for stn in stations_list:
        spaces = graph.node[stn[1]]['spaces']
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
            graph.node[stn[1]]['spaces'] = 0
            # If this is a truck moving bikes then ignore
            # Otherwise count it as person that cant add bike
            if person:
                graph.node[stn[1]]['full'] += 1
            print("Put some bikes in %s, remaining %s" % (stn[1], bike_num))
        else:
            # There are more spaces than bikes so drop all bike
            # and reset station number
            graph.node[stn[1]]['spaces'] -= bike_num
            bike_num = 0
            print("Put all bikes in %s, remaining %s" % (stn[1], bike_num))

def remove_bikes(graph, stations_list, bike_num, person=True):
    for stn in stations_list:
        spaces = graph.node[stn[1]]['spaces']
        total = graph.node[stn[1]]['total']
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
            graph.node[stn[1]]['spaces'] += spare_bikes
            print("Removed some bikes in %s, remaining %s" % (stn[1], bike_num))
            # If truck is moving bikes it does not count
            # Only care is people cannot find a bike
            if person:
                graph.node[stn[1]]['empty']+=1
        else:
            # There are more spare bikes than we need so
            # we can take all bikes from this station
            graph.node[stn[1]]['spaces'] += bike_num
            bike_num = 0
            print("Removed all bikes in %s, remaining %s" % (stn[1], bike_num))

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
            if check_station(graph, station[1], bikes, False, False):
                print("TRUCK COLLECT: %d, %d" % (station[1], graph.node[station[1]]['spaces']))
                # Now move bikes to non central stations
                add_bikes(graph, sorted(central_list, reverse=True), bikes, False)
    return(True)

def bikes_init(G):
    """
    Initialize each station at the start so that is have 50% spaces available
    """
    # Initial setup, create stations relative to centrality
    # and populate with 50% empty spaces
    for u in G.nodes():
        G.node[u]["total"] = int(10*G.node[u]['in_cent'])*10
        G.node[u]["spaces"] = G.node[u]["total"]/2
        # Track how many times someone tried to take bike from station
        # and it was not available
        G.node[u]["empty"] = 0
        # Track how many times someone tried to put a bike in station
        # and there was no room
        G.node[u]["full"] = 0

def check_station(graph, node, change, add=True, person=True):
    spaces = graph.node[node]['spaces']
    total = graph.node[node]['total']
    spare_bikes = total - spaces
    if add:
        if spaces >= change:
            graph.node[node]['spaces'] -= change
            # If this is a truck moving bikes then ignore
            # Otherwise count it as person that cant add bike
            if person:
                if graph.node[node]['spaces'] == 0:
                    graph.node[node]['full'] += 1
            return(True)
        else:
            return(False)
    else:
        if spare_bikes >= change:
            graph.node[node]['spaces'] += change
            # If truck is moving bikes it does not count
            # Only care if people cannot find a bike
            if person:
                if (total - graph.node[node]['spaces']) == 0:
                    graph.node[node]['empty'] += 1
            return(True)
        else:
            return(False)

def centrality_list(cent_dict):
    """Return sorted list of desc order of node centrality"""
    cent = [(b,a) for (a,b) in cent_dict.items()]
    return(sorted(cent, reverse=True))

def am_cycle(G, central_list):
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
    central_count = len(central_list)//centre_flow
    for person in range(people):
        # Bikes flow from less central nodes to more central in-degree nodes
        # We want to have more flow to these nodes i.e. adding bikes
        if random.uniform(0.55, 0.99) <= central_list[central_count][0]:
            # Randomly choose from most central stations
            node = random.randrange(0, central_count)
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
    bikes_init(G)

    # Run program for number of steps
    for i in range(nsteps):
        am_cycle(G, cent_list)
        empty_list = [(n, G.node[n]['in_cent'], G.node[n]['empty']) for n in G.nodes() if G.node[n]['empty'] >= 1]
        full_list = [(n, G.node[n]['in_cent'], G.node[n]['full']) for n in G.nodes() if G.node[n]['full'] >= 1]
        # Trucks can move bikes from full stations to less full stations
        bike_trucks(G, 2, 10, cent_list)
        print("Full Count: %s\nEmpty Count %s" % (empty_list, full_list))

if __name__ == "__main__":
    run()

