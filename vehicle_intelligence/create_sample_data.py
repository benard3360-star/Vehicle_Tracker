"""
Create sample vehicle data directly in PostgreSQL for testing
"""
import os
import django
import sys
from datetime import datetime, timedelta
import random

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import Organization, Vehicle, VehicleMovement, CustomUser

def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample organizations...")
    
    # Create sample organizations
    orgs = []
    org_names = ['Nairobi Branch', 'Mombasa Branch', 'Kisumu Branch']
    
    for name in org_names:
        org, created = Organization.objects.get_or_create(
            name=name,
            defaults={
                'slug': name.lower().replace(' ', '-'),
                'email': f'admin@{name.lower().replace(" ", "")}.com',
                'is_active': True
            }
        )
        orgs.append(org)
        if created:
            print(f"Created organization: {name}")
    
    print("Creating sample vehicles...")
    
    # Create sample vehicles
    vehicles = []
    makes = ['Toyota', 'Nissan', 'Mitsubishi', 'Isuzu', 'Ford']
    models = ['Hilux', 'Navara', 'L200', 'D-Max', 'Ranger']
    
    for i in range(15):  # 15 vehicles
        org = random.choice(orgs)
        make = random.choice(makes)
        model = random.choice(models)
        
        vehicle, created = Vehicle.objects.get_or_create(
            vehicle_id=f"KE{str(i+1).zfill(3)}",
            defaults={
                'make': make,
                'model': model,
                'year': random.randint(2018, 2024),
                'vin': f"VIN{str(i+1).zfill(10)}",
                'license_plate': f"KE{random.randint(100, 999)}{chr(random.randint(65, 90))}",
                'fuel_type': random.choice(['gasoline', 'diesel']),
                'organization': org,
                'is_active': True
            }
        )
        vehicles.append(vehicle)
        if created:
            print(f"Created vehicle: {vehicle.vehicle_id}")
    
    print("Creating sample movements...")
    
    # Create sample movements
    locations = [
        'Nairobi CBD', 'Westlands', 'Karen', 'Kiambu', 'Thika',
        'Mombasa Port', 'Nyali', 'Diani', 'Malindi',
        'Kisumu City', 'Kakamega', 'Eldoret', 'Nakuru'
    ]
    
    movements_created = 0
    
    # Create movements for the last 30 days
    for day in range(30):
        date = datetime.now() - timedelta(days=day)
        
        # Random number of trips per day (2-8)
        daily_trips = random.randint(2, 8)
        
        for trip in range(daily_trips):
            vehicle = random.choice(vehicles)
            start_loc = random.choice(locations)
            end_loc = random.choice([loc for loc in locations if loc != start_loc])
            
            # Random trip times
            start_hour = random.randint(6, 20)
            start_minute = random.randint(0, 59)
            duration = random.randint(15, 180)  # 15 minutes to 3 hours
            
            start_time = date.replace(hour=start_hour, minute=start_minute, second=0)
            end_time = start_time + timedelta(minutes=duration)
            
            # Random trip metrics
            distance = random.uniform(5, 150)  # 5-150 km
            fuel_consumed = distance * random.uniform(0.08, 0.15)  # 8-15L/100km
            avg_speed = distance / (duration / 60) if duration > 0 else 50
            max_speed = avg_speed * random.uniform(1.1, 1.5)
            
            movement, created = VehicleMovement.objects.get_or_create(
                trip_id=f"TRIP_{date.strftime('%Y%m%d')}_{vehicle.vehicle_id}_{trip}",
                defaults={
                    'vehicle': vehicle,
                    'start_location': start_loc,
                    'end_location': end_loc,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': duration,
                    'distance_km': round(distance, 2),
                    'fuel_consumed_liters': round(fuel_consumed, 2),
                    'average_speed_kmh': round(avg_speed, 2),
                    'max_speed_kmh': round(max_speed, 2),
                    'trip_status': 'completed'
                }
            )
            
            if created:
                movements_created += 1
    
    print(f"\n=== SAMPLE DATA CREATED ===")
    print(f"Organizations: {len(orgs)}")
    print(f"Vehicles: {len(vehicles)}")
    print(f"Movements: {movements_created}")
    print("\nYou can now:")
    print("1. Run: python manage.py runserver")
    print("2. Login and go to Analytics")
    print("3. View your data!")

if __name__ == "__main__":
    create_sample_data()