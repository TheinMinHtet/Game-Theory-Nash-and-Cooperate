import pygame
import threading
import time
import uuid
import json
import os
import math
from typing import Dict, Tuple
from core.graph import create_base_graph, calculate_edge_cost
from core.routing import get_path_edges, get_best_selfish_path, get_cooperative_distribution

class Vehicle:
    def __init__(self, v_id, path_id, path_nodes_pos, estimated_time=0.0):
        self.id = v_id
        self.path_id = path_id
        self.path_nodes_pos = path_nodes_pos
        self.current_edge_index = 0
        self.progress = 0.0
        self.start_time = time.time()
        self.end_time = None
        self.estimated_time = estimated_time
        self.done = False

class TrafficSimulation:
    def __init__(self):
        self.running = False
        self.thread = None
        
        self.total_vehicles = 50
        self.mode = "selfish"
        self._spawn_timer = 0
        
        self.vehicles = []
        self.completed_vehicles = []
        self._results_exported = False
        self.decision_logs = []
        
        self.graph = create_base_graph()
        self.flows = {}
        
        self.lock = threading.Lock()
        
    def start(self, in_main_thread=False):
        if not self.running:
            self.running = True
            self._reset_sim()
            if in_main_thread:
                self._run_pygame()
            else:
                self.thread = threading.Thread(target=self._run_pygame, daemon=True)
                self.thread.start()
            
    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2.0)
                
    def set_parameters(self, mode: str, with_shortcut: bool, total_vehicles: int):
        with self.lock:
            self.mode = mode
            self.total_vehicles = total_vehicles
            self.graph = create_base_graph()
            self._reset_sim()
            
    def _reset_sim(self):
        self.vehicles.clear()
        self.completed_vehicles.clear()
        self._results_exported = False
        self.graph = create_base_graph()
        
        if self.mode == "cooperative":
            self.flows = get_cooperative_distribution(self.total_vehicles)
            self._spawn_queue = []
            for path_id, count in self.flows.items():
                self._spawn_queue.extend([path_id] * count)
            import random
            random.shuffle(self._spawn_queue)
        else:
            self.flows = {} # Dynamically evaluated
            self._spawn_queue = [None] * self.total_vehicles
            
    def _export_results(self):
        results = {
            "mode": self.mode,
            "total_vehicles": self.total_vehicles,
            "route_distribution": self.flows,
            "average_actual_time": sum([v.end_time - v.start_time for v in self.completed_vehicles]) / max(len(self.completed_vehicles), 1),
            "vehicles": []
        }
        for v in self.completed_vehicles:
            results["vehicles"].append({
                "id": str(v.id),
                "path": v.path_id,
                "estimated_time_at_spawn": v.estimated_time,
                "actual_time_visual": v.end_time - v.start_time
            })
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(script_dir, "..", "results.json")
        with open(path, "w") as f:
            json.dump(results, f, indent=4)
        print(f"Exported results to {path}")
        
    def _run_pygame(self):
        pygame.init()
        screen = pygame.display.set_mode((900, 650))
        pygame.display.set_caption("Dynamic AV Traffic Simulator")
        clock = pygame.time.Clock()
        
        font = pygame.font.SysFont("segoeui, arial", 26, bold=True)
        small_font = pygame.font.SysFont("segoeui, arial", 16, bold=True)
        log_font = pygame.font.SysFont("consolas, courier", 14)

        while self.running:
            # Clean Map-like background (Light light gray)
            screen.fill((240, 244, 248))
            
            with self.lock:
                if self._spawn_queue:
                    self._spawn_timer += 1
                    # Spawn next vehicle every 50 frames (nearly a full second) so user can see it spawn
                    if self._spawn_timer >= 50:
                        self._spawn_timer = 0
                        item = self._spawn_queue.pop(0)

                        active_flows = self._calculate_current_edge_flows()
                        
                        # Even in cooperative, we will evaluate paths so the user can see *why* it is optimal 
                        _, estimates = get_best_selfish_path(self.graph, active_flows)
                        
                        if self.mode == "cooperative":
                            path_id = item
                            est = 0.0
                            self.decision_logs = [
                                "[CO-OP OVERRIDE ENFORCED]",
                                f"Eval Route 1: {estimates.get('Route 1 (Top)', 0):.1f}s",
                                f"Eval Route 2: {estimates.get('Route 2 (Bot)', 0):.1f}s",
                                f"-> System Assigned: {path_id}"
                            ]
                        else:
                            # Dynamic real-time selfish evaluation!
                            path_id = min(estimates, key=estimates.get)
                            est = estimates[path_id]
                            self.flows[path_id] = self.flows.get(path_id, 0) + 1
                            
                            self.decision_logs = [
                                "[NASH GREEDY DECISION]",
                                f"Eval Route 1: {estimates.get('Route 1 (Top)', 0):.1f}s",
                                f"Eval Route 2: {estimates.get('Route 2 (Bot)', 0):.1f}s",
                                f"-> Selfish Pick: {path_id}"
                            ]
                            
                        path_edges = get_path_edges(path_id)
                        nodes = [path_edges[0][0]] + [e[1] for e in path_edges]
                        nodes_pos = [self.graph.nodes[n]['pos'] for n in nodes]
                        self.vehicles.append(Vehicle(uuid.uuid4(), path_id, nodes_pos, est))
                        
                active_flows = self._calculate_current_edge_flows()
                
                for v in self.vehicles:
                    if v.done: continue
                    
                    current_edge_nodes = get_path_edges(v.path_id)[v.current_edge_index]
                    edge_flow = active_flows.get(current_edge_nodes, 0)
                    
                    cost = calculate_edge_cost(self.graph, current_edge_nodes[0], current_edge_nodes[1], edge_flow)
                    step = 1.0 / max(cost, 1.0) 
                    step *= 0.01
                    
                    v.progress += step
                    
                    if v.progress >= 1.0:
                        v.current_edge_index += 1
                        v.progress = 0.0
                        if v.current_edge_index >= len(v.path_nodes_pos) - 1:
                            v.done = True
                            v.end_time = time.time()
                            self.completed_vehicles.append(v)
                            
                            if len(self.completed_vehicles) == self.total_vehicles and not self._results_exported:
                                self._export_results()
                                self._results_exported = True
                                
                self.vehicles = [v for v in self.vehicles if not v.done]
            
            for u, v in self.graph.edges():
                start_pos = self.graph.nodes[u]['pos']
                end_pos = self.graph.nodes[v]['pos']
                
                # Asphalt road color base
                base_color = (203, 213, 225) # Light gray roads
                edge_flow = active_flows.get((u, v), 0)
                
                ratio = min(edge_flow / 25.0, 1.0)
                if ratio > 0:
                    r = int(203 + (239 - 203) * ratio)
                    g = int(213 + (68 - 213) * ratio)
                    b = int(225 + (68 - 225) * ratio)
                    road_color = (r, g, b)
                else:
                    road_color = base_color
                    
                # Clean simple thick lines for roads
                pygame.draw.line(screen, (148, 163, 184), start_pos, end_pos, 16) # Road Border
                pygame.draw.line(screen, road_color, start_pos, end_pos, 14)    # Road fill
                
                # Simple elegant hover text without ugly box
                current_cost = calculate_edge_cost(self.graph, u, v, edge_flow)
                mid_x = (start_pos[0] + end_pos[0]) // 2
                # Shift text significantly higher to avoid any overlap with the road or cars
                mid_y = (start_pos[1] + end_pos[1]) // 2 - 38
                
                cost_text = small_font.render(f"Delay: {current_cost:.1f}s", True, (71, 85, 105)) # Slate text
                text_rect = cost_text.get_rect(center=(mid_x, mid_y))
                # Soft white halo behind text for readability natively
                pygame.draw.rect(screen, (255,255,255), text_rect.inflate(8,4), border_radius=4)
                screen.blit(cost_text, text_rect)
                
            # Draw premium nodes
            for n in self.graph.nodes():
                pos = self.graph.nodes[n]['pos']
                pygame.draw.circle(screen, (255, 255, 255), pos, 22) # White rim
                pygame.draw.circle(screen, (51, 65, 85), pos, 18)   # Solid center
                text = font.render(n, True, (255, 255, 255))
                screen.blit(text, text.get_rect(center=pos))
                
            # Draw 2.5D Cars
            for v in self.vehicles:
                p1 = v.path_nodes_pos[v.current_edge_index]
                p2 = v.path_nodes_pos[v.current_edge_index + 1]
                
                cx = p1[0] + (p2[0] - p1[0]) * v.progress
                cy = p1[1] + (p2[1] - p1[1]) * v.progress
                
                # Calculate angle for rotation
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                angle = math.atan2(dy, dx)
                
                # Colors
                car_color = (14, 165, 233) if v.path_id == "Route 1 (Top)" else (236, 72, 153)
                roof_color = (224, 242, 254) if v.path_id == "Route 1 (Top)" else (252, 231, 243)
                
                # Create a car surface to allow rotation
                car_w, car_h = 24, 12
                car_surf = pygame.Surface((car_w, car_h), pygame.SRCALPHA)
                
                # Main body (Shadow box for 2.5D)
                pygame.draw.rect(car_surf, (0, 0, 0, 50), (2, 2, car_w, car_h), border_radius=3)
                # Main body color
                pygame.draw.rect(car_surf, car_color, (0, 0, car_w, car_h), border_radius=3)
                
                # Roof (offset slightly back and up to give 2.5D illusion)
                pygame.draw.rect(car_surf, (51, 65, 85), (6, 2, 8, 8), border_radius=2) # Windshield dark
                pygame.draw.rect(car_surf, roof_color, (4, 3, 7, 6), border_radius=2)   # Roof light top
                
                # Rotate and draw
                rotated_car = pygame.transform.rotate(car_surf, -math.degrees(angle))
                car_rect = rotated_car.get_rect(center=(int(cx), int(cy)))
                screen.blit(rotated_car, car_rect)
            
            # Clean UI Dashboard HUD
            hud_bg = pygame.Surface((340, 240), pygame.SRCALPHA)
            pygame.draw.rect(hud_bg, (255, 255, 255, 230), hud_bg.get_rect(), border_radius=12)
            pygame.draw.rect(hud_bg, (203, 213, 225, 200), hud_bg.get_rect(), width=1, border_radius=12)
            # Soft shadow
            pygame.draw.rect(screen, (0, 0, 0, 10), hud_bg.get_rect(topleft=(22, 22)), border_radius=12)
            screen.blit(hud_bg, (20, 20))
            
            mode_color = (16, 185, 129) if self.mode == "cooperative" else (14, 165, 233)
            text_mode = font.render(f"{self.mode.upper()}", True, mode_color)
            
            text_flows = small_font.render(f"TOP ROUTE: {self.flows.get('Route 1 (Top)', 0)}  |  BOT ROUTE: {self.flows.get('Route 2 (Bot)', 0)}", True, (71, 85, 105))
            text_active = small_font.render(f"ACTIVE VEHICLES: {len(self.vehicles)}", True, (71, 85, 105))
            
            screen.blit(text_mode, (40, 35))
            screen.blit(text_flows, (40, 70))
            screen.blit(text_active, (40, 95))
            
            # Terminal log (clean style)
            pygame.draw.line(screen, (226, 232, 240), (40, 125), (320, 125)) # Divider
            for i, line in enumerate(self.decision_logs):
                # Bold title for decision, gray for evaluations
                color = (234, 88, 12) if i == 0 else (100, 116, 139) 
                sys_lbl = log_font.render(line, True, color) 
                screen.blit(sys_lbl, (40, 135 + (i * 22)))
            
            pygame.display.flip()
            clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
        pygame.quit()

    def _calculate_current_edge_flows(self) -> Dict[Tuple[str, str], int]:
        edge_counts = {}
        for v in self.vehicles:
            if not v.done:
                edge = get_path_edges(v.path_id)[v.current_edge_index]
                edge_counts[edge] = edge_counts.get(edge, 0) + 1
        return edge_counts

    def calculate_theoretical_delay(self) -> float:
        edge_flows = {}
        for path, count in self.flows.items():
            edges = get_path_edges(path)
            for u, v in edges:
                edge_flows[(u, v)] = edge_flows.get((u, v), 0) + count
                
        total_delay = 0
        for path, count in self.flows.items():
            path_time = 0
            edges = get_path_edges(path)
            for u, v in edges:
                path_time += calculate_edge_cost(self.graph, u, v, edge_flows.get((u, v), 0))
            total_delay += path_time * count
        return total_delay / max(self.total_vehicles, 1)

    def get_state(self):
        with self.lock:
            avg_time = 0
            if self.completed_vehicles:
                total = sum([v.end_time - v.start_time for v in self.completed_vehicles])
                avg_time = total / len(self.completed_vehicles)
                
            return {
                "active_vehicles": len(self.vehicles),
                "completed_vehicles": len(self.completed_vehicles),
                "avg_travel_time": avg_time,
                "theoretical_total_delay": self.calculate_theoretical_delay(),
                "mode": self.mode,
                "route_1_count": self.flows.get("Route 1 (Top)", 0),
                "route_2_count": self.flows.get("Route 2 (Bot)", 0)
            }
