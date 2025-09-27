
# milk_app/utils.py
import jwt
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

def generate_jwt_tokens(user):
    """Generate access and refresh tokens for a user"""
    now = timezone.now()
    
    access_payload = {
        'user_id': str(user.id),
        'role': user.role,
        'exp': now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_LIFETIME),
        'iat': now,
        'type': 'access'
    }
    
    refresh_payload = {
        'user_id': str(user.id),
        'role': user.role,
        'exp': now + timedelta(seconds=settings.JWT_REFRESH_TOKEN_LIFETIME),
        'iat': now,
        'type': 'refresh'
    }
    
    access_token = jwt.encode(access_payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    
    return access_token, refresh_token

def get_user_timezone(user):
    """Get user's timezone object"""
    return pytz.timezone(user.timezone)

def get_cutoff_time(target_date, user_timezone):
    """Get cutoff time (00:00) for a target date in user's timezone"""
    user_tz = pytz.timezone(user_timezone)
    cutoff = datetime.combine(target_date, datetime.min.time())
    cutoff = user_tz.localize(cutoff)
    return cutoff

def is_past_cutoff(target_date, user_timezone):
    """Check if current time is past the cutoff for a target date"""
    cutoff_time = get_cutoff_time(target_date, user_timezone)
    current_time = timezone.now()
    return current_time >= cutoff_time