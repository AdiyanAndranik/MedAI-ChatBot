from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib import messages
from .models import ChatSession, UserProfile
import json
import uuid

def auth_redirect(request):
    """Redirect /auth to /auth/login/"""
    return redirect('/auth/login/')

@ensure_csrf_cookie
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('http://127.0.0.1:8080/chat')  # Redirect to Flask chat app
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'auth/login.html')

@ensure_csrf_cookie
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'auth/register.html')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create user profile
        UserProfile.objects.create(user=user)
        
        messages.success(request, 'Account created successfully')
        return redirect('/auth/login')
    
    return render(request, 'auth/register.html')

@login_required
def logout_view(request):
    logout(request)
    return redirect('/auth/login')

@csrf_exempt
def check_auth(request):
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name
            }
        })
    return JsonResponse({'authenticated': False})

@csrf_exempt
@login_required
def create_session(request):
    if request.method == 'POST':
        session_id = str(uuid.uuid4())
        session = ChatSession.objects.create(
            user=request.user,
            session_id=session_id
        )
        return JsonResponse({
            'session_id': session_id,
            'title': session.title
        })
    return JsonResponse({'error': 'Invalid request'})
