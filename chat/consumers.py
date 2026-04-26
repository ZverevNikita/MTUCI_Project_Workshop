import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        query_string = self.scope['query_string'].decode()
        query_params = parse_qs(query_string)
        self.username = query_params.get('username', ['Аноним'])[0]

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'text')

        if msg_type == 'text':
            message = data['message']
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'text',
                    'message': message,
                    'username': self.username
                }
            )
        elif msg_type == 'file':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'file',
                    'file_url': data['file_url'],
                    'file_name': data['file_name'],
                    'file_size': data['file_size'],
                    'username': self.username
                }
            )

    async def chat_message(self, event):
        if event['message_type'] == 'text':
            await self.send(text_data=json.dumps({
                'type': 'text',
                'username': event['username'],
                'message': event['message']
            }))
        elif event['message_type'] == 'file':
            await self.send(text_data=json.dumps({
                'type': 'file',
                'username': event['username'],
                'file_url': event['file_url'],
                'file_name': event['file_name'],
                'file_size': event['file_size']
            }))