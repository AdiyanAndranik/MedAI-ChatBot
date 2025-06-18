from django.contrib import admin
from .models import UserProfile, ChatSession, ChatMessage

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified')
    list_filter = ('is_verified',)
    search_fields = ('user__username', 'user__email')

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'title')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'language')
    list_filter = ('timestamp', 'language')
    search_fields = ('message', 'response')
