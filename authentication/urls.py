from django.urls import path
from . import views

urlpatterns = [
    path('', views.auth_redirect, name='auth_redirect'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('check/', views.check_auth, name='check_auth'),
    path('session/create/', views.create_session, name='create_session'),
]
