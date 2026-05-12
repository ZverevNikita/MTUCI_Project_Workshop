import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.utils.text import get_valid_filename
from .models import ChatRoom, ChatFile

def index(request):
    if request.method == 'POST' and 'username' in request.POST:
        username = request.POST.get('username')
        if username:
            request.session['username'] = username
            return redirect('index')
    username = request.session.get('username', '')
    rooms = ChatRoom.objects.all().order_by('-created_at')
    return render(request, 'chat/index.html', {'rooms': rooms, 'username': username})

def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        if room_name:
            safe_name = get_valid_filename(room_name)   # заменяет пробелы на _, удаляет плохие символы
            if safe_name:
                ChatRoom.objects.get_or_create(name=safe_name)
                return redirect('room', room_name=safe_name)
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
def upload_file(request, room_name):
    username = request.session.get('username')
    if not username:
        return JsonResponse({'error': 'Не указано имя пользователя'}, status=403)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'Файл не передан'}, status=400)

    uploaded_file = request.FILES['file']

    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'Файл не должен превышать 10 МБ'}, status=400)

    safe_filename = get_valid_filename(uploaded_file.name)
    safe_room = get_valid_filename(room_name)
    if not safe_filename or not safe_room:
        return JsonResponse({'error': 'Некорректное имя файла или комнаты'}, status=400)

    relative_path = os.path.join('chat_files', safe_room, safe_filename)
    full_path = default_storage.save(relative_path, uploaded_file)
    file_url = request.build_absolute_uri(default_storage.url(full_path))

    ChatFile.objects.create(
        file=full_path,
        original_name=uploaded_file.name,
        room_name=safe_room,
        uploaded_by=username,
        size=uploaded_file.size
    )

    return JsonResponse({
        'url': file_url,
        'name': safe_filename,
        'size': uploaded_file.size,
    })