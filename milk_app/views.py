# milk_app/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q
from .permission import IsJWTAuthenticated, IsAdmin, IsOwnerOrAdmin
from datetime import datetime
from django.utils import timezone

import jwt
from django.conf import settings

from .models import DailyMilkDelivery, DailySkipRequest, SubscriptionRate, User, DailyMilkRequest, UserSubscription
from .serializers import (
    CreateSubscriptionSerializer, DailyMilkDeliverySerializer, SubscriptionRateSerializer, UpdateSubscriptionRateSerializer, UserRegistrationSerializer, UserLoginSerializer, RefreshTokenSerializer,
    UserSerializer, DailyMilkRequestSerializer, AdminRequestUpdateSerializer, UserSubscriptionSerializer, DailySkipRequestSerializer,
     
)   
from .utils import generate_jwt_tokens, is_past_cutoff
from .firebase_config import FirebaseConfig


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


# New Subscription Views
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsJWTAuthenticated])
def user_subscription(request):
    """Manage user's milk subscription"""
    if request.method == 'GET':
        try:
            subscription = UserSubscription.objects.get(user=request.user)
            serializer = UserSubscriptionSerializer(subscription)
            return Response(serializer.data)
        except UserSubscription.DoesNotExist:
            return Response({'message': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
    
 
    elif request.method == 'POST':
        # Create new subscription with initial rate
        try:
            existing = UserSubscription.objects.get(user=request.user, is_active=True)
            return Response(
                {'error': 'Active subscription already exists. Use rate update endpoint to change daily liters.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except UserSubscription.DoesNotExist:
            pass
        
        serializer = CreateSubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():  # Ensure both records are created together
                # Create subscription
                subscription = UserSubscription.objects.create(
                    user=request.user,
                    subscription_start_date=serializer.validated_data['subscription_start_date']
                )
                
                # Create initial rate
                initial_rate = SubscriptionRate.objects.create(
                    subscription=subscription,
                    daily_liters=serializer.validated_data['daily_liters'],
                    effective_from=serializer.validated_data['subscription_start_date']
                )
                
                # Refresh subscription to get the current_rate
                subscription.refresh_from_db()
                
            return Response({
                'message': 'Subscription created successfully',
                'subscription': UserSubscriptionSerializer(subscription).data,
                'initial_rate': SubscriptionRateSerializer(initial_rate).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'PUT':
        # Update existing subscription
        try:
            subscription = UserSubscription.objects.get(user=request.user, is_active=True)
            serializer = UserSubscriptionSerializer(subscription, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except UserSubscription.DoesNotExist:
            return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsJWTAuthenticated])
def update_subscription_rate(request):
    """Update subscription rate - creates new rate version"""
    try:
        subscription = UserSubscription.objects.get(user=request.user, is_active=True)
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = UpdateSubscriptionRateSerializer(data=request.data)
    if serializer.is_valid():
        new_daily_liters = serializer.validated_data['new_daily_liters']
        effective_from = serializer.validated_data['effective_from']
        
        # Check if there's already a rate for this date
        existing_rate = SubscriptionRate.objects.filter(
            subscription=subscription,
            effective_from=effective_from
        ).first()
        
        if existing_rate:
            return Response(
                {'error': f'Rate already exists for {effective_from}. Cannot create duplicate.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # End current active rate if new rate is immediate
        current_rate = subscription.current_rate
        if current_rate and effective_from <= timezone.now().date():
            current_rate.effective_to = effective_from - timezone.timedelta(days=1)
            current_rate.is_active = False
            current_rate.save()
        
        # Create new rate
        new_rate = SubscriptionRate.objects.create(
            subscription=subscription,
            daily_liters=new_daily_liters,
            effective_from=effective_from
        )
        
        return Response({
            'message': 'Subscription rate updated successfully',
            'new_rate': SubscriptionRateSerializer(new_rate).data,
            'effective_from': effective_from
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsJWTAuthenticated])
def subscription_billing_history(request):
    """Get billing history with rate changes"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date or not end_date:
        return Response(
            {'error': 'start_date and end_date parameters are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        subscription = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No subscription found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get all rates that were active during the period
    rates_in_period = SubscriptionRate.objects.filter(
        subscription=subscription,
        effective_from__lte=end_date,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=start_date)
    ).order_by('effective_from')
    
    # Get deliveries in period
    deliveries = DailyMilkDelivery.objects.filter(
        user=request.user,
        delivery_date__range=[start_date, end_date],
        status='delivered'
    ).order_by('delivery_date')
    
    billing_data = []
    total_liters = 0
    total_days = 0
    
    for rate in rates_in_period:
        rate_start = max(rate.effective_from, datetime.strptime(start_date, '%Y-%m-%d').date())
        rate_end = min(rate.effective_to or datetime.strptime(end_date, '%Y-%m-%d').date(), 
                      datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # Count delivered days for this rate
        rate_deliveries = deliveries.filter(
            delivery_date__range=[rate_start, rate_end],
            rate_applied=rate
        )
        
        days_count = rate_deliveries.count()
        liters_delivered = sum(float(d.actual_liters or d.scheduled_liters) for d in rate_deliveries)
        
        if days_count > 0:
            billing_data.append({
                'rate_id': rate.id,
                'daily_liters': rate.daily_liters,
                'effective_from': rate.effective_from,
                'effective_to': rate.effective_to,
                'days_delivered': days_count,
                'total_liters': liters_delivered
            })
            
            total_liters += liters_delivered
            total_days += days_count
    
    return Response({
        'billing_period': {'start_date': start_date, 'end_date': end_date},
        'total_days_delivered': total_days,
        'total_liters_delivered': total_liters,
        'rate_breakdown': billing_data
    })


@api_view(['POST'])
@permission_classes([IsJWTAuthenticated])
def skip_delivery(request):
    """Request to skip delivery for specific date"""
    serializer = DailySkipRequestSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        try:
            skip_request = serializer.save(user=request.user)
            return Response(
                DailySkipRequestSerializer(skip_request).data, 
                status=status.HTTP_201_CREATED
            )
        except IntegrityError:
            return Response(
                {'error': 'Skip request for this date already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



@api_view(['GET'])
@permission_classes([IsJWTAuthenticated])
def user_skip_requests(request):
    """Get user's skip requests"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    skip_requests = DailySkipRequest.objects.filter(user=request.user)
    
    if start_date:
        skip_requests = skip_requests.filter(skip_date__gte=start_date)
    if end_date:
        skip_requests = skip_requests.filter(skip_date__lte=end_date)
    
    skip_requests = skip_requests.order_by('-skip_date')
    
    serializer = DailySkipRequestSerializer(skip_requests, many=True)
    return Response(serializer.data)



@api_view(['DELETE'])
@permission_classes([IsJWTAuthenticated])
def cancel_skip_request(request, skip_id):
    """Cancel a skip request (if before cutoff)"""
    skip_request = get_object_or_404(DailySkipRequest, id=skip_id, user=request.user)
    
    # Check if past cutoff time
    if is_past_cutoff(skip_request.skip_date, request.user.timezone):
        return Response(
            {'error': f'Cannot cancel skip for {skip_request.skip_date}. Cutoff time has passed.'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    skip_request.delete()
    return Response({'message': 'Skip request cancelled successfully'})





# New Admin Views for Subscription System
# Updated Admin Views for Rate Versioning System
@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_delivery_schedule(request):
    """Get delivery schedule for a specific date with correct rates"""
    date_str = request.GET.get('date')
    if not date_str:
        return Response({'error': 'Date parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        delivery_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get all active subscriptions
    active_subscriptions = UserSubscription.objects.filter(
        is_active=True,
        subscription_start_date__lte=delivery_date,
    ).filter(
        Q(subscription_end_date__isnull=True) | Q(subscription_end_date__gte=delivery_date)
    ).select_related('user')
    
    # Get skip requests for this date
    skip_requests = DailySkipRequest.objects.filter(
        skip_date=delivery_date
    ).values_list('user_id', flat=True)
    
    # Build delivery schedule with correct rates
    deliveries = []
    total_liters = 0
    
    for subscription in active_subscriptions:
        if subscription.user.id not in skip_requests:
            # Get the rate applicable for this date
            applicable_rate = SubscriptionRate.objects.filter(
                subscription=subscription,
                effective_from__lte=delivery_date,
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=delivery_date)
            ).first()
            
            if applicable_rate:
                deliveries.append({
                    'user_id': subscription.user.id,
                    'user_name': subscription.user.full_name,
                    'user_phone': subscription.user.phone_number,
                    'scheduled_liters': applicable_rate.daily_liters,
                    'rate_id': applicable_rate.id,
                    'status': 'scheduled'
                })
                total_liters += applicable_rate.daily_liters
    
    return Response({
        'date': delivery_date,
        'total_deliveries': len(deliveries),
        'total_liters': total_liters,
        'deliveries': deliveries
    })
@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_billing_report(request):
    """Generate billing report for a user in a date range"""
    user_id = request.GET.get('user_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not all([user_id, start_date, end_date]):
        return Response({
            'error': 'user_id, start_date, and end_date parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = User.objects.get(id=user_id)
        subscription = UserSubscription.objects.get(user=user)
    except (User.DoesNotExist, UserSubscription.DoesNotExist):
        return Response({'error': 'User or subscription not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Parse dates
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get all rates active in the period
    rates_in_period = SubscriptionRate.objects.filter(
        subscription=subscription,
        effective_from__lte=end_date_obj,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=start_date_obj)
    ).order_by('effective_from')
    
    # Get actual deliveries
    deliveries = DailyMilkDelivery.objects.filter(
        user=user,
        delivery_date__range=[start_date_obj, end_date_obj],
        status='delivered'
    ).select_related('rate_applied').order_by('delivery_date')
    
    # Build billing breakdown
    billing_breakdown = []
    total_delivered_liters = 0
    total_delivered_days = 0
    
    for rate in rates_in_period:
        rate_start = max(rate.effective_from, start_date_obj)
        rate_end = min(rate.effective_to or end_date_obj, end_date_obj)
        
        # ✅ Filter on queryset (not serialized list)
        rate_deliveries = deliveries.filter(
            delivery_date__range=[rate_start, rate_end],
            rate_applied=rate
        )
        
        delivered_days = rate_deliveries.count()
        delivered_liters = sum(float(d.actual_liters or d.scheduled_liters) for d in rate_deliveries)
        
        total_days_in_range = (rate_end - rate_start).days + 1
        skip_days = DailySkipRequest.objects.filter(
            user=user,
            skip_date__range=[rate_start, rate_end]
        ).count()
        
        expected_delivery_days = total_days_in_range - skip_days
        
        billing_breakdown.append({
            'rate_id': str(rate.id),
            'daily_liters': str(rate.daily_liters),
            'effective_from': rate.effective_from,
            'effective_to': rate.effective_to,
            'period_start': rate_start,
            'period_end': rate_end,
            'expected_delivery_days': expected_delivery_days,
            'actual_delivery_days': delivered_days,
            'delivered_liters': delivered_liters,
            'delivery_success_rate': f"{(delivered_days/expected_delivery_days*100):.1f}%" if expected_delivery_days > 0 else "0%"
        })
        
        total_delivered_liters += delivered_liters
        total_delivered_days += delivered_days
    
    # ✅ Serialize only once at the end
    deliveries_serialized = DailyMilkDeliverySerializer(deliveries, many=True).data
    
    return Response({
        'user': {
            'id': str(user.id),
            'name': user.full_name,
            'phone': user.phone_number
        },
        'billing_period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'summary': {
            'total_delivered_days': total_delivered_days,
            'total_delivered_liters': total_delivered_liters
        },
        'rate_breakdown': billing_breakdown,
        'deliveries': deliveries_serialized
    })

    
@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_skip_requests(request):
    """Get all skip requests for a date range"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    skip_requests = DailySkipRequest.objects.select_related('user')
    
    if start_date:
        skip_requests = skip_requests.filter(skip_date__gte=start_date)
    if end_date:
        skip_requests = skip_requests.filter(skip_date__lte=end_date)
    
    skip_requests = skip_requests.order_by('-skip_date')
    
    data = []
    for skip in skip_requests:
        data.append({
            'id': skip.id,
            'user_name': skip.user.full_name,
            'user_phone': skip.user.phone_number,
            'skip_date': skip.skip_date,
            'reason': skip.reason,
            'notes': skip.notes,
            'created_at': skip.created_at
        })
    
    return Response(data)






@api_view(['PUT'])
@permission_classes([IsAdmin])
def admin_update_delivery_status(request):
    """Update delivery status for multiple users on a specific date"""
    delivery_date = request.data.get('delivery_date')
    deliveries = request.data.get('deliveries', [])  # List of {user_id, status, actual_liters}
    
    if not delivery_date or not deliveries:
        return Response(
            {'error': 'delivery_date and deliveries are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    updated_count = 0
    for delivery_data in deliveries:
        user_id = delivery_data.get('user_id')
        new_status = delivery_data.get('status')
        actual_liters = delivery_data.get('actual_liters')
        
        try:
            subscription = UserSubscription.objects.get(user_id=user_id)

            # ✅ get the correct rate for the delivery_date
            rate = subscription.subscription_rates.filter(
                effective_from__lte=delivery_date
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=delivery_date)
            ).order_by('-effective_from').first()

            if not rate:
                continue  # no valid rate found, skip this user

            scheduled_liters = rate.daily_liters

            delivery, created = DailyMilkDelivery.objects.get_or_create(
                user_id=user_id,
                delivery_date=delivery_date,
                defaults={
                    'scheduled_liters': scheduled_liters,
                    'status': new_status,
                    'actual_liters': actual_liters
                }
            )

            if not created:
                delivery.status = new_status
                if actual_liters is not None:
                    delivery.actual_liters = actual_liters
                delivery.scheduled_liters = scheduled_liters  # ✅ keep it updated if plan changes
                delivery.save()
            
            updated_count += 1
            
        except UserSubscription.DoesNotExist:
            continue
    
    return Response({
        'message': f'Updated {updated_count} deliveries',
        'delivery_date': delivery_date
    })

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









