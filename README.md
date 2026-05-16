# CLICR Backend

Simplified prototype implementation of CLICR backend

## Features
- DataBase object for interaction with Supabase DB (Postgres SQL)
- Venue-specific WebSocket connections using venue name to establish unique WebSockets (Would use venue IDs in production)
- Real-time processing of incrementation and decrementation from the frontend via the WebSocket
- Real-time broadcasting of the updated count, people entered, and people exited
- Venue-specific Redis caches spun up per venue-specific WebSocket
- Periodic (5 minute) Redis cache writes to Supabase DB
- Redis cache flush to Supabase upon WebSocket closures

## Tech Stack
- Python
- FastAPI
- Redis
- Supabase

## Notes
This project is configured for local use only  
Environment variables are intentionally omitted  

## Project Architecture, Scaling, & Production Ready Notes
![Project Architecture](assets/Images/CLICR%20Architecture,%20Product,%20and%20Scaling.png)
