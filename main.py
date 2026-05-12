from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Dict
from contextlib import asynccontextmanager
from db import establish_connection, update, update_live_count
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

@app.get("/health_check")
async def ping():
    return {"result": "healthy"}

@app.patch("/update")
async def update_entry(body: UpdateBody):
    """
    Asynchronous backend API route to update the live count in the Supabase Database.

    ::param body the UpdateBody model to handle the body information
    """
    
    live_bool = False

    ### NOTE: We need to add an error handling check when we migrate to phase 3 to check if the venue exists and if it doesn't
    ### We need to return the appropriate value
    
    try:
        live_bool = update_live_count(body.venue, body.value)
    except Exception as e:
        return {f"Error Updating Live Count for {body.venue}": str(e)}
    
    if live_bool is False:
        return {f"Error Updating Live Count for {body.venue}": "Failed"}
    
    return {f"Success! You have updated {body.venue}'s Live Count to {body.value}": "Pass"}

