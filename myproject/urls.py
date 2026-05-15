from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from chat.views import RegistrationUser, LoginUser, logout_user, pageNotFound

urlpatterns = [
    path('', RedirectView.as_view(url='/chat/', permanent=False)),
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),
    path('register/', RegistrationUser.as_view(), name='register'),
    path('login/', LoginUser.as_view(), name='login'),
    path('logout/', logout_user, name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = pageNotFound