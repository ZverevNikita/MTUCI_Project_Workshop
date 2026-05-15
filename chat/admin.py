from django.contrib import admin
from .models import ChatRoom, ChatFile, Message

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'participants_count']
    search_fields = ['name']
    filter_horizontal = ['participants']

    def participants_count(self, obj):
        return obj.participants.count()

    participants_count.short_description = 'Участников'

@admin.register(ChatFile)
class ChatFileAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'room_name', 'uploaded_by', 'uploaded_at', 'size']
    list_filter = ['room_name', 'uploaded_at']
    search_fields = ['original_name', 'uploaded_by']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['username', 'room', 'message_type', 'timestamp']
    list_filter = ['room', 'message_type', 'timestamp']
    search_fields = ['username', 'content']