from django.contrib import admin
from .models import (
    User,
    DailyMilkRequest,
    UserSubscription,
    SubscriptionRate,
    DailySkipRequest,
    DailyMilkDelivery,
    MilkPricing,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'full_name', 'role', 'timezone', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['phone_number', 'full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DailyMilkRequest)
class DailyMilkRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'target_date', 'liters', 'milk_type', 'status', 'created_at']
    list_filter = ['status', 'milk_type', 'target_date', 'created_at']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_active', 'subscription_start_date', 'subscription_end_date', 'milk_type', 'created_at']
    list_filter = ['is_active', 'milk_type', 'subscription_start_date', 'subscription_end_date']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(SubscriptionRate)
class SubscriptionRateAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'daily_liters', 'effective_from', 'effective_to', 'is_active', 'created_at']
    list_filter = ['is_active', 'effective_from']
    search_fields = ['subscription__user__phone_number', 'subscription__user__full_name']
    readonly_fields = ['id', 'created_at']


@admin.register(DailySkipRequest)
class DailySkipRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'skip_date', 'reason', 'notes', 'created_at']
    list_filter = ['reason', 'skip_date', 'created_at']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['id', 'created_at']


@admin.register(DailyMilkDelivery)
class DailyMilkDeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'delivery_date',
        'scheduled_liters',
        'actual_liters',
        'rate_applied',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'delivery_date', 'created_at']
    search_fields = ['user__phone_number', 'user__full_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(MilkPricing)
class MilkPricingAdmin(admin.ModelAdmin):
    list_display = ['milk_type', 'liters', 'price', 'effective_from', 'effective_to', 'created_at']
    list_filter = ['milk_type', 'effective_from', 'effective_to', 'created_at']
    search_fields = ['milk_type', 'price']
    readonly_fields = ['id', 'created_at']
    ordering = ['milk_type', '-effective_from']
