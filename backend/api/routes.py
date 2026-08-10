from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from simulation.pygame_env import TrafficSimulation

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulation = TrafficSimulation()

class SimParams(BaseModel):
    mode: str
    with_shortcut: bool
    total_vehicles: int

@app.on_event("startup")
async def startup_event():
    pass
    
@app.on_event("shutdown")
async def shutdown_event():
    simulation.stop()

@app.post("/api/simulation/params")
async def set_params(params: SimParams):
    simulation.set_parameters(params.mode, params.with_shortcut, params.total_vehicles)
    return {"status": "ok"}

@app.websocket("/ws/simulation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Poll simulation state and send to client
            state = simulation.get_state()
            await websocket.send_json(state)
            await asyncio.sleep(0.5) # Send state every 0.5 seconds
    except WebSocketDisconnect:
        pass
