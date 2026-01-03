#!/usr/bin/env python
"""
Simplified Vehicle Intelligence Feature Engineering
Works with existing data to create movement analytics
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import Organization, CustomUser

class SimpleVehicleIntelligence:
    """Simple vehicle intelligence system using existing data"""
    
    def __init__(self):
        self.features_created = 0
        
    def create_movement_analytics_table(self):
        """Create a table to store derived movement analytics"""
        print("Creating movement analytics table...")
        
        with connection.cursor() as cursor:
            # Create movement analytics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movement_analytics (
                    id SERIAL PRIMARY KEY,
                    vehicle_plate VARCHAR(20),
                    organization_from VARCHAR(100),
                    organization_to VARCHAR(100),
                    movement_date DATE,
                    movement_time TIME,
                    duration_minutes INTEGER,
                    movement_type VARCHAR(20),
                    
                    -- Temporal features
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    is_weekend BOOLEAN DEFAULT FALSE,
                    is_business_hours BOOLEAN DEFAULT FALSE,
                    is_peak_hours BOOLEAN DEFAULT FALSE,
                    season VARCHAR(10),
                    
                    -- Movement features
                    is_inter_org_movement BOOLEAN DEFAULT FALSE,
                    movement_frequency VARCHAR(20),
                    route_popularity INTEGER DEFAULT 0,
                    
                    -- Analytics features
                    vehicle_activity_score INTEGER DEFAULT 0,
                    organization_traffic_score INTEGER DEFAULT 0,
                    
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_movement_vehicle ON movement_analytics(vehicle_plate);
                CREATE INDEX IF NOT EXISTS idx_movement_org_from ON movement_analytics(organization_from);
                CREATE INDEX IF NOT EXISTS idx_movement_date ON movement_analytics(movement_date);
                CREATE INDEX IF NOT EXISTS idx_movement_weekend ON movement_analytics(is_weekend);
                CREATE INDEX IF NOT EXISTS idx_movement_peak ON movement_analytics(is_peak_hours);
            """)
        
        print("[SUCCESS] Movement analytics table created")
    
    def generate_sample_movement_data(self):
        """Generate sample movement data between organizations"""
        print("Generating sample movement data...")
        
        # Get existing organizations
        organizations = list(Organization.objects.all())
        if len(organizations) < 2:
            print("Creating sample organizations...")
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
                organizations.append(org)
                if created:
                    print(f"   Created organization: {name}")
        
        # Generate sample vehicle plates
        import random
        vehicle_plates = [f'KCA{i:03d}A' for i in range(1, 21)]  # 20 vehicles
        
        # Generate movements for the last 30 days
        movements_created = 0
        with connection.cursor() as cursor:
            for day in range(30):
                date = datetime.now().date() - timedelta(days=day)
                
                # Generate 10-50 movements per day
                daily_movements = random.randint(10, 50)
                
                for _ in range(daily_movements):
                    # Random movement time
                    hour = random.randint(6, 22)
                    minute = random.randint(0, 59)
                    movement_time = f"{hour:02d}:{minute:02d}:00"
                    
                    # Random organizations
                    org_from = random.choice(organizations).name
                    org_to = random.choice(organizations).name
                    
                    # Random vehicle
                    vehicle_plate = random.choice(vehicle_plates)
                    
                    # Duration (30 minutes to 8 hours)
                    duration = random.randint(30, 480)
                    
                    # Movement type
                    if org_from == org_to:
                        movement_type = 'parking'
                    else:
                        movement_type = 'transit'
                    
                    # Temporal features
                    day_of_week = date.weekday()
                    is_weekend = day_of_week >= 5
                    is_business_hours = 9 <= hour <= 17
                    is_peak_hours = hour in [8, 9, 17, 18, 19]
                    
                    # Season
                    month = date.month
                    if month in [12, 1, 2]:
                        season = 'winter'
                    elif month in [3, 4, 5]:
                        season = 'spring'
                    elif month in [6, 7, 8]:
                        season = 'summer'
                    else:
                        season = 'autumn'
                    
                    # Insert movement
                    cursor.execute("""
                        INSERT INTO movement_analytics (
                            vehicle_plate, organization_from, organization_to,
                            movement_date, movement_time, duration_minutes, movement_type,
                            hour_of_day, day_of_week, is_weekend, is_business_hours,
                            is_peak_hours, season, is_inter_org_movement
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        vehicle_plate, org_from, org_to, date, movement_time,
                        duration, movement_type, hour, day_of_week, is_weekend,
                        is_business_hours, is_peak_hours, season, org_from != org_to
                    ])
                    
                    movements_created += 1
        
        print(f"[SUCCESS] Generated {movements_created:,} sample movements")
        return movements_created
    
    def calculate_advanced_features(self):
        """Calculate advanced analytics features"""
        print("Calculating advanced features...")
        
        with connection.cursor() as cursor:
            # Calculate vehicle activity scores
            print("   Calculating vehicle activity scores...")
            cursor.execute("""
                UPDATE movement_analytics SET vehicle_activity_score = (
                    SELECT COUNT(*) FROM movement_analytics m2 
                    WHERE m2.vehicle_plate = movement_analytics.vehicle_plate
                ) / 10  -- Normalize to 0-10 scale
            """)
            
            # Calculate organization traffic scores
            print("   Calculating organization traffic scores...")
            cursor.execute("""
                UPDATE movement_analytics SET organization_traffic_score = (
                    SELECT COUNT(*) FROM movement_analytics m2 
                    WHERE m2.organization_from = movement_analytics.organization_from
                       OR m2.organization_to = movement_analytics.organization_from
                ) / 20  -- Normalize to 0-10 scale
            """)
            
            # Calculate route popularity
            print("   Calculating route popularity...")
            cursor.execute("""
                UPDATE movement_analytics SET route_popularity = (
                    SELECT COUNT(*) FROM movement_analytics m2 
                    WHERE m2.organization_from = movement_analytics.organization_from
                      AND m2.organization_to = movement_analytics.organization_to
                )
            """)
            
            # Calculate movement frequency patterns
            print("   Calculating movement frequency patterns...")
            cursor.execute("""
                UPDATE movement_analytics SET movement_frequency = 
                CASE 
                    WHEN vehicle_activity_score >= 8 THEN 'very_frequent'
                    WHEN vehicle_activity_score >= 5 THEN 'frequent'
                    WHEN vehicle_activity_score >= 2 THEN 'moderate'
                    ELSE 'rare'
                END
            """)
        
        print("[SUCCESS] Advanced features calculated")
    
    def generate_analytics_summary(self):
        """Generate comprehensive analytics summary"""
        print("\nGenerating Analytics Summary...")
        
        with connection.cursor() as cursor:
            # Basic statistics
            cursor.execute("SELECT COUNT(*) FROM movement_analytics")
            total_movements = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT vehicle_plate) FROM movement_analytics")
            unique_vehicles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT organization_from) FROM movement_analytics")
            unique_organizations = cursor.fetchone()[0]
            
            # Temporal insights
            cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_weekend = true")
            weekend_movements = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_peak_hours = true")
            peak_hour_movements = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_business_hours = true")
            business_hour_movements = cursor.fetchone()[0]
            
            # Movement patterns
            cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_inter_org_movement = true")
            inter_org_movements = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE movement_type = 'parking'")
            parking_movements = cursor.fetchone()[0]
            
            # Top organizations by traffic
            cursor.execute("""
                SELECT organization_from, COUNT(*) as traffic_count 
                FROM movement_analytics 
                GROUP BY organization_from 
                ORDER BY traffic_count DESC 
                LIMIT 5
            """)
            top_orgs = cursor.fetchall()
            
            # Top vehicles by activity
            cursor.execute("""
                SELECT vehicle_plate, COUNT(*) as activity_count 
                FROM movement_analytics 
                GROUP BY vehicle_plate 
                ORDER BY activity_count DESC 
                LIMIT 5
            """)
            top_vehicles = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print(f"VEHICLE INTELLIGENCE ANALYTICS SUMMARY")
        print(f"{'='*60}")
        print(f"Total Movements: {total_movements:,}")
        print(f"Unique Vehicles: {unique_vehicles:,}")
        print(f"Unique Organizations: {unique_organizations:,}")
        
        print(f"\nTemporal Patterns:")
        print(f"  Weekend Movements: {weekend_movements:,} ({weekend_movements/total_movements*100:.1f}%)")
        print(f"  Peak Hour Movements: {peak_hour_movements:,} ({peak_hour_movements/total_movements*100:.1f}%)")
        print(f"  Business Hour Movements: {business_hour_movements:,} ({business_hour_movements/total_movements*100:.1f}%)")
        
        print(f"\nMovement Patterns:")
        print(f"  Inter-Organization Movements: {inter_org_movements:,} ({inter_org_movements/total_movements*100:.1f}%)")
        print(f"  Parking Movements: {parking_movements:,} ({parking_movements/total_movements*100:.1f}%)")
        
        print(f"\nTop Organizations by Traffic:")
        for i, (org, count) in enumerate(top_orgs, 1):
            print(f"  {i}. {org}: {count:,} movements")
        
        print(f"\nTop Vehicles by Activity:")
        for i, (vehicle, count) in enumerate(top_vehicles, 1):
            print(f"  {i}. {vehicle}: {count:,} movements")
        
        return {
            'total_movements': total_movements,
            'unique_vehicles': unique_vehicles,
            'weekend_percentage': weekend_movements/total_movements*100 if total_movements > 0 else 0,
            'peak_hour_percentage': peak_hour_movements/total_movements*100 if total_movements > 0 else 0,
            'inter_org_percentage': inter_org_movements/total_movements*100 if total_movements > 0 else 0
        }
    
    def run_complete_setup(self):
        """Run the complete vehicle intelligence setup"""
        print("Starting Vehicle Intelligence System Setup")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Create analytics table
            self.create_movement_analytics_table()
            
            # Step 2: Generate sample data
            movements_count = self.generate_sample_movement_data()
            
            # Step 3: Calculate features
            self.calculate_advanced_features()
            
            # Step 4: Generate summary
            summary = self.generate_analytics_summary()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n[SUCCESS] Vehicle Intelligence System Setup Complete!")
            print(f"  Total Time: {duration:.2f} seconds")
            print(f"  Enhanced {summary['total_movements']:,} movement records")
            print(f"  System ready for advanced analytics and AI insights!")
            
            return summary
            
        except Exception as e:
            print(f"[ERROR] Error in setup: {e}")
            raise

def main():
    """Main execution function"""
    intelligence = SimpleVehicleIntelligence()
    summary = intelligence.run_complete_setup()
    
    print(f"\n[SUCCESS] Setup completed successfully!")
    print(f"Your vehicle intelligence system is now ready with:")
    print(f"  • {summary['total_movements']:,} movement records")
    print(f"  • {summary['unique_vehicles']:,} vehicles tracked")
    print(f"  • Advanced temporal and behavioral analytics")
    print(f"  • Ready for dashboard visualizations and AI insights")

if __name__ == "__main__":
    main()