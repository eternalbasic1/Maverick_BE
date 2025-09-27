
# milk_app/serializers.py
from rest_framework import serializers
from .models import User, DailyMilkRequest
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