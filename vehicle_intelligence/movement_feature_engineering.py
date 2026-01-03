#!/usr/bin/env python
"""
Vehicle Movement Feature Engineering
Analyzes vehicle movements between organizations to derive intelligent features
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Max, Min, F, Q
from django.db import transaction

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import VehicleMovement, Vehicle, Organization, CustomUser

class VehicleMovementFeatureEngineer:
    """Advanced feature engineering for vehicle movement data"""
    
    def __init__(self):
        self.features_created = 0
        self.records_updated = 0
        
    def add_temporal_features(self):
        """Add time-based features to vehicle movements"""
        print("Adding temporal features to vehicle movements...")
        
        # Add temporal fields to VehicleMovement model if they don't exist
        from django.db import connection
        with connection.cursor() as cursor:
            # Check if temporal fields exist, if not add them
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'vehicle_movements' AND column_name = 'start_hour'
            """)
            
            if not cursor.fetchone():
                print("Adding temporal feature fields...")
                cursor.execute("""
                    ALTER TABLE vehicle_movements 
                    ADD COLUMN IF NOT EXISTS start_hour INTEGER,
                    ADD COLUMN IF NOT EXISTS start_day_of_week INTEGER,
                    ADD COLUMN IF NOT EXISTS start_month INTEGER,
                    ADD COLUMN IF NOT EXISTS start_quarter INTEGER,
                    ADD COLUMN IF NOT EXISTS is_weekend BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS is_business_hours BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS is_peak_hours BOOLEAN DEFAULT FALSE,
                    ADD COLUMN IF NOT EXISTS season VARCHAR(10),
                    ADD COLUMN IF NOT EXISTS trip_type VARCHAR(20),
                    ADD COLUMN IF NOT EXISTS is_inter_org_trip BOOLEAN DEFAULT FALSE
                """)
        
        updated_count = 0
        for movement in VehicleMovement.objects.all().iterator(chunk_size=1000):
            try:
                start_time = movement.start_time
                
                # Basic temporal features
                movement.start_hour = start_time.hour
                movement.start_day_of_week = start_time.weekday()
                movement.start_month = start_time.month
                movement.start_quarter = (start_time.month - 1) // 3 + 1
                
                # Time classifications
                movement.is_weekend = start_time.weekday() >= 5
                movement.is_business_hours = 9 <= start_time.hour <= 17
                movement.is_peak_hours = start_time.hour in [8, 9, 17, 18, 19]
                
                # Season
                month = start_time.month
                if month in [12, 1, 2]:
                    movement.season = 'winter'
                elif month in [3, 4, 5]:
                    movement.season = 'spring'
                elif month in [6, 7, 8]:
                    movement.season = 'summer'
                else:
                    movement.season = 'autumn'
                
                # Trip type analysis
                if movement.start_location == movement.end_location:
                    movement.trip_type = 'round_trip'
                elif 'home' in movement.start_location.lower() or 'home' in movement.end_location.lower():
                    movement.trip_type = 'commute'
                else:
                    movement.trip_type = 'business'
                
                # Inter-organization trip detection
                movement.is_inter_org_trip = movement.start_location != movement.end_location
                
                # Update using raw SQL for performance
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE vehicle_movements SET 
                        start_hour = %s, start_day_of_week = %s, start_month = %s, 
                        start_quarter = %s, is_weekend = %s, is_business_hours = %s,
                        is_peak_hours = %s, season = %s, trip_type = %s, is_inter_org_trip = %s
                        WHERE id = %s
                    """, [
                        movement.start_hour, movement.start_day_of_week, movement.start_month,
                        movement.start_quarter, movement.is_weekend, movement.is_business_hours,
                        movement.is_peak_hours, movement.season, movement.trip_type, 
                        movement.is_inter_org_trip, movement.id
                    ])
                
                updated_count += 1
                if updated_count % 1000 == 0:
                    print(f"   Updated {updated_count} movements...")
                    
            except Exception as e:
                print(f"Error updating movement {movement.id}: {e}")
                continue
        
        print(f"Added temporal features to {updated_count} vehicle movements")
        return updated_count
    
    def add_vehicle_behavior_features(self):
        """Add vehicle-specific behavioral features"""
        print("Adding vehicle behavior features...")
        
        # Add vehicle behavior fields
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE vehicle_movements 
                ADD COLUMN IF NOT EXISTS vehicle_trip_count INTEGER,
                ADD COLUMN IF NOT EXISTS vehicle_total_distance DECIMAL(12,2),
                ADD COLUMN IF NOT EXISTS vehicle_avg_speed DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS vehicle_usage_pattern VARCHAR(20),
                ADD COLUMN IF NOT EXISTS is_frequent_route BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS route_efficiency_score DECIMAL(5,2)
            """)
        
        # Calculate vehicle statistics
        vehicle_stats = VehicleMovement.objects.values('vehicle').annotate(
            total_trips=Count('id'),
            total_distance=Sum('distance_km'),
            avg_speed=Avg('average_speed_kmh'),
            unique_routes=Count('start_location', distinct=True)
        )
        
        updated_count = 0
        for stats in vehicle_stats:
            try:
                vehicle_id = stats['vehicle']
                total_trips = stats['total_trips']
                total_distance = stats['total_distance'] or 0
                avg_speed = stats['avg_speed'] or 0
                unique_routes = stats['unique_routes']
                
                # Determine usage pattern
                if total_trips >= 100:
                    usage_pattern = 'heavy'
                elif total_trips >= 50:
                    usage_pattern = 'moderate'
                elif total_trips >= 20:
                    usage_pattern = 'light'
                else:
                    usage_pattern = 'minimal'
                
                # Calculate route efficiency (distance vs time ratio)
                movements = VehicleMovement.objects.filter(vehicle_id=vehicle_id)
                for movement in movements:
                    # Route frequency analysis
                    route_count = VehicleMovement.objects.filter(
                        vehicle_id=vehicle_id,
                        start_location=movement.start_location,
                        end_location=movement.end_location
                    ).count()
                    
                    is_frequent = route_count >= 5
                    
                    # Efficiency score (0-100)
                    if movement.duration_minutes > 0 and movement.distance_km > 0:
                        expected_time = movement.distance_km * 2  # Assume 30 km/h average
                        efficiency = max(0, 100 - abs(movement.duration_minutes - expected_time) / expected_time * 100)
                    else:
                        efficiency = 50
                    
                    # Update movement
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE vehicle_movements SET 
                            vehicle_trip_count = %s, vehicle_total_distance = %s,
                            vehicle_avg_speed = %s, vehicle_usage_pattern = %s,
                            is_frequent_route = %s, route_efficiency_score = %s
                            WHERE id = %s
                        """, [
                            total_trips, total_distance, avg_speed, usage_pattern,
                            is_frequent, efficiency, movement.id
                        ])
                    
                    updated_count += 1
                    
            except Exception as e:
                print(f"Error updating vehicle {vehicle_id}: {e}")
                continue
        
        print(f"Added behavior features to {updated_count} movements")
        return updated_count
    
    def add_organization_features(self):
        """Add organization-specific features"""
        print("Adding organization features...")
        
        # Add organization fields
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE vehicle_movements 
                ADD COLUMN IF NOT EXISTS org_vehicle_count INTEGER,
                ADD COLUMN IF NOT EXISTS org_total_trips INTEGER,
                ADD COLUMN IF NOT EXISTS org_avg_distance DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS org_activity_level VARCHAR(20)
            """)
        
        # Get organization statistics from vehicle movements
        # We'll use start_location as organization identifier
        org_stats = VehicleMovement.objects.values('start_location').annotate(
            total_trips=Count('id'),
            unique_vehicles=Count('vehicle', distinct=True),
            avg_distance=Avg('distance_km'),
            total_distance=Sum('distance_km')
        )
        
        updated_count = 0
        for stats in org_stats:
            try:
                location = stats['start_location']
                total_trips = stats['total_trips']
                unique_vehicles = stats['unique_vehicles']
                avg_distance = stats['avg_distance'] or 0
                
                # Determine activity level
                if total_trips >= 1000:
                    activity_level = 'very_high'
                elif total_trips >= 500:
                    activity_level = 'high'
                elif total_trips >= 100:
                    activity_level = 'moderate'
                else:
                    activity_level = 'low'
                
                # Update all movements from this location
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE vehicle_movements SET 
                        org_vehicle_count = %s, org_total_trips = %s,
                        org_avg_distance = %s, org_activity_level = %s
                        WHERE start_location = %s
                    """, [
                        unique_vehicles, total_trips, avg_distance, 
                        activity_level, location
                    ])
                
                updated_count += VehicleMovement.objects.filter(start_location=location).count()
                
            except Exception as e:
                print(f"Error updating organization {location}: {e}")
                continue
        
        print(f"Added organization features to {updated_count} movements")
        return updated_count
    
    def add_driver_features(self):
        """Add driver-specific features"""
        print("Adding driver features...")
        
        # Add driver fields
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE vehicle_movements 
                ADD COLUMN IF NOT EXISTS driver_trip_count INTEGER,
                ADD COLUMN IF NOT EXISTS driver_avg_speed DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS driver_efficiency_rating DECIMAL(5,2),
                ADD COLUMN IF NOT EXISTS driver_experience_level VARCHAR(20)
            """)
        
        # Calculate driver statistics
        driver_stats = VehicleMovement.objects.filter(driver__isnull=False).values('driver').annotate(
            total_trips=Count('id'),
            avg_speed=Avg('average_speed_kmh'),
            avg_distance=Avg('distance_km'),
            total_fuel=Sum('fuel_consumed_liters')
        )
        
        updated_count = 0
        for stats in driver_stats:
            try:
                driver_id = stats['driver']
                total_trips = stats['total_trips']
                avg_speed = stats['avg_speed'] or 0
                avg_distance = stats['avg_distance'] or 0
                total_fuel = stats['total_fuel'] or 0
                
                # Calculate efficiency rating (fuel per km)
                if avg_distance > 0 and total_fuel > 0:
                    fuel_efficiency = total_fuel / (total_trips * avg_distance)
                    efficiency_rating = max(0, 100 - fuel_efficiency * 10)
                else:
                    efficiency_rating = 50
                
                # Determine experience level
                if total_trips >= 200:
                    experience_level = 'expert'
                elif total_trips >= 100:
                    experience_level = 'experienced'
                elif total_trips >= 50:
                    experience_level = 'intermediate'
                else:
                    experience_level = 'novice'
                
                # Update all movements by this driver
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE vehicle_movements SET 
                        driver_trip_count = %s, driver_avg_speed = %s,
                        driver_efficiency_rating = %s, driver_experience_level = %s
                        WHERE driver_id = %s
                    """, [
                        total_trips, avg_speed, efficiency_rating, 
                        experience_level, driver_id
                    ])
                
                updated_count += VehicleMovement.objects.filter(driver_id=driver_id).count()
                
            except Exception as e:
                print(f"Error updating driver {driver_id}: {e}")
                continue
        
        print(f"Added driver features to {updated_count} movements")
        return updated_count
    
    def generate_summary_report(self):
        """Generate a comprehensive summary of the feature engineering"""
        print("\nGenerating Feature Engineering Summary...")
        
        from django.db import connection
        
        # Get basic statistics
        total_movements = VehicleMovement.objects.count()
        total_vehicles = Vehicle.objects.count()
        total_organizations = Organization.objects.count()
        
        # Get feature statistics using raw SQL
        with connection.cursor() as cursor:
            # Temporal features
            cursor.execute("SELECT COUNT(*) FROM vehicle_movements WHERE start_hour IS NOT NULL")
            temporal_features = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vehicle_movements WHERE is_weekend = true")
            weekend_trips = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vehicle_movements WHERE is_peak_hours = true")
            peak_hour_trips = cursor.fetchone()[0]
            
            # Behavior features
            cursor.execute("SELECT COUNT(*) FROM vehicle_movements WHERE vehicle_usage_pattern IS NOT NULL")
            behavior_features = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vehicle_movements WHERE is_frequent_route = true")
            frequent_routes = cursor.fetchone()[0]
            
            # Organization features
            cursor.execute("SELECT COUNT(DISTINCT start_location) FROM vehicle_movements WHERE org_activity_level IS NOT NULL")
            active_locations = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"VEHICLE MOVEMENT FEATURE ENGINEERING SUMMARY")
        print(f"{'='*60}")
        print(f"Total Vehicle Movements: {total_movements:,}")
        print(f"Total Vehicles: {total_vehicles:,}")
        print(f"Total Organizations: {total_organizations:,}")
        print(f"Active Locations: {active_locations:,}")
        
        print(f"\nTemporal Features:")
        print(f"  Movements with temporal data: {temporal_features:,} ({temporal_features/total_movements*100:.1f}%)")
        print(f"  Weekend trips: {weekend_trips:,} ({weekend_trips/total_movements*100:.1f}%)")
        print(f"  Peak hour trips: {peak_hour_trips:,} ({peak_hour_trips/total_movements*100:.1f}%)")
        
        print(f"\nBehavior Features:")
        print(f"  Movements with behavior data: {behavior_features:,} ({behavior_features/total_movements*100:.1f}%)")
        print(f"  Frequent routes: {frequent_routes:,} ({frequent_routes/total_movements*100:.1f}%)")
        
        print(f"\nFeature Engineering Complete!")
        print(f"Your vehicle movement data is now enhanced with intelligent features.")
        
        return {
            'total_movements': total_movements,
            'temporal_coverage': temporal_features/total_movements*100 if total_movements > 0 else 0,
            'weekend_percentage': weekend_trips/total_movements*100 if total_movements > 0 else 0,
            'peak_hour_percentage': peak_hour_trips/total_movements*100 if total_movements > 0 else 0,
            'frequent_routes': frequent_routes,
            'active_locations': active_locations
        }
    
    def run_complete_feature_engineering(self):
        """Run the complete feature engineering pipeline"""
        print("Starting Vehicle Movement Feature Engineering Pipeline")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            with transaction.atomic():
                # Run all feature engineering steps
                self.add_temporal_features()
                self.add_vehicle_behavior_features()
                self.add_organization_features()
                self.add_driver_features()
                
                # Generate summary
                summary = self.generate_summary_report()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"\nFeature Engineering Pipeline Complete!")
                print(f"Total Time: {duration:.2f} seconds")
                
                return summary
                
        except Exception as e:
            print(f"Error in feature engineering pipeline: {e}")
            raise

def main():
    """Main execution function"""
    engineer = VehicleMovementFeatureEngineer()
    summary = engineer.run_complete_feature_engineering()
    
    print(f"\nVehicle Movement Feature Engineering completed successfully!")
    print(f"Enhanced {summary['total_movements']:,} movement records with intelligent features.")
    print(f"Your system is now ready for advanced vehicle intelligence analytics!")

if __name__ == "__main__":
    main()