"""
Script to add initial milk pricing data (per liter pricing by milk type)
Run with: python manage.py shell < milk_app/scripts/add_initial_pricing.py
Or copy-paste into: python manage.py shell
"""
from decimal import Decimal
from django.utils import timezone
from milk_app.models import MilkPricing

# Get today's date
today = timezone.now().date()

# Initial pricing data - per liter pricing for each milk type
# Only storing 1-liter prices, total price will be calculated as: price_per_liter * liters
pricing_data = [
    {'milk_type': 'buffalo', 'liters': Decimal('1.0'), 'price': Decimal('96.00')},  # ₹96 per liter for buffalo milk
    {'milk_type': 'cow', 'liters': Decimal('1.0'), 'price': Decimal('80.00')},      # ₹80 per liter for cow milk
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
            milk_type=data['milk_type'],
            liters=Decimal('1.0'),  # Always 1.0 (per liter pricing)
            effective_from=today,
            effective_to=None,
            defaults={'price': data['price']}
        )
        if created:
            created_count += 1
            print(f"✅ Created pricing: {pricing.milk_type.capitalize()} Milk - {pricing.liters}L = ₹{pricing.price}/liter")
        else:
            print(f"ℹ️  Pricing already exists: {pricing.milk_type.capitalize()} Milk - {pricing.liters}L = ₹{pricing.price}/liter")
    
    print(f"\n✨ Successfully added {created_count} new pricing records!")
    print("💡 Note: Prices are per liter. Total price = price_per_liter × liters")

