#!/usr/bin/env python
"""
Vehicle Movement Feature Engineering Setup
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def main():
    print("Vehicle Movement Feature Engineering Setup")
    print("=" * 50)
    
    try:
        from main_app.models import VehicleMovement, Vehicle, Organization
        
        # Check current data
        print("1. Checking current data...")
        movement_count = VehicleMovement.objects.count()
        vehicle_count = Vehicle.objects.count()
        org_count = Organization.objects.count()
        
        print(f"   Vehicle Movements: {movement_count:,}")
        print(f"   Vehicles: {vehicle_count:,}")
        print(f"   Organizations: {org_count:,}")
        
        if movement_count == 0:
            print("\n   No vehicle movement data found.")
            print("   You need to create some sample vehicle movement data first.")
            
            # Create sample data
            create_sample = input("\n   Create sample vehicle movement data? (y/n): ").lower().strip()
            if create_sample == 'y':
                create_sample_data()
                movement_count = VehicleMovement.objects.count()
                print(f"   Created sample data: {movement_count:,} movements")
        
        if movement_count > 0:
            print(f"\n2. Running feature engineering on {movement_count:,} movements...")
            
            # Import and run feature engineering
            from movement_feature_engineering import VehicleMovementFeatureEngineer
            
            engineer = VehicleMovementFeatureEngineer()
            summary = engineer.run_complete_feature_engineering()
            
            print(f"\n✓ Feature engineering completed successfully!")
            print(f"  Enhanced {summary['total_movements']:,} movement records")
            print(f"  Ready for advanced vehicle intelligence analytics!")
            
        else:
            print("\n   No data to process. Please add vehicle movement data first.")
            
    except Exception as e:
        print(f"\nError: {e}")
        return False
    
    return True

def create_sample_data():
    """Create sample vehicle movement data for testing"""
    from main_app.models import VehicleMovement, Vehicle, Organization, CustomUser
    from datetime import datetime, timedelta
    import random
    
    print("   Creating sample organizations...")
    
    # Create sample organizations
    orgs = []
    org_names = ['JKIA', 'KNH', 'Green House Mall', 'United Mall', 'Greenspan Mall']
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
            print(f"     Created organization: {name}")
    
    print("   Creating sample vehicles...")
    
    # Create sample vehicles
    vehicles = []
    makes = ['Toyota', 'Nissan', 'Mazda', 'Honda', 'Subaru']
    models = ['Corolla', 'Camry', 'Prius', 'Civic', 'Accord']
    
    for i in range(10):
        vehicle, created = Vehicle.objects.get_or_create(
            vehicle_id=f'VH{i+1:03d}',
            defaults={
                'make': random.choice(makes),
                'model': random.choice(models),
                'year': random.randint(2015, 2023),
                'vin': f'VIN{i+1:014d}',
                'license_plate': f'KCA{i+1:03d}A',
                'fuel_type': random.choice(['gasoline', 'diesel', 'hybrid']),
                'organization': random.choice(orgs),
                'is_active': True
            }
        )
        vehicles.append(vehicle)
        if created:
            print(f"     Created vehicle: {vehicle.vehicle_id}")
    
    print("   Creating sample vehicle movements...")
    
    # Create sample movements
    locations = [org.name for org in orgs]
    
    movements_created = 0
    for i in range(100):
        start_time = datetime.now() - timedelta(days=random.randint(1, 30))
        duration = random.randint(30, 480)  # 30 minutes to 8 hours
        end_time = start_time + timedelta(minutes=duration)
        
        movement = VehicleMovement.objects.create(
            vehicle=random.choice(vehicles),
            trip_id=f'TRIP{i+1:06d}',
            start_location=random.choice(locations),
            end_location=random.choice(locations),
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration,
            distance_km=random.uniform(5, 50),
            fuel_consumed_liters=random.uniform(2, 15),
            fuel_cost=random.uniform(200, 1500),
            average_speed_kmh=random.uniform(20, 80),
            max_speed_kmh=random.uniform(40, 120),
            trip_status='completed'
        )
        movements_created += 1
    
    print(f"     Created {movements_created} sample movements")

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)