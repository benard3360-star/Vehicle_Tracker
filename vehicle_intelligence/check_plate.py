#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord

def check_plate(plate_number):
    print(f"Searching for plate: {plate_number}")
    
    # Check exact match
    exact_records = ParkingRecord.objects.filter(plate_number__iexact=plate_number)
    print(f"Exact match records: {exact_records.count()}")
    
    # Check case-sensitive match
    case_records = ParkingRecord.objects.filter(plate_number=plate_number)
    print(f"Case-sensitive match records: {case_records.count()}")
    
    # Check contains match
    contains_records = ParkingRecord.objects.filter(plate_number__icontains=plate_number)
    print(f"Contains match records: {contains_records.count()}")
    
    # Show similar plates
    similar_plates = ParkingRecord.objects.filter(plate_number__startswith=plate_number[:3]).values_list('plate_number', flat=True).distinct()[:10]
    print(f"Similar plates starting with '{plate_number[:3]}': {list(similar_plates)}")
    
    if exact_records.exists():
        print("\nSample records:")
        for record in exact_records[:3]:
            print(f"  {record.plate_number} - {record.organization} - {record.entry_time}")

if __name__ == '__main__':
    check_plate('KDQ339K')