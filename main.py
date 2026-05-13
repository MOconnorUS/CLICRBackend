from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict
from contextlib import asynccontextmanager
from db import establish_connection, update, update_live_count, fetch
from models import UpdateBody

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Establish the connection with our database and setup a yield for cleanup functions after shutdown. For the time being there will
    be no cleanup functions but when we implement Redis we will want it to flush the cache to the supabase DB.

    ::param app the FastAPI backend app
    """
    establish_connection()
    yield

app = FastAPI(lifespan=lifespan)

active_connections: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Initial websocket endpoint. This will serve as phase 1 of 2 with websockets to establish a single live connection. Phase 2 will have per venue sockets

    ::param websocket the websocket connection
    """
    
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        print(f'WebSocket Exception: {e}')
        active_connections.remove(websocket)

async def broadcast(count: int, entered: int, exited: int):
    """
    Initial websocket broadcasting function to send the live count to all those listening on the websocket. Phase 2 will send socket specific information.

    ::param count the live count int
    ::param entered the people entered
    ::param exited the people exited
    """
    
    for connection in active_connections:
        await connection.send_json({"count": count, "entered": entered, "exited": exited})

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
        entered = fetch(body.venue, "people_entered")
    except Exception as e:
        return {f"Error fetching people entered for {body.venue}": str(e)}

    if type(entered) is str:
        return {f"Failed to fetch people entered for {body.venue}": "Fail"}

    try:
        exited = fetch(body.venue, "people_exited")
    except Exception as e:
        return {f"Error fetching people exited for {body.venue}": str(e)}
    
    if type(exited) is str:
        return {f"Failed to fetch people exited for {body.venue}": "Fail"}
    
    entered += body.entered
    exited += body.exited

    liveCount = max(0, entered - exited)
    
    try:
        passUpdates = update(body.venue, "people_entered", entered)
    except Exception as e:
        return {f"Error updating people entered for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Failed to update people entered for {body.venue}": "Fail"}
    
    try:
        passUpdates = update(body.venue, "people_exited", exited)
    except Exception as e:
        return {f"Error updating people exited for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Failed to update people entered for {body.venue}": "Fail"}
    
    ### NOTE: We need to add an error handling check when we migrate to phase 3 to check if the venue exists and if it doesn't
    ### We need to return the appropriate value
    
    try:
        passUpdates = update_live_count(body.venue, liveCount)
    except Exception as e:
        return {f"Error Updating Live Count for {body.venue}": str(e)}
    
    if passUpdates is False:
        return {f"Error Updating Live Count for {body.venue}": "Failed"}
    
    await broadcast(liveCount, entered, exited)
    
    return {f"Success! You have updated {body.venue}'s Live Count to {liveCount}": "Pass"}
