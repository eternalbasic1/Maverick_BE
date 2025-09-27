# milk_app/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from .permission import IsJWTAuthenticated
from datetime import datetime
import jwt
from django.conf import settings

from .models import User, DailyMilkRequest
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, RefreshTokenSerializer,
    UserSerializer, DailyMilkRequestSerializer, AdminRequestUpdateSerializer
)
from .utils import generate_jwt_tokens, is_past_cutoff
from .firebase_config import FirebaseConfig

# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        full_name = serializer.validated_data['full_name']
        
        # Verify Firebase token
        firebase_config = FirebaseConfig()
        decoded_token = firebase_config.verify_id_token(
            serializer.validated_data['firebase_id_token']
        )
        
        if not decoded_token:
            return Response(
                {'error': 'Invalid Firebase ID token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create or get user
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={'full_name': full_name}
            )
            
            if not created:
                # Update full name if user exists
                user.full_name = full_name
                user.save()
            
            # Generate JWT tokens
            access_token, refresh_token = generate_jwt_tokens(user)
            
            return Response({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except IntegrityError:
            return Response(
                {'error': 'User with this phone number already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        phone_number = serializer.validated_data['phone_number']
        
        # Verify Firebase token
        firebase_config = FirebaseConfig()
        decoded_token = firebase_config.verify_id_token(
            serializer.validated_data['firebase_id_token']
        )
        
        if not decoded_token:
            return Response(
                {'error': 'Invalid Firebase ID token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(phone_number=phone_number)
            access_token, refresh_token = generate_jwt_tokens(user)
            
            return Response({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': UserSerializer(user).data
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found. Please sign up first.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    serializer = RefreshTokenSerializer(data=request.data)
    if serializer.is_valid():
        try:
            payload = jwt.decode(
                serializer.validated_data['refresh_token'], 
                settings.JWT_SECRET_KEY, 
                algorithms=['HS256']
            )
            
            if payload.get('type') != 'refresh':
                return Response(
                    {'error': 'Invalid token type'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user = User.objects.get(id=payload['user_id'])
            access_token, new_refresh_token = generate_jwt_tokens(user)
            
            return Response({
                'access_token': access_token,
                'refresh_token': new_refresh_token
            })
            
        except jwt.ExpiredSignatureError:
            return Response(
                {'error': 'Refresh token expired'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.InvalidTokenError:
            return Response(
                {'error': 'Invalid refresh token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# User Views
@api_view(['GET', 'PUT'])
@permission_classes([IsJWTAuthenticated])
def user_profile(request):
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Milk Request Views
@api_view(['POST'])
@permission_classes([IsJWTAuthenticated])
def create_milk_request(request):
    serializer = DailyMilkRequestSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        try:
            milk_request = serializer.save(user=request.user)
            return Response(
                DailyMilkRequestSerializer(milk_request).data, 
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {'error': 'Request for this date already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([IsJWTAuthenticated])
def update_milk_request(request, request_id):
    milk_request = get_object_or_404(
        DailyMilkRequest, 
        id=request_id, 
        user=request.user
    )
    
    # Check cutoff time
    if is_past_cutoff(milk_request.target_date, request.user.timezone):
        return Response(
            {'error': f'Cannot modify request for {milk_request.target_date}. Cutoff time has passed.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = DailyMilkRequestSerializer(
        milk_request, 
        data=request.data, 
        partial=True, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsJWTAuthenticated])
def delete_milk_request(request, request_id):
    milk_request = get_object_or_404(
        DailyMilkRequest, 
        id=request_id, 
        user=request.user
    )
    
    # Check cutoff time
    if is_past_cutoff(milk_request.target_date, request.user.timezone):
        return Response(
            {'error': f'Cannot cancel request for {milk_request.target_date}. Cutoff time has passed.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    milk_request.status = 'cancelled'
    milk_request.save()
    
    return Response({'message': 'Request cancelled successfully'})

@api_view(['GET'])
@permission_classes([IsJWTAuthenticated])
def get_user_request(request):
    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'error': 'Date parameter is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        milk_request = DailyMilkRequest.objects.get(
            user=request.user, 
            target_date=target_date
        )
        serializer = DailyMilkRequestSerializer(milk_request)
        return Response(serializer.data)
    except DailyMilkRequest.DoesNotExist:
        return Response(
            {'error': 'No request found for this date'}, 
            status=status.HTTP_404_NOT_FOUND
        )

# Admin Views
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'admin':
            return Response(
                {'error': 'Admin access required'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(request, *args, **kwargs)
    return wrapper

@api_view(['GET'])
@permission_classes([IsJWTAuthenticated])
@admin_required
def admin_get_requests(request):
    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'error': 'Date parameter is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    requests = DailyMilkRequest.objects.filter(target_date=target_date).select_related('user')
    
    data = []
    for req in requests:
        data.append({
            'id': req.id,
            'user_name': req.user.full_name,
            'user_phone': req.user.phone_number,
            'target_date': req.target_date,
            'liters': req.liters,
            'status': req.status,
            'created_at': req.created_at,
            'updated_at': req.updated_at
        })
    
    return Response(data)

@api_view(['GET'])
@permission_classes([IsJWTAuthenticated])
@admin_required
def admin_get_aggregate(request):
    date_str = request.GET.get('date')
    if not date_str:
        return Response(
            {'error': 'Date parameter is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    aggregate_data = DailyMilkRequest.objects.filter(
        target_date=target_date,
        status='confirmed'
    ).aggregate(
        total_liters=Sum('liters'),
        active_users=Count('user', distinct=True)
    )
    
    return Response({
        'total_liters': aggregate_data['total_liters'] or 0,
        'active_users': aggregate_data['active_users'] or 0,
        'date': target_date
    })

@api_view(['PUT'])
@permission_classes([IsJWTAuthenticated])
@admin_required
def admin_override_request(request, request_id):
    milk_request = get_object_or_404(DailyMilkRequest, id=request_id)
    
    serializer = AdminRequestUpdateSerializer(
        milk_request, 
        data=request.data, 
        partial=True
    )
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'id': milk_request.id,
            'user_name': milk_request.user.full_name,
            'user_phone': milk_request.user.phone_number,
            'target_date': milk_request.target_date,
            'liters': milk_request.liters,
            'status': milk_request.status,
            'updated_at': milk_request.updated_at
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
