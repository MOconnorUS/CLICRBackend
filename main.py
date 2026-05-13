from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict
from contextlib import asynccontextmanager
from db import DB
from models import UpdateBody
    
### NOTE: We need to add an error handling check when we migrate to phase 3 to check if the venue exists and if it doesn't
### We need to return the appropriate value

db = DB()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Establish the connection with our database and setup a yield for cleanup functions after shutdown. For the time being there will
    be no cleanup functions but when we implement Redis we will want it to flush the cache to the supabase DB.

    ::param app the FastAPI backend app
    """

    db.establish_connection()
    yield

app = FastAPI(lifespan=lifespan)

active_connections: dict[str, dict[str, list[WebSocket] | int]] = {}

async def broadcast(venue: str):
    """
    Initial websocket broadcasting function to send the live count to all those listening on the websocket. Phase 2 will send socket specific information.

    ::param count the live count int
    ::param entered the people entered
    ::param exited the people exited
    """
    
    if venue in active_connections:
        for connection in active_connections[venue]["ws"]:
            await connection.send_json(
                {
                    "count": active_connections[venue]["liveCount"], 
                    "entered": active_connections[venue]["entered"], 
                    "exited": active_connections[venue]["exited"]
                }
            )

@app.websocket("/ws/{venue}")
async def websocket_endpoint(websocket: WebSocket, venue: str):
    """
    Initial websocket endpoint. This will serve as phase 1 of 2 with websockets to establish a single live connection. Phase 2 will have per venue sockets

    ::param websocket the websocket connection
    """
    
    await websocket.accept()

    if venue not in active_connections:
        active_connections[venue] = {
            "ws": [],
            "liveCount": 0,
            "entered": 0,
            "exited": 0
        }

    active_connections[venue]["ws"].append(websocket)

    await initial_data(venue)

    try:
        while True:
            data = await websocket.receive_json()

            if data["action"] == "increment":
                active_connections[venue]["entered"] += 1
                db.update(venue, active_connections[venue]["entered"], "people_entered")
                
            elif data["action"] == "decrement":
                active_connections[venue]["exited"] += 1
                db.update(venue, active_connections[venue]["exited"], "people_exited")

            active_connections[venue]["liveCount"] = max(0, active_connections[venue]["entered"] - active_connections[venue]["exited"])
            db.update(venue, active_connections[venue]["liveCount"])

            await broadcast(venue)
    except Exception as e:
        print(f'WebSocket Exception: {e}')
        active_connections[venue]["ws"].remove(websocket)

async def initial_data(venue: str):
    """
    Grabs the initial data from the database via fetch and sends it to be broadcasted.
    """

    entered = 0
    exited = 0
    liveCount = 0

    try:
        entered = db.fetch(venue, "people_entered")
    except Exception as e:
        return {f"Error fetching people entered for {venue}": str(e)}
    
    if type(entered) is str:
        return {f"Failed to fetch people entered for {venue}": "Fail"}
    
    try:
        exited = db.fetch(venue, "people_exited")
    except Exception as e:
        return {f"Error fetching people exited for {venue}": str(e)}
    
    if type(exited) is str:
        return {f"Failed to fetch people exited for {venue}": str(e)}

    try:
        liveCount = db.fetch(venue, "live_count")
    except Exception as e:
        return {f"Error fetching live count for {venue}": str(e)}
    
    if type(liveCount) is str:
        return {f"Failed to fetch live count for {venue}": "Fail"}
    
    active_connections[venue]["liveCount"] = liveCount
    active_connections[venue]["entered"] = entered
    active_connections[venue]["exited"] = exited
    
    await broadcast(venue)


@app.get("/health_check")
async def ping():
    return {"result": "healthy"}    
