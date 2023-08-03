import asyncio
import json
import jwt
import logging
import os
import redis

from fastapi import Depends, FastAPI, WebSocket
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect

from auth import (
    generate_token,
    validate_token
)
from common import (
    WEBSOCKET_SEND_INTERVAL,
    logger
)

app = FastAPI()
security = HTTPBearer()
# Mount the "static" directory to serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Simulated microwave state stored in Redis
# TODO: Create a wrapper around redis client for easy access and DRY
redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)

CACHE_KEY = "microwave_state"

# Initial state of the microwave
INITIAL_MICROWAVE_STATE = {
    "power": "0",
    "counter": "0",
    "on": "False"
}


def _get_microwave_state():
    """
    Get microwave state from redis or return initial state if it does not exist in redis
    """
    state = redis_client.hgetall(CACHE_KEY)
    if not state:
        redis_client.hmset(CACHE_KEY, INITIAL_MICROWAVE_STATE)
        state = INITIAL_MICROWAVE_STATE
    return state

# A set to keep track of active WebSocket connections
active_connections = set()

async def send_data_to_clients():
    """
    Send data to all active websocket connections.
    """
    data = _get_microwave_state()
    for connection in active_connections:
        logger.info(f"Sending data to client: {connection.client[0]}:{connection.client[1]}")
        await connection.send_text(json.dumps(data))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Websocket endpoint client sessions connect to.
    """
    # Open the WebSocket connection
    await websocket.accept()

    # Add the WebSocket connection to the set of active connections
    active_connections.add(websocket)

    try:
        while True:
            # Continuously read data from Redis
            data = _get_microwave_state()
            if data:
                # Send the data to the client
                await websocket.send_text(json.dumps(data))

            # Sleep for a short duration
            await asyncio.sleep(WEBSOCKET_SEND_INTERVAL)

    except WebSocketDisconnect:
        # Remove the WebSocket connection from the set when it's disconnected
        active_connections.remove(websocket)

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up the connection set on application shutdown
    """
    for connection in active_connections:
        await connection.close()

@app.get("/microwave")
def get_microwave_state():
    """
    Returns state of microwave.
    """
    return _get_microwave_state()

@app.post("/microwave/power/")
async def adjust_power(adjustment: int):
    """
    Adjust power of microwave.
    """
    state = _get_microwave_state()

    power = int(state.get("power", 0)) + adjustment
    power = max(0, power)
    state["power"] = str(power)

    # Turn the microwave on if power is greater than 0
    state["on"] = str(power > 0)
    logger.info(f"Power: {state['power']}, Counter: {state['counter']}")

    redis_client.hmset(CACHE_KEY, state)
    await send_data_to_clients()
    # No need to send data, websocket sends data in real time.
    return {}

@app.post("/microwave/counter")
async def adjust_counter(adjustment: int):
    """
    Adjust counter of microwave.
    """
    state = _get_microwave_state()

    counter = int(state.get("counter", 0)) + adjustment
    counter = max(0, counter)
    state["counter"] = str(counter)

    # Turn the microwave on if counter is greater than 0
    state["on"] = str(counter > 0)

    logger.info(f"Power: {state['power']}, Counter: {state['counter']}")

    redis_client.hmset(CACHE_KEY, state)
    await send_data_to_clients()
    # No need to send data, websocket sends data in real time.
    return {}

@app.post("/microwave/cancel")
def cancel_microwave(token: HTTPAuthorizationCredentials = Depends(security)):
    """
    Cancel microwave operation (requires JWT token)
    """
    # Raises exception if token is not valid
    validate_token(token)

    # Reset microwave state to initial state
    redis_client.hmset(CACHE_KEY, INITIAL_MICROWAVE_STATE)
    # No need to send data, websocket sends data in real time.
    return {}

@app.get("/get_token/")
async def get_token():
    """
    Returns JWT token
    """
    # Generate a new JWT token
    token = generate_token()
    return {"token": token}
