import uvicorn
import threading
import asyncio
from api.routes import app, simulation

def run_uvicorn():
    # Setup a new event loop for the child thread to avoid async errors
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run server without passing "import string", directly pass the app instance
    # This prevents Uvicorn from attempting to use the reloader or spawn subprocesses.
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    t = threading.Thread(target=run_uvicorn, daemon=True)
    t.start()
    
    # Run Pygame in the MAIN thread
    simulation.start(in_main_thread=True)
