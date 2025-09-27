# milk_app/admin.py
from django.contrib import admin
from .models import User, DailyMilkRequest

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'full_name', 'role', 'timezone', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['phone_number', 'full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(DailyMilkRequest)
class DailyMilkRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'target_date', 'liters', 'status', 'created_at']
    list_filter = ['status', 'target_date', 'created_at']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']