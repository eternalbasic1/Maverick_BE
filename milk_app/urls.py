# milk_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('auth/signup/', views.signup, name='signup'), 
    path('auth/login/', views.login, name='login'),
    path('auth/refresh/', views.refresh_token, name='refresh_token'),
    
    # User Profile
    path('user/me/', views.user_profile, name='user_profile'),
    
    # Subscription Management (Updated with Rate Versioning)
    path('subscription/', views.user_subscription, name='user_subscription'),
    path('subscription/update-rate/', views.update_subscription_rate, name='update_subscription_rate'),
    path('subscription/billing-history/', views.subscription_billing_history, name='subscription_billing_history'),
    
    # Skip Requests (New - Exception-based approach)
    path('skip/', views.skip_delivery, name='skip_delivery'),
    path('skip/list/', views.user_skip_requests, name='user_skip_requests'),
    path('skip/<uuid:skip_id>/', views.cancel_skip_request, name='cancel_skip_request'),
    
    # Legacy Milk Requests (Keep for backward compatibility or remove)
    path('requests/', views.create_milk_request, name='create_milk_request'),
    path('requests/<uuid:request_id>/', views.update_milk_request, name='update_milk_request'),
    path('requests/<uuid:request_id>/delete/', views.delete_milk_request, name='delete_milk_request'),
    path('requests/by-date/', views.get_user_request, name='get_user_request'),
    
    # Admin - Updated with Rate Versioning System
    path('admin/schedule/', views.admin_delivery_schedule, name='admin_delivery_schedule'),
    path('admin/billing-report/', views.admin_billing_report, name='admin_billing_report'),
    path('admin/skip-requests/', views.admin_skip_requests, name='admin_skip_requests'),
    path('admin/update-deliveries/', views.admin_update_delivery_status, name='admin_update_delivery_status'),
    
    # Admin - Legacy (Keep or remove based on needs)
    path('admin/requests/', views.admin_get_requests, name='admin_get_requests'),
    path('admin/aggregate/', views.admin_get_aggregate, name='admin_get_aggregate'),
    path('admin/requests/<uuid:request_id>/override/', views.admin_override_request, name='admin_override_request'),
]
