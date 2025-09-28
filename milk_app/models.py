# milk_app/models.py
import uuid
from django.db import models
from django.utils import timezone

class User(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, unique=True)
    full_name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='customer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"
    
    class Meta:
        db_table = 'users'

class DailyMilkRequest(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
    ]
    MILK_TYPE_CHOICES = [
        ('buffalo', 'Buffalo'),
        ('cow', 'Cow'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='milk_requests')
    target_date = models.DateField()
    liters = models.DecimalField(max_digits=5, decimal_places=2)
    milk_type = models.CharField(max_length=10, choices=MILK_TYPE_CHOICES, default='buffalo')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'target_date']
        db_table = 'daily_milk_requests'
    
    def __str__(self):
        return f"{self.user.full_name} - {self.target_date} - {self.liters}L"



class UserSubscription(models.Model):
    """Main subscription record - tracks overall subscription status"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    is_active = models.BooleanField(default=True)
    subscription_start_date = models.DateField()
    subscription_end_date = models.DateField(null=True, blank=True)  # null = ongoing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.full_name} - Subscription"
    
    @property
    def current_rate(self):
        """Get current active rate"""
        current_rate = self.subscription_rates.filter(
            is_active=True,
            effective_from__lte=timezone.now().date()
        ).order_by('-effective_from').first()
        return current_rate
    
    class Meta:
        db_table = 'user_subscriptions'

class SubscriptionRate(models.Model):
    """Versioned rates - maintains complete history for billing"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='subscription_rates')
    daily_liters = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)  # null = current rate
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.subscription.user.full_name} - {self.daily_liters}L from {self.effective_from}"
    
    class Meta:
        db_table = 'subscription_rates'
        unique_together = ['subscription', 'effective_from']
        ordering = ['-effective_from']


class DailySkipRequest(models.Model):
    REASON_CHOICES = [
        ('traveling', 'Traveling'),
        ('excess_stock', 'Have Excess Stock'),
        ('health', 'Health Reasons'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='skip_requests')
    skip_date = models.DateField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='other')
    notes = models.TextField(blank=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.full_name} - Skip {self.skip_date}"
    
    class Meta:
        unique_together = ['user', 'skip_date']
        db_table = 'daily_skip_requests'


class DailyMilkDelivery(models.Model):
    """Auto-generated delivery records for tracking and billing"""
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('skipped', 'Skipped by User'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliveries')
    delivery_date = models.DateField()
    scheduled_liters = models.DecimalField(max_digits=5, decimal_places=2)
    actual_liters = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    rate_applied = models.ForeignKey(SubscriptionRate, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'delivery_date']
        db_table = 'daily_milk_deliveries'