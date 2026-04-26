from django.urls import re_path

from . import consumers
from .consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>.+)/$', ChatConsumer.as_asgi()),
]
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>.+)/$', consumers.ChatConsumer.as_asgi()),
]