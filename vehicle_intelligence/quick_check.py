"""
Quick check for plate numbers
"""
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord

# Get first 5 plate numbers
plates = ParkingRecord.objects.values_list('plate_number', flat=True)[:5]
print("First 5 plate numbers:")
for plate in plates:
    print(f"- {plate}")

# Check if "Benadom" exists
benadom_count = ParkingRecord.objects.filter(plate_number__icontains='Benadom').count()
print(f"\nRecords containing 'Benadom': {benadom_count}")

# Check for KCA plates
kca_count = ParkingRecord.objects.filter(plate_number__icontains='KCA').count()
print(f"Records containing 'KCA': {kca_count}")

if kca_count > 0:
    kca_sample = ParkingRecord.objects.filter(plate_number__icontains='KCA').first()
    print(f"Sample KCA plate: {kca_sample.plate_number}")