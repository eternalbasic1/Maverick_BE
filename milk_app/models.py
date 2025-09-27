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
