import os
import asyncio

from fastapi import FastAPI, WebSocket
from redis.asyncio import Redis
from pydantic import BaseModel
from typing import Dict
from contextlib import asynccontextmanager
from db import DB
from models import UpdateBody
from dotenv import load_dotenv
    
### NOTE: We need to add an error handling check when we migrate to phase 3 to check if the venue exists and if it doesn't
### We need to return the appropriate value
load_dotenv()

db = DB()
redis = Redis(
    host=os.getenv("REDIS_ENDPOINT"),
    port=16840,
    password=os.getenv("REDIS_PASSWORD"),
    ssl=False,
    decode_responses=True
)

async def periodic_flush():
    """
    Periodic cache flushing system to update the DB with the Redis cache as a safety net incase we have a crash. This will be a background process.
    """

    while True:
        await asyncio.sleep(300) 
        await flush_all_venues_to_db()

async def flush_all_venues_to_db():
    """
    Flush all venues into the DB from the cache based on the periodic flushing function. Ensures we keep accurate counts.
    """
    
    keys = await redis.keys("venue:*")
    for key in keys:
        data = await redis.hgetall(key)
        venue_id = key.split(":")[1]
        db.update(venue_id, int(data["entered"]), "people_entered")
        db.update(venue_id, int(data["exited"]),  "people_exited")
        db.update(venue_id, int(data["liveCount"]))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Establish the connection with our database and setup a yield for cleanup functions after shutdown. For the time being there will
    be no cleanup functions but when we implement Redis we will want it to flush the cache to the supabase DB.

    ::param app the FastAPI backend app
    """

    db.establish_connection()
    asyncio.create_task(periodic_flush())
    yield

app = FastAPI(lifespan=lifespan)
active_connections: dict[str, list[WebSocket]] = {}

async def broadcast(venue: str):
    """
    Initial websocket broadcasting function to send the live count to all those listening on the websocket. Phase 2 will send socket specific information.

    ::param count the live count int
    ::param entered the people entered
    ::param exited the people exited
    """
    
    if venue in active_connections:
        for connection in active_connections[venue]:
            await connection.send_json(
                {
                    "count": await redis.hget(f"venue:{venue}", "liveCount"),
                    "entered": await redis.hget(f"venue:{venue}", "entered"),
                    "exited": await redis.hget(f"venue:{venue}", "exited")
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
        active_connections[venue] = []

    active_connections[venue].append(websocket)

    await initial_data(venue)

    try:
        while True:
            data = await websocket.receive_json()

            if data["action"] == "increment":
                await redis.hincrby(f"venue:{venue}", "entered", 1)
                
            elif data["action"] == "decrement":
                await redis.hincrby(f"venue:{venue}", "exited", 1)
            
            entered = await redis.hget(f"venue:{venue}", "entered")
            exited  = await redis.hget(f"venue:{venue}", "exited")
            live = max(0, int(entered) - int(exited))
            await redis.hset(f"venue:{venue}", "liveCount", live)

            await broadcast(venue)
    except Exception as e:
        print(f'WebSocket Exception: {e}')
        active_connections[venue].remove(websocket)

        if len(active_connections[venue]) == 0:
            data = await redis.hgetall(f"venue:{venue}")
            db.update(venue, int(data["entered"]), "people_entered")
            db.update(venue, int(data["exited"]),  "people_exited")
            db.update(venue, int(data["liveCount"]))
            await redis.delete(f"venue:{venue}")

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

    await redis.hset(f"venue:{venue}", mapping={
        "entered": entered,
        "exited": exited,
        "liveCount": liveCount
    })
    
    await broadcast(venue) 
