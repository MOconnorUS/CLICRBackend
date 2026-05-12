from fastapi import FastAPI, WebSocket
from typing import Dict
from contextlib import asynccontextmanager
from db import establish_connection, update, update_live_count

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

@app.patch("/update/{venue}/{column}")
async def update_entry(venue:str, column: str):
    col_bool = False
    live_bool = False

    try:
        col_bool = update(venue, column)
    except Exception as e:
        return {f"Error Updating {column}": str(e)}

    if col_bool is False:
        return {f"Error Updating {column}": "Failed"}
    
    try:
        live_bool = update_live_count(venue)
    except Exception as e:
        return {f"Error Updating Live Count for {venue}": str(e)}
    
    if live_bool is False:
        return {f"Error Updating Live Count for {venue}": "Failed"}
    
    return {f"Success! You have updated {venue}'s {column}": "Pass"}

