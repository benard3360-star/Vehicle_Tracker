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

def analyze_vehicle(plate_number):
    print(f"Analyzing vehicle: {plate_number}")
    
    # Get records for 2025-12-01
    records = ParkingRecord.objects.filter(
        plate_number=plate_number,
        entry_time__date='2025-12-01'
    ).order_by('entry_time')
    
    print(f"\nRecords for {plate_number} on 2025-12-01:")
    print("Time\t\tOrganization\t\tAmount\t\tDuration")
    print("-" * 60)
    
    total_amount = 0
    organizations = set()
    
    for record in records:
        total_amount += record.amount_paid
        organizations.add(record.organization)
        duration = record.parking_duration_minutes or 0
        
        print(f"{record.entry_time.strftime('%H:%M:%S')}\t{record.organization:<15}\tKSh {record.amount_paid}\t{duration} min")
    
    print("-" * 60)
    print(f"Total visits: {records.count()}")
    print(f"Total amount: KSh {total_amount}")
    print(f"Organizations visited: {len(organizations)}")
    print(f"Organizations: {', '.join(sorted(organizations))}")

if __name__ == '__main__':
    analyze_vehicle('KDD271S')