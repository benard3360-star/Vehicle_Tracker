"""
Check available plate numbers in database
"""
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord

def check_plate_numbers():
    """Check what plate numbers are available"""
    
    # Get total count
    total_records = ParkingRecord.objects.count()
    print(f"Total parking records: {total_records}")
    
    # Get sample plate numbers
    sample_plates = ParkingRecord.objects.values_list('plate_number', flat=True).distinct()[:20]
    print(f"\nSample plate numbers:")
    for i, plate in enumerate(sample_plates, 1):
        print(f"{i}. {plate}")
    
    # Check for specific patterns
    print(f"\nPlate numbers containing 'KCA':")
    kca_plates = ParkingRecord.objects.filter(plate_number__icontains='KCA').values_list('plate_number', flat=True).distinct()[:10]
    for plate in kca_plates:
        print(f"- {plate}")
    
    print(f"\nPlate numbers containing 'KAA':")
    kaa_plates = ParkingRecord.objects.filter(plate_number__icontains='KAA').values_list('plate_number', flat=True).distinct()[:10]
    for plate in kaa_plates:
        print(f"- {plate}")
    
    # Organizations
    orgs = ParkingRecord.objects.values_list('organization', flat=True).distinct()
    print(f"\nOrganizations: {list(orgs)}")

if __name__ == "__main__":
    check_plate_numbers()