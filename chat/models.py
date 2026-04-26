from django.db import models

class ChatRoom(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChatFile(models.Model):
    file = models.FileField(upload_to='chat_files/%Y/%m/%d/')
    original_name = models.CharField(max_length=255)
    room_name = models.CharField(max_length=255)  # комната, из которой загружен
    uploaded_by = models.CharField(max_length=150)  # имя пользователя (из сессии)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    size = models.IntegerField()  # размер в байтах

    def __str__(self):
        return self.original_name