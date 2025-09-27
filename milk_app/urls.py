# milk_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('auth/signup/', views.signup, name='signup'), #working✅
    path('auth/login/', views.login, name='login'), #working✅
    path('auth/refresh/', views.refresh_token, name='refresh_token'),
    
    # User
    path('user/me/', views.user_profile, name='user_profile'), #working✅
    
    # Milk Requests
    path('requests/', views.create_milk_request, name='create_milk_request'),
    path('requests/<uuid:request_id>/', views.update_milk_request, name='update_milk_request'), #comebacklater I think we have time error & Make sure you pass proper UUID inorder to hit this api 
    path('requests/<uuid:request_id>/delete/', views.delete_milk_request, name='delete_milk_request'),#working✅, but once cross check on soft delete there can be multiple Milk request from single check if that be possible w.r.t BUsinness standpoint
    path('requests/by-date/', views.get_user_request, name='get_user_request'), #working✅
    
    # Admin
    path('admin/requests/', views.admin_get_requests, name='admin_get_requests'), #working✅
    path('admin/aggregate/', views.admin_get_aggregate, name='admin_get_aggregate'), #working✅
    path('admin/requests/<uuid:request_id>/override/', views.admin_override_request, name='admin_override_request'), #COnsider working✅, actually not needed at the moment so i did stopped testig 
]
