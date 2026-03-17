import asyncio
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
import models

async def main():
    nickname = await input(
        "Введите ваш ник",
        required=True,
        validate=lambda n: "Ник уже используется!"
        if any(n in room['users'] for room in models.rooms.values())
        else None
    )

    def validate_room_name(r):
        if r in models.rooms:
            return "Такая комната уже существует"
        if r in '🔄🔄️':
            return "Запрещённое название для комнаты"
        return None

    while True:
        room_choices = ['🔄️'] + list(models.rooms.keys()) + ['Создать новую комнату']
        action = await actions("Выберите комнату или создайте новую", buttons=room_choices)
        if action == '🔄️':
            toast("Список комнат обновлён", color='blue')
        elif action == 'Создать новую комнату':
            new_room = await input(
                "Введите название новой комнаты",
                required=True,
                validate=validate_room_name
            )
            password = await input(
                "Введите пароль для комнаты (оставьте пустым, если пароль не нужен)",
                type=PASSWORD
            )
            async with models.data_lock:
                models.rooms[new_room] = {
                    'messages': [],
                    'users': set(),
                    'password': password if password else None
                }
            room_name = new_room
            break
        else:
            room_name = action
            async with models.data_lock:
                if room_name not in models.rooms:
                    toast("Комната не найдена", color='error')
                    continue
                need_password = models.rooms[room_name]['password'] is not None

            if need_password:
                entered = await input("Введите пароль для комнаты", type=PASSWORD)
                async with models.data_lock:
                    if room_name not in models.rooms:
                        toast("Комната больше не существует", color='error')
                        continue
                    if models.rooms[room_name]['password'] != entered:
                        toast("Неверный пароль", color='error')
                        continue 
            break

    async with models.data_lock:
        models.rooms[room_name]['users'].add(nickname)
        models.user_current_room[nickname] = room_name
        models.rooms[room_name]['messages'].append(('📢', f'`{nickname}` присоединился к чату'))
        if len(models.rooms[room_name]['messages']) > models.MAX_MESSAGES_PER_ROOM:
            models.rooms[room_name]['messages'] = models.rooms[room_name]['messages'][-models.MAX_MESSAGES_PER_ROOM:]

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
            async with models.data_lock:
                current_room = models.user_current_room.get(nickname)
                if current_room and current_room in models.rooms:
                    users = models.rooms[current_room]['users']
                    with use_scope('user-list', clear=True):
                        put_column([put_text(u) for u in sorted(users)])
                else:
                    break

    async def refresh_messages():
        last_idx = 0
        while True:
            await asyncio.sleep(1)
            async with models.data_lock:
                current_room = models.user_current_room.get(nickname)
                if not current_room or current_room not in models.rooms:
                    break
                room_msgs = models.rooms[current_room]['messages']
                for i in range(last_idx, len(room_msgs)):
                    sender, text = room_msgs[i]
                    if sender != nickname:
                        with use_scope('msg-box'):
                            put_markdown(f"`{sender}`: {text}")
                last_idx = len(room_msgs)

    user_list_task = run_async(update_user_list())
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
                async with models.data_lock:
                    if target_room not in models.rooms:
                        toast("Комната не найдена", color='error')
                        continue
                    need_password = models.rooms[target_room]['password'] is not None

                if need_password:
                    entered = await input("Введите пароль для комнаты", type=PASSWORD)
                    async with models.data_lock:
                        if target_room not in models.rooms:
                            toast("Комната больше не существует", color='error')
                            continue
                        if models.rooms[target_room]['password'] != entered:
                            toast("Неверный пароль", color='error')
                            continue

                async with models.data_lock:
                    old_room = models.user_current_room[nickname]
                    models.rooms[old_room]['users'].discard(nickname)
                    models.rooms[old_room]['messages'].append(('📢', f'`{nickname}` покинул чат'))
                    models.rooms[target_room]['users'].add(nickname)
                    models.user_current_room[nickname] = target_room
                    models.rooms[target_room]['messages'].append(('📢', f'`{nickname}` присоединился к чату'))
                    with use_scope('msg-box', clear=True):
                        for sender, text in models.rooms[target_room]['messages'][-50:]:
                            put_markdown(f"`{sender}`: {text}")
                toast(f"Перешли в комнату {target_room}")
                continue
            else:
                toast("Неизвестная команда", color='error')
                continue

        async with models.data_lock:
            current_room = models.user_current_room.get(nickname)
            if current_room:
                models.rooms[current_room]['messages'].append((nickname, msg_text))
                if len(models.rooms[current_room]['messages']) > models.MAX_MESSAGES_PER_ROOM:
                    models.rooms[current_room]['messages'] = models.rooms[current_room]['messages'][-models.MAX_MESSAGES_PER_ROOM:]
                with use_scope('msg-box'):
                    put_markdown(f"`{nickname}`: {msg_text}")

    refresh_task.close()
    user_list_task.close()
    async with models.data_lock:
        current_room = models.user_current_room.get(nickname)
        if current_room:
            models.rooms[current_room]['users'].discard(nickname)
            models.rooms[current_room]['messages'].append(('📢', f'`{nickname}` покинул чат'))
        if nickname in models.user_current_room:
            del models.user_current_room[nickname]

    toast("Вы вышли из чата")
    put_buttons(['Перезайти'], onclick=lambda btn: run_js('window.location.reload()'))