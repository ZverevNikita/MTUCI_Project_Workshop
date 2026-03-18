from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
import models
from manager import manager
import uuid

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

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB
        raise HTTPException(400, "Файл слишком большой")
    file_id = str(uuid.uuid4())
    models.files[file_id] = {
        'data': contents,
        'filename': file.filename,
        'size': len(contents)
    }
    return {"file_id": file_id, "filename": file.filename, "size": len(contents)}

@router.get("/file/{file_id}")
async def get_file(file_id: str):
    if file_id not in models.files:
        raise HTTPException(404, "Файл не найден")
    file_info = models.files[file_id]
    from fastapi.responses import Response
    return Response(
        content=file_info['data'],
        media_type='application/octet-stream',
        headers={
            "Content-Disposition": f"attachment; filename={file_info['filename']}"
        }
    )