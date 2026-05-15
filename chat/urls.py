from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('my-rooms/', views.my_rooms, name='my_rooms'),
    path('create/', views.create_room, name='create_room'),
    path('<str:room_name>/', views.room, name='room'),
    path('<str:room_name>/upload/', views.upload_file, name='upload_file'),
    path('<str:room_name>/leave/', views.leave_room, name='leave_room'),
]