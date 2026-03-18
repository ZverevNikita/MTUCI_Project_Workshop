import asyncio
from collections import defaultdict

MAX_MESSAGES_PER_ROOM = 100

rooms = defaultdict(lambda: {'messages': [], 'users': set(), 'password': None})
rooms['общий'] = {'messages': [], 'users': set(), 'password': None}

private_channels = defaultdict(list)
user_current_room = {}
data_lock = asyncio.Lock()

files = {}