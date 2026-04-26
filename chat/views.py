from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from .models import ChatRoom, ChatFile
import os

def index(request):
    if request.method == 'POST' and 'username' in request.POST:
        username = request.POST.get('username')
        if username:
            request.session['username'] = username
            return redirect('index')

    username = request.session.get('username', '')

    rooms = ChatRoom.objects.all().order_by('-created_at')

    return render(request, 'chat/index.html', {
        'rooms': rooms,
        'username': username
    })

def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        if room_name:
            # get_or_create создаёт комнату, если её ещё нет
            ChatRoom.objects.get_or_create(name=room_name)
            return redirect('room', room_name=room_name)
    return redirect('index')

def room(request, room_name):
    username = request.session.get('username')
    if not username:
        return redirect('index')
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'username': username
    })

@require_http_methods(["POST"])
@csrf_exempt
def upload_file(request, room_name):
    username = request.session.get('username')
    if not username:
        return JsonResponse({'error': 'Не указано имя пользователя'}, status=403)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Файл не передан'}, status=400)

    uploaded_file = request.FILES['file']

    file_path = default_storage.save(
        os.path.join('chat_files', room_name, uploaded_file.name),
        uploaded_file
    )
    file_url = request.build_absolute_uri(default_storage.url(file_path))

    ChatFile.objects.create(
        file=file_path,
        original_name=uploaded_file.name,
        room_name=room_name,
        uploaded_by=username,
        size=uploaded_file.size
    )

    return JsonResponse({
        'url': file_url,
        'name': uploaded_file.name,
        'size': uploaded_file.size,
        'uploaded_by': username,
    })