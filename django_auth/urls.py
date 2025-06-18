from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def root_redirect(request):
    """Redirect root URL to auth login"""
    return redirect('/auth/login/')

def chat_redirect(request):
    """Redirect chat URL to Flask server"""
    return redirect('http://127.0.0.1:8080/chat')

urlpatterns = [
    path('', root_redirect, name='root_redirect'),
    path('chat/', chat_redirect, name='chat_redirect'),  # Added chat redirect
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
]
