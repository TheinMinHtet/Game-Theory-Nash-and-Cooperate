import networkx as nx
from typing import Dict

def create_base_graph() -> nx.DiGraph:
    """
    Creates a standard routing network from Node A to Node D.
    Paths:
    Route 1 (Top): A -> B -> D
    Route 2 (Bot): A -> C -> D
    """
    G = nx.DiGraph()
    G.add_node("A", pos=(150, 250))
    # Route 1 nodes (Completely straight horizontal path)
    G.add_node("B", pos=(400, 250)) 
    # Route 2 nodes (Loops way down as a heavy physical detour)
    G.add_node("C", pos=(400, 500)) 
    G.add_node("D", pos=(650, 250))
    
    # Route 1 (Fast but highly susceptible to congestion)
    G.add_edge("A", "B", cost=(1.0, 5.0), original_cost_fn=lambda x: (x * 1.0) + 5.0)
    G.add_edge("B", "D", cost=(1.0, 5.0), original_cost_fn=lambda x: (x * 1.0) + 5.0)
    
    # Route 2 (Slow base speed, but handles congestion much better)
    G.add_edge("A", "C", cost=(0.2, 15.0), original_cost_fn=lambda x: (x * 0.2) + 15.0)
    G.add_edge("C", "D", cost=(0.2, 15.0), original_cost_fn=lambda x: (x * 0.2) + 15.0)
    
    return G

def calculate_edge_cost(G: nx.DiGraph, u: str, v: str, flow: int) -> float:
    # flow is the EXACT CURRENT active vehicles on this edge right now
    coeff, const = G[u][v]['cost']
    return (coeff * flow) + const
