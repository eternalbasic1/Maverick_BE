"""
Script to add initial milk pricing data
Run with: python manage.py shell < milk_app/scripts/add_initial_pricing.py
Or copy-paste into: python manage.py shell
"""
from decimal import Decimal
from django.utils import timezone
from milk_app.models import MilkPricing

# Get today's date
today = timezone.now().date()

# Initial pricing data
pricing_data = [
    {'liters': Decimal('0.5'), 'price': Decimal('50.00')},
    {'liters': Decimal('1.0'), 'price': Decimal('100.00')},
    {'liters': Decimal('1.5'), 'price': Decimal('150.00')},
    {'liters': Decimal('2.0'), 'price': Decimal('200.00')},
    {'liters': Decimal('2.5'), 'price': Decimal('250.00')},
    {'liters': Decimal('3.5'), 'price': Decimal('300.00')},
]

# Check if pricing already exists
existing_count = MilkPricing.objects.filter(effective_from=today, effective_to__isnull=True).count()

if existing_count > 0:
    print(f"⚠️  Found {existing_count} existing pricing records for today. Skipping...")
    print("If you want to add new pricing, please delete existing ones first or use a different date.")
else:
    # Create pricing records
    created_count = 0
    for data in pricing_data:
        pricing, created = MilkPricing.objects.get_or_create(
            liters=data['liters'],
            effective_from=today,
            effective_to=None,
            defaults={'price': data['price']}
        )
        if created:
            created_count += 1
            print(f"✅ Created pricing: {pricing.liters}L = ₹{pricing.price}")
        else:
            print(f"ℹ️  Pricing already exists: {pricing.liters}L = ₹{pricing.price}")
    
    print(f"\n✨ Successfully added {created_count} new pricing records!")

