from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict
from contextlib import asynccontextmanager
from db import DB
from models import UpdateBody

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

active_connections: dict[str, list[WebSocket]] = {}

@app.websocket("/ws/{venue}")
async def websocket_endpoint(websocket: WebSocket, venue: str):
    """
    Initial websocket endpoint. This will serve as phase 1 of 2 with websockets to establish a single live connection. Phase 2 will have per venue sockets

    ::param websocket the websocket connection
    """
    
    await websocket.accept()

    if venue not in active_connections:
        active_connections[venue] = []

    active_connections[venue].append(websocket)

    await initial_data(venue)

    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f'WebSocket Exception: {e}')
        active_connections[venue].remove(websocket)

async def broadcast(venue: str, count: int, entered: int, exited: int):
    """
    Initial websocket broadcasting function to send the live count to all those listening on the websocket. Phase 2 will send socket specific information.

    ::param count the live count int
    ::param entered the people entered
    ::param exited the people exited
    """
    
    if venue in active_connections:
        for connection in active_connections[venue]:
            await connection.send_json({"count": count, "entered": entered, "exited": exited})

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
    
    await broadcast(venue, liveCount, entered, exited)


@app.get("/health_check")
async def ping():
    return {"result": "healthy"}

@app.patch("/update") 
async def update_entry(body: UpdateBody):
    """
    Asynchronous backend API route to update the people entered and exited in the Supabase Database and then broadcast the live count.

    ::param body the UpdateBody model to handle the body information
    """

    passUpdates = False
    entered = 0
    exited = 0
    liveCount = 0

    try:
        entered = db.fetch(body.venue, "people_entered")
    except Exception as e:
        return {f"Error fetching people entered for {body.venue}": str(e)}

    if type(entered) is str:
        return {f"Failed to fetch people entered for {body.venue}": "Fail"}

    try:
        exited = db.fetch(body.venue, "people_exited")
    except Exception as e:
        return {f"Error fetching people exited for {body.venue}": str(e)}
    
    if type(exited) is str:
        return {f"Failed to fetch people exited for {body.venue}": "Fail"}
    
    entered += body.entered
    exited += body.exited

    liveCount = max(0, entered - exited)
    
    try:
        passUpdates = db.update(body.venue, entered, "people_entered")
    except Exception as e:
        return {f"Error updating people entered for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Failed to update people entered for {body.venue}": "Fail"}
    
    try:
        passUpdates = db.update(body.venue, exited, "people_exited")
    except Exception as e:
        return {f"Error updating people exited for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Failed to update people entered for {body.venue}": "Fail"}
    
    ### NOTE: We need to add an error handling check when we migrate to phase 3 to check if the venue exists and if it doesn't
    ### We need to return the appropriate value
    
    try:
        passUpdates = db.update(body.venue, liveCount)
    except Exception as e:
        return {f"Error Updating Live Count for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Error Updating Live Count for {body.venue}": "Failed"}
    
    await broadcast(body.venue, liveCount, entered, exited)
    
    return {f"Success! You have updated {body.venue}'s Live Count to {liveCount}": "Pass"}
