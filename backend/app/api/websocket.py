import asyncio
import json
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings

router = APIRouter(prefix="", tags=["WebSocket Live Stream"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Subscribes to Redis 'alerts_channel' and streams live classified hotspot alerts to connected clients.
    """
    await manager.connect(websocket)
    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("alerts_channel")

        # Send initial connection acknowledgment
        await websocket.send_json({"type": "connection_established", "status": "LIVE"})

        while True:
            # Poll redis pubsub message
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                await websocket.send_text(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket Error] Client disconnected or redis error: {e}")
        manager.disconnect(websocket)
    finally:
        if pubsub:
            await pubsub.unsubscribe("alerts_channel")
        if redis_client:
            await redis_client.close()
