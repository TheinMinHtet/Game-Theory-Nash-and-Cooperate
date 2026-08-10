import networkx as nx
from typing import Dict, List, Tuple
from core.graph import calculate_edge_cost

def get_path_edges(path_id: str) -> List[Tuple[str, str]]:
    if path_id == "Route 1 (Top)":
        return [("A", "B"), ("B", "D")]
    elif path_id == "Route 2 (Bot)":
        return [("A", "C"), ("C", "D")]
    return []

def get_best_selfish_path(graph: nx.DiGraph, current_edge_flows: Dict[Tuple[str, str], int]) -> Tuple[str, Dict[str, float]]:
    """
    Evaluates all available paths based on exactly how many cars are on them RIGHT NOW.
    Returns the selected path and the calculation estimates.
    """
    paths = ["Route 1 (Top)", "Route 2 (Bot)"]
    estimates = {}
    
    best_path = None
    best_cost = float('inf')
    
    for path in paths:
        edges = get_path_edges(path)
        path_cost = 0.0
        for u, v in edges:
            current_cars_on_edge = current_edge_flows.get((u, v), 0)
            # Evaluate cost if THIS new car joins the road (+1)
            path_cost += calculate_edge_cost(graph, u, v, current_cars_on_edge + 1)
            
        estimates[path] = path_cost
        
        if path_cost < best_cost:
            best_cost = path_cost
            best_path = path
            
    return best_path, estimates

def get_cooperative_distribution(total_vehicles: int) -> Dict[str, int]:
    """
    Calculates the System Optimum for N vehicles.
    System Optimum minimizes Total Delay = x * Cost1(x) + y * Cost2(y)
    Where Cost1 = (1.0x + 5) and Cost2 = (0.2y + 15)
    Total Delay = x(1.0x + 5) + (N-x)(0.2(N-x) + 15)
    Taking the derivative with respect to x and setting to 0 gives:
    x = (10 + 0.4 * N) / 2.4
    """
    optimum_x = (10 + 0.4 * total_vehicles) / 2.4
    route_1_count = int(round(optimum_x))
    
    # Constrain within bounds
    route_1_count = max(0, min(total_vehicles, route_1_count))
    route_2_count = total_vehicles - route_1_count
    
    return {
        "Route 1 (Top)": route_1_count,
        "Route 2 (Bot)": route_2_count
    }
