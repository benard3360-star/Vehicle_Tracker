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
from django.db.models import Count

def find_multi_org_vehicles():
    print("Finding vehicles that visited multiple organizations on the same day...")
    
    # Find vehicles that visited United Mall and other organizations on the same day
    vehicles_with_multiple_orgs = ParkingRecord.objects.values(
        'plate_number', 'entry_time__date'
    ).annotate(
        org_count=Count('organization', distinct=True)
    ).filter(
        org_count__gt=1
    ).order_by('-org_count')
    
    print(f"Found {vehicles_with_multiple_orgs.count()} vehicle-date combinations with multiple organizations")
    
    # Look for specific cases with United Mall
    for vehicle_date in vehicles_with_multiple_orgs[:10]:
        plate = vehicle_date['plate_number']
        date = vehicle_date['entry_time__date']
        org_count = vehicle_date['org_count']
        
        # Get the organizations visited by this vehicle on this date
        orgs_visited = ParkingRecord.objects.filter(
            plate_number=plate,
            entry_time__date=date
        ).values_list('organization', flat=True).distinct()
        
        orgs_list = list(orgs_visited)
        
        # Check if United Mall is one of them
        if 'United Mall' in orgs_list:
            print(f"\nPERFECT MATCH: {plate} on {date}")
            print(f"   Organizations visited ({org_count}): {', '.join(orgs_list)}")
            
            # Show detailed records for this vehicle on this date
            records = ParkingRecord.objects.filter(
                plate_number=plate,
                entry_time__date=date
            ).order_by('entry_time')
            
            print("   Detailed visits:")
            for record in records:
                print(f"     {record.entry_time.strftime('%H:%M:%S')} - {record.organization} - KSh {record.amount_paid}")
            
            return plate  # Return the first good example
    
    # If no United Mall examples, show any multi-org vehicle
    if vehicles_with_multiple_orgs.exists():
        example = vehicles_with_multiple_orgs.first()
        plate = example['plate_number']
        date = example['entry_time__date']
        
        orgs_visited = ParkingRecord.objects.filter(
            plate_number=plate,
            entry_time__date=date
        ).values_list('organization', flat=True).distinct()
        
        print(f"\nAlternative example: {plate} on {date}")
        print(f"   Organizations: {', '.join(orgs_visited)}")
        
        return plate
    
    return None

if __name__ == '__main__':
    result = find_multi_org_vehicles()
    if result:
        print(f"\nTest with vehicle: {result}")
    else:
        print("\nNo vehicles found with multiple organization visits on same day")