import asyncio
from collections import defaultdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
from pywebio.platform.fastapi import webio_routes
import uvicorn

rooms = {}
private_channels = defaultdict(list)
user_current_room = {}
data_lock = asyncio.Lock()

MAX_MESSAGES_PER_ROOM = 100

rooms['общий'] = {'messages': [], 'users': set()}

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.active_connections[room].append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        if room in self.active_connections:
            self.active_connections[room].remove(websocket)
            if not self.active_connections[room]:
                del self.active_connections[room]

    async def send_personal(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict, room: str, sender: WebSocket = None):
        for connection in self.active_connections.get(room, []):
            if connection != sender:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

app = FastAPI()

@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    await manager.connect(websocket, room)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data, room, sender=websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)

@app.get("/room_users")
async def get_room_users(room: str):
    async with data_lock:
        if room in rooms:
            return list(rooms[room]['users'])
        return []

async def main():
    global rooms, user_current_room

    nickname = await input(
        "Введите ваш ник",
        required=True,
        validate=lambda n: "Ник уже используется!"
        if any(n in room['users'] for room in rooms.values())
        else None
    )

    room_choices = list(rooms.keys()) + ['Создать новую комнату']
    action = await actions("Выберите комнату или создайте новую", buttons=room_choices)

    if action == 'Создать новую комнату':
        new_room = await input(
            "Введите название новой комнаты",
            required=True,
            validate=lambda r: "Такая комната уже существует" if r in rooms else None
        )
        async with data_lock:
            rooms[new_room] = {'messages': [], 'users': set()}
        room_name = new_room
    else:
        room_name = action

    async with data_lock:
        rooms[room_name]['users'].add(nickname)
        user_current_room[nickname] = room_name
        rooms[room_name]['messages'].append(('📢', f'`{nickname}` присоединился к чату'))
        if len(rooms[room_name]['messages']) > MAX_MESSAGES_PER_ROOM:
            rooms[room_name]['messages'] = rooms[room_name]['messages'][-MAX_MESSAGES_PER_ROOM:]

    put_markdown(f"## Добро пожаловать в комнату **{room_name}**, {nickname}!")

    user_list_panel = put_column([
        put_markdown("### Участники"),
        put_scope('user-list')
    ])

    msg_box = put_scope('msg-box')
    input_area = put_column([put_scope('input-area')])
    main_area = put_column([
        put_scrollable(msg_box, height=300, keep_bottom=True),
        input_area
    ])

    put_row([user_list_panel, main_area])

    run_js(f"""
    let localStream = null;
    let peerConnections = {{}};
    let ws = null;

    function closeAllConnections() {{
        if (ws) {{
            ws.close();
            ws = null;
        }}
        for (let id in peerConnections) {{
            peerConnections[id].close();
        }}
        peerConnections = {{}};
    }}

    function connectToRoom(room) {{
        closeAllConnections(); 

        ws = new WebSocket(`ws://${{window.location.host}}/ws/${{room}}`);

        ws.onopen = () => {{
            console.log("WebSocket connected");
            getRoomUsers(room);
        }};

        ws.onmessage = async (event) => {{
            const data = JSON.parse(event.data);
            await handleSignal(data);
        }};

        ws.onclose = () => {{
            console.log("WebSocket closed");
        }};
    }}

    async function handleSignal(data) {{
        const {{ type, sdp, candidate, from }} = data;

        if (type === 'offer') {{
            if (!peerConnections[from]) {{
                peerConnections[from] = new RTCPeerConnection();
                peerConnections[from].ontrack = (event) => {{
                    const audio = new Audio();
                    audio.srcObject = event.streams[0];
                    audio.autoplay = true;
                }};
                localStream.getTracks().forEach(track => peerConnections[from].addTrack(track, localStream));
            }}
            await peerConnections[from].setRemoteDescription({{ type: 'offer', sdp: sdp }});
            const answer = await peerConnections[from].createAnswer();
            await peerConnections[from].setLocalDescription(answer);
            ws.send(JSON.stringify({{ type: 'answer', sdp: answer.sdp, to: from }}));
        }} else if (type === 'answer') {{
            if (peerConnections[from]) {{
                await peerConnections[from].setRemoteDescription({{ type: 'answer', sdp: sdp }});
            }}
        }} else if (type === 'candidate') {{
            if (peerConnections[from]) {{
                await peerConnections[from].addIceCandidate(new RTCIceCandidate(candidate));
            }}
        }}
    }}

    function createPeerConnection(targetId) {{
        if (peerConnections[targetId]) return;
        const pc = new RTCPeerConnection();
        peerConnections[targetId] = pc;

        pc.onicecandidate = (event) => {{
            if (event.candidate) {{
                ws.send(JSON.stringify({{ type: 'candidate', candidate: event.candidate, to: targetId }}));
            }}
        }};

        pc.ontrack = (event) => {{
            const audio = new Audio();
            audio.srcObject = event.streams[0];
            audio.autoplay = true;
        }};

        localStream.getTracks().forEach(track => pc.addTrack(track, localStream));

        pc.createOffer()
            .then(offer => pc.setLocalDescription(offer))
            .then(() => {{
                ws.send(JSON.stringify({{ type: 'offer', sdp: pc.localDescription.sdp, to: targetId }}));
            }});
    }}

    function getRoomUsers(room) {{
        fetch('/room_users?room=' + encodeURIComponent(room))
            .then(res => res.json())
            .then(users => {{
                users.forEach(user => {{
                    if (user !== "{nickname}") {{
                        createPeerConnection(user);
                    }}
                }});
            }});
    }}
    """)

    async def update_user_list():
        while True:
            await asyncio.sleep(2)
            async with data_lock:
                current_room = user_current_room.get(nickname)
                if current_room and current_room in rooms:
                    users = rooms[current_room]['users']
                    with use_scope('user-list', clear=True):
                        put_column([put_text(u) for u in sorted(users)])
                else:
                    break

    user_list_task = run_async(update_user_list())

    async def refresh_messages():
        last_idx = 0
        while True:
            await asyncio.sleep(1)
            async with data_lock:
                current_room = user_current_room.get(nickname)
                if not current_room or current_room not in rooms:
                    break
                room_msgs = rooms[current_room]['messages']
                for msg in room_msgs[last_idx:]:
                    sender, text = msg
                    if sender != nickname:
                        with use_scope('msg-box'):
                            put_markdown(f"`{sender}`: {text}")
                last_idx = len(room_msgs)

    refresh_task = run_async(refresh_messages())

    while True:
        data = await input_group("Новое сообщение", [
            input(placeholder="Сообщение...", name="msg"),
            actions(name="cmd", buttons=[
                "Отправить",
                {'label': "Покинуть чат", 'type': 'cancel'}
            ])
        ], validate=lambda m: ('msg', "Введите текст") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if data is None:
            break

        msg_text = data['msg'].strip()

        if msg_text.startswith('/'):
            parts = msg_text.split(maxsplit=1)
            cmd = parts[0].lower()
            if cmd == '/join' and len(parts) > 1:
                target_room = parts[1].strip()
                async with data_lock:
                    if target_room in rooms:
                        old_room = user_current_room[nickname]
                        rooms[old_room]['users'].discard(nickname)
                        rooms[old_room]['messages'].append(('📢', f'`{nickname}` покинул чат'))
                        rooms[target_room]['users'].add(nickname)
                        user_current_room[nickname] = target_room
                        rooms[target_room]['messages'].append(('📢', f'`{nickname}` присоединился к чату'))
                        with use_scope('msg-box', clear=True):
                            for sender, text in rooms[target_room]['messages'][-50:]:
                                put_markdown(f"`{sender}`: {text}")
                        toast(f"Перешли в комнату {target_room}")
                    else:
                        toast("Комната не найдена", color='error')
                continue
            else:
                toast("Неизвестная команда", color='error')
                continue

        async with data_lock:
            current_room = user_current_room.get(nickname)
            if current_room:
                rooms[current_room]['messages'].append((nickname, msg_text))
                if len(rooms[current_room]['messages']) > MAX_MESSAGES_PER_ROOM:
                    rooms[current_room]['messages'] = rooms[current_room]['messages'][-MAX_MESSAGES_PER_ROOM:]
                with use_scope('msg-box'):
                    put_markdown(f"`{nickname}`: {msg_text}")

    refresh_task.close()
    user_list_task.close()
    async with data_lock:
        current_room = user_current_room.get(nickname)
        if current_room:
            rooms[current_room]['users'].discard(nickname)
            rooms[current_room]['messages'].append(('📢', f'`{nickname}` покинул чат'))
        if nickname in user_current_room:
            del user_current_room[nickname]

    toast("Вы вышли из чата")
    put_buttons(['Перезайти'], onclick=lambda btn: run_js('window.location.reload()'))

app.routes.extend(webio_routes(main))

if __name__ == "__main__":
    uvicorn.run(app, host="192.168.1.77", port=8080)