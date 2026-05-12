import json
import re
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Безопасное имя группы
        safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', self.room_name)[:100]
        self.room_group_name = f'chat_{safe_name}'

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Аноним'])[0]

        self.room = await self.get_or_create_room(self.room_name)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send_history()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        if msg_type == 'text':
            message_text = data.get('message', '').strip()
            if not message_text:
                return
            saved_msg = await self.save_text_message(self.username, self.room, message_text)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'text',
                    'username': self.username,
                    'content': message_text,
                    'timestamp': saved_msg.timestamp.isoformat(),
                }
            )
        elif msg_type == 'file':
            file_url = data.get('file_url')
            file_name = data.get('file_name')
            file_size = data.get('file_size')
            if not file_url:
                return
            saved_msg = await self.save_file_message(self.username, self.room, file_url, file_name, file_size)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'file',
                    'username': self.username,
                    'file_url': file_url,
                    'file_name': file_name,
                    'file_size': file_size,
                    'timestamp': saved_msg.timestamp.isoformat(),
                }
            )

    async def chat_message(self, event):
        payload = {
            'type': event['message_type'],
            'username': event['username'],
            'timestamp': event.get('timestamp'),
        }
        if event['message_type'] == 'text':
            payload['content'] = event['content']
        elif event['message_type'] == 'file':
            payload['file_url'] = event['file_url']
            payload['file_name'] = event['file_name']
            payload['file_size'] = event['file_size']
        await self.send(text_data=json.dumps(payload))

    async def send_history(self):
        messages = await self.get_room_history(self.room)
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages
        }))

    @database_sync_to_async
    def get_or_create_room(self, room_name):
        room, _ = ChatRoom.objects.get_or_create(name=room_name)
        return room

    @database_sync_to_async
    def save_text_message(self, username, room, content):
        return Message.objects.create(
            room=room,
            username=username,
            message_type='text',
            content=content
        )

    @database_sync_to_async
    def save_file_message(self, username, room, file_url, file_name, file_size):
        return Message.objects.create(
            room=room,
            username=username,
            message_type='file',
            file_url=file_url,
            file_name=file_name,
            file_size=file_size
        )

    @database_sync_to_async
    def get_room_history(self, room, limit=50):
        qs = Message.objects.filter(room=room)[:limit]
        return [
            {
                'type': msg.message_type,
                'username': msg.username,
                'content': msg.content,
                'file_url': msg.file_url,
                'file_name': msg.file_name,
                'file_size': msg.file_size,
                'timestamp': msg.timestamp.isoformat(),
            }
            for msg in qs
        ]