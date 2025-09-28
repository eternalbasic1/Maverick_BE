
# milk_app/serializers.py
from rest_framework import serializers
from .models import DailyMilkDelivery, DailySkipRequest, SubscriptionRate, User, DailyMilkRequest, UserSubscription
from .firebase_config import FirebaseConfig
from .utils import is_past_cutoff
from django.utils import timezone

class UserRegistrationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    full_name = serializers.CharField(max_length=255)
    firebase_id_token = serializers.CharField()
    
    def validate_firebase_id_token(self, value):
        firebase_config = FirebaseConfig()
        decoded_token = firebase_config.verify_id_token(value)
        if not decoded_token:
            raise serializers.ValidationError("Invalid Firebase ID token")
        return value
    
    def validate_phone_number(self, value):
        # Basic phone number validation
        if not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format")
        return value

class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    firebase_id_token = serializers.CharField()
    
    def validate_firebase_id_token(self, value):
        firebase_config = FirebaseConfig()
        decoded_token = firebase_config.verify_id_token(value)
        if not decoded_token:
            raise serializers.ValidationError("Invalid Firebase ID token")
        return value

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'phone_number', 'full_name', 'timezone', 'role', 'created_at', 'updated_at']
        read_only_fields = ['id', 'phone_number', 'role', 'created_at', 'updated_at']

class SubscriptionRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionRate
        fields = ['id', 'daily_liters', 'effective_from', 'effective_to', 'is_active', 'created_at']
        read_only_fields = ['id', 'effective_to', 'is_active', 'created_at']
        
class UserSubscriptionSerializer(serializers.ModelSerializer):
    current_rate = SubscriptionRateSerializer(read_only=True)
    rate_history = SubscriptionRateSerializer(source='subscription_rates', many=True, read_only=True)
    
    class Meta:
        model = UserSubscription
        fields = ['id', 'is_active', 'subscription_start_date', 'subscription_end_date', 
                 'current_rate', 'rate_history', 'created_at', 'updated_at']
        read_only_fields = ['id', 'current_rate', 'rate_history', 'created_at', 'updated_at']

class CreateSubscriptionSerializer(serializers.Serializer):
    daily_liters = serializers.DecimalField(max_digits=5, decimal_places=2)
    subscription_start_date = serializers.DateField()
    
    def validate_subscription_start_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Subscription start date cannot be in the past")
        return value  

class UpdateSubscriptionRateSerializer(serializers.Serializer):
    new_daily_liters = serializers.DecimalField(max_digits=5, decimal_places=2)
    effective_from = serializers.DateField()
    
    def validate_effective_from(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Rate change cannot be effective from past date")
        return value

class DailySkipRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySkipRequest
        fields = ['id', 'skip_date', 'reason', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_skip_date(self, value):
        user = self.context['request'].user
        
        # Check if skip date is in the past
        if value < timezone.now().date():
            raise serializers.ValidationError("Cannot skip delivery for past dates")
        
        # Check if past cutoff time (midnight before skip date)
        if is_past_cutoff(value, user.timezone):
            raise serializers.ValidationError(
                f"Cannot skip delivery for {value}. Cutoff time has passed."
            )
        
        return value
    
class DailyMilkDeliverySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    applied_rate = serializers.DecimalField(source='rate_applied.daily_liters', max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = DailyMilkDelivery
        fields = ['id', 'user_name', 'user_phone', 'delivery_date', 'scheduled_liters', 
                 'actual_liters', 'applied_rate', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_name', 'user_phone', 'applied_rate', 'created_at', 'updated_at']


class DailyMilkRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMilkRequest
        fields = ['id', 'target_date', 'liters', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, attrs):
        user = self.context['request'].user
        target_date = attrs.get('target_date')
        
        # Check if past cutoff time
        if is_past_cutoff(target_date, user.timezone):
            raise serializers.ValidationError(
                f"Cannot modify request for {target_date}. Cutoff time has passed."
            )
        
        return attrs

class AdminRequestUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMilkRequest
        fields = ['liters', 'status']



class DailyMilkDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMilkDelivery
        fields = [
            'id',
            'delivery_date',
            'scheduled_liters',
            'actual_liters',
            'status',
            'rate_applied'
        ]