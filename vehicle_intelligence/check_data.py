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

def check_parking_data():
    print("Checking parking records data...")
    
    total_records = ParkingRecord.objects.count()
    print(f"Total parking records: {total_records}")
    
    if total_records > 0:
        print("\nSample records:")
        for record in ParkingRecord.objects.all()[:10]:
            print(f"  {record.plate_number} - {record.organization} - {record.entry_time}")
        
        print(f"\nSearching for 'KCA536Y':")
        kca_records = ParkingRecord.objects.filter(plate_number__iexact='KCA536Y')
        print(f"Found {kca_records.count()} records for KCA536Y")
        
        if kca_records.exists():
            for record in kca_records:
                print(f"  {record.plate_number} - {record.organization} - {record.entry_time}")
        
        print(f"\nAll unique plate numbers (first 20):")
        unique_plates = ParkingRecord.objects.values_list('plate_number', flat=True).distinct()[:20]
        for plate in unique_plates:
            print(f"  {plate}")
    else:
        print("No parking records found in database!")

if __name__ == '__main__':
    check_parking_data()