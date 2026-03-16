from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import models
from manager import manager

router = APIRouter()

@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data, room, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)

@router.get("/room_users")
async def get_room_users(room: str):
    async with models.data_lock:
        if room in models.rooms:
            return list(models.rooms[room]['users'])
        return []