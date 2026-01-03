#!/usr/bin/env python
"""
Real Data Feature Engineering
Uses actual combined_dataset from PostgreSQL to create vehicle movement analytics
"""

import os
import sys
import django
from datetime import datetime
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

class RealDataFeatureEngineer:
    """Feature engineering using real combined_dataset"""
    
    def __init__(self):
        self.total_records = 0
        
    def create_enhanced_analytics_table(self):
        """Create enhanced analytics table from real data"""
        print("Creating enhanced analytics from real data...")
        
        with connection.cursor() as cursor:
            # Drop existing table if exists
            cursor.execute("DROP TABLE IF EXISTS real_movement_analytics")
            
            # Create enhanced table with features
            cursor.execute("""
                CREATE TABLE real_movement_analytics AS
                SELECT 
                    "Plate Number" as plate_number,
                    "Entry Time (Kenyan Time)"::timestamp as entry_time,
                    "Exit Time (Kenyan Time)"::timestamp as exit_time,
                    "Vehicle Type" as vehicle_type,
                    "Plate Color" as plate_color,
                    "Vehicle Brand" as vehicle_brand,
                    "Amount Paid" as amount_paid,
                    "Payment Time (Kenyan Time)"::timestamp as payment_time,
                    "Payment Method" as payment_method,
                    "Organization" as organization,
                    
                    -- Calculate duration
                    EXTRACT(EPOCH FROM ("Exit Time (Kenyan Time)"::timestamp - "Entry Time (Kenyan Time)"::timestamp))/60 as duration_minutes,
                    
                    -- Temporal features
                    EXTRACT(HOUR FROM "Entry Time (Kenyan Time)"::timestamp) as entry_hour,
                    EXTRACT(DOW FROM "Entry Time (Kenyan Time)"::timestamp) as day_of_week,
                    EXTRACT(MONTH FROM "Entry Time (Kenyan Time)"::timestamp) as entry_month,
                    EXTRACT(QUARTER FROM "Entry Time (Kenyan Time)"::timestamp) as entry_quarter,
                    
                    -- Boolean features
                    CASE WHEN EXTRACT(DOW FROM "Entry Time (Kenyan Time)"::timestamp) IN (0,6) THEN true ELSE false END as is_weekend,
                    CASE WHEN EXTRACT(HOUR FROM "Entry Time (Kenyan Time)"::timestamp) BETWEEN 9 AND 17 THEN true ELSE false END as is_business_hours,
                    CASE WHEN EXTRACT(HOUR FROM "Entry Time (Kenyan Time)"::timestamp) IN (8,9,17,18,19) THEN true ELSE false END as is_peak_hours,
                    
                    -- Season
                    CASE 
                        WHEN EXTRACT(MONTH FROM "Entry Time (Kenyan Time)"::timestamp) IN (12,1,2) THEN 'summer'
                        WHEN EXTRACT(MONTH FROM "Entry Time (Kenyan Time)"::timestamp) IN (3,4,5) THEN 'autumn'
                        WHEN EXTRACT(MONTH FROM "Entry Time (Kenyan Time)"::timestamp) IN (6,7,8) THEN 'winter'
                        ELSE 'spring'
                    END as season,
                    
                    -- Duration categories
                    CASE 
                        WHEN EXTRACT(EPOCH FROM ("Exit Time (Kenyan Time)"::timestamp - "Entry Time (Kenyan Time)"::timestamp))/60 <= 30 THEN 'short'
                        WHEN EXTRACT(EPOCH FROM ("Exit Time (Kenyan Time)"::timestamp - "Entry Time (Kenyan Time)"::timestamp))/60 <= 120 THEN 'medium'
                        WHEN EXTRACT(EPOCH FROM ("Exit Time (Kenyan Time)"::timestamp - "Entry Time (Kenyan Time)"::timestamp))/60 <= 480 THEN 'long'
                        ELSE 'extended'
                    END as duration_category,
                    
                    -- Revenue categories
                    CASE 
                        WHEN "Amount Paid" >= 500 THEN 'high'
                        WHEN "Amount Paid" >= 200 THEN 'medium'
                        WHEN "Amount Paid" >= 50 THEN 'low'
                        ELSE 'minimal'
                    END as revenue_category
                    
                FROM combined_dataset
                WHERE "Entry Time (Kenyan Time)" IS NOT NULL
                  AND "Exit Time (Kenyan Time)" IS NOT NULL
            """)
            
            # Add primary key and indexes
            cursor.execute("ALTER TABLE real_movement_analytics ADD COLUMN id SERIAL PRIMARY KEY")
            cursor.execute("CREATE INDEX idx_real_plate ON real_movement_analytics(plate_number)")
            cursor.execute("CREATE INDEX idx_real_org ON real_movement_analytics(organization)")
            cursor.execute("CREATE INDEX idx_real_entry_time ON real_movement_analytics(entry_time)")
            cursor.execute("CREATE INDEX idx_real_weekend ON real_movement_analytics(is_weekend)")
            cursor.execute("CREATE INDEX idx_real_peak ON real_movement_analytics(is_peak_hours)")
            
            # Get count
            cursor.execute("SELECT COUNT(*) FROM real_movement_analytics")
            self.total_records = cursor.fetchone()[0]
            
        print(f"[SUCCESS] Created analytics table with {self.total_records:,} records")
    
    def add_vehicle_behavior_features(self):
        """Add vehicle-specific behavioral features"""
        print("Adding vehicle behavior features...")
        
        with connection.cursor() as cursor:
            # Add new columns
            cursor.execute("""
                ALTER TABLE real_movement_analytics 
                ADD COLUMN IF NOT EXISTS vehicle_visit_count INTEGER,
                ADD COLUMN IF NOT EXISTS vehicle_total_revenue DECIMAL(12,2),
                ADD COLUMN IF NOT EXISTS vehicle_avg_duration DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS vehicle_usage_type VARCHAR(20),
                ADD COLUMN IF NOT EXISTS vehicle_revenue_tier VARCHAR(20)
            """)
            
            # Calculate vehicle statistics
            cursor.execute("""
                WITH vehicle_stats AS (
                    SELECT 
                        plate_number,
                        COUNT(*) as visit_count,
                        SUM(amount_paid) as total_revenue,
                        AVG(duration_minutes) as avg_duration
                    FROM real_movement_analytics
                    GROUP BY plate_number
                )
                UPDATE real_movement_analytics 
                SET 
                    vehicle_visit_count = vs.visit_count,
                    vehicle_total_revenue = vs.total_revenue,
                    vehicle_avg_duration = vs.avg_duration,
                    vehicle_usage_type = CASE 
                        WHEN vs.visit_count >= 50 THEN 'frequent'
                        WHEN vs.visit_count >= 20 THEN 'regular'
                        WHEN vs.visit_count >= 5 THEN 'occasional'
                        ELSE 'rare'
                    END,
                    vehicle_revenue_tier = CASE 
                        WHEN vs.total_revenue >= 10000 THEN 'high'
                        WHEN vs.total_revenue >= 5000 THEN 'medium'
                        WHEN vs.total_revenue >= 1000 THEN 'low'
                        ELSE 'minimal'
                    END
                FROM vehicle_stats vs
                WHERE real_movement_analytics.plate_number = vs.plate_number
            """)
        
        print("[SUCCESS] Added vehicle behavior features")
    
    def add_organization_features(self):
        """Add organization-specific features"""
        print("Adding organization features...")
        
        with connection.cursor() as cursor:
            # Add new columns
            cursor.execute("""
                ALTER TABLE real_movement_analytics 
                ADD COLUMN IF NOT EXISTS org_total_vehicles INTEGER,
                ADD COLUMN IF NOT EXISTS org_total_revenue DECIMAL(12,2),
                ADD COLUMN IF NOT EXISTS org_avg_duration DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS org_size_category VARCHAR(20),
                ADD COLUMN IF NOT EXISTS org_performance_tier VARCHAR(20)
            """)
            
            # Calculate organization statistics
            cursor.execute("""
                WITH org_stats AS (
                    SELECT 
                        organization,
                        COUNT(DISTINCT plate_number) as total_vehicles,
                        SUM(amount_paid) as total_revenue,
                        AVG(duration_minutes) as avg_duration
                    FROM real_movement_analytics
                    GROUP BY organization
                )
                UPDATE real_movement_analytics 
                SET 
                    org_total_vehicles = os.total_vehicles,
                    org_total_revenue = os.total_revenue,
                    org_avg_duration = os.avg_duration,
                    org_size_category = CASE 
                        WHEN os.total_vehicles >= 1000 THEN 'large'
                        WHEN os.total_vehicles >= 500 THEN 'medium'
                        WHEN os.total_vehicles >= 100 THEN 'small'
                        ELSE 'micro'
                    END,
                    org_performance_tier = CASE 
                        WHEN os.total_revenue >= 500000 THEN 'excellent'
                        WHEN os.total_revenue >= 250000 THEN 'good'
                        WHEN os.total_revenue >= 100000 THEN 'average'
                        ELSE 'poor'
                    END
                FROM org_stats os
                WHERE real_movement_analytics.organization = os.organization
            """)
        
        print("[SUCCESS] Added organization features")
    
    def generate_analytics_summary(self):
        """Generate comprehensive analytics summary"""
        print("\nGenerating Real Data Analytics Summary...")
        
        with connection.cursor() as cursor:
            # Basic statistics
            cursor.execute("SELECT COUNT(*) FROM real_movement_analytics")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT plate_number) FROM real_movement_analytics")
            unique_vehicles = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT organization) FROM real_movement_analytics")
            unique_orgs = cursor.fetchone()[0]
            
            # Temporal patterns
            cursor.execute("SELECT COUNT(*) FROM real_movement_analytics WHERE is_weekend = true")
            weekend_visits = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM real_movement_analytics WHERE is_peak_hours = true")
            peak_visits = cursor.fetchone()[0]
            
            # Duration patterns
            cursor.execute("SELECT duration_category, COUNT(*) FROM real_movement_analytics GROUP BY duration_category ORDER BY COUNT(*) DESC")
            duration_stats = cursor.fetchall()
            
            # Revenue patterns
            cursor.execute("SELECT revenue_category, COUNT(*) FROM real_movement_analytics GROUP BY revenue_category ORDER BY COUNT(*) DESC")
            revenue_stats = cursor.fetchall()
            
            # Top organizations
            cursor.execute("SELECT organization, COUNT(*) as visits FROM real_movement_analytics GROUP BY organization ORDER BY visits DESC LIMIT 5")
            top_orgs = cursor.fetchall()
            
            # Top vehicles
            cursor.execute("SELECT plate_number, COUNT(*) as visits FROM real_movement_analytics GROUP BY plate_number ORDER BY visits DESC LIMIT 5")
            top_vehicles = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print(f"REAL DATA VEHICLE INTELLIGENCE SUMMARY")
        print(f"{'='*60}")
        print(f"Total Records: {total_records:,}")
        print(f"Unique Vehicles: {unique_vehicles:,}")
        print(f"Unique Organizations: {unique_orgs:,}")
        
        print(f"\nTemporal Patterns:")
        print(f"  Weekend Visits: {weekend_visits:,} ({weekend_visits/total_records*100:.1f}%)")
        print(f"  Peak Hour Visits: {peak_visits:,} ({peak_visits/total_records*100:.1f}%)")
        
        print(f"\nDuration Distribution:")
        for category, count in duration_stats:
            print(f"  {category.title()}: {count:,} ({count/total_records*100:.1f}%)")
        
        print(f"\nRevenue Distribution:")
        for category, count in revenue_stats:
            print(f"  {category.title()}: {count:,} ({count/total_records*100:.1f}%)")
        
        print(f"\nTop Organizations:")
        for i, (org, visits) in enumerate(top_orgs, 1):
            print(f"  {i}. {org}: {visits:,} visits")
        
        print(f"\nTop Vehicles:")
        for i, (vehicle, visits) in enumerate(top_vehicles, 1):
            print(f"  {i}. {vehicle}: {visits:,} visits")
        
        return {
            'total_records': total_records,
            'unique_vehicles': unique_vehicles,
            'weekend_percentage': weekend_visits/total_records*100,
            'peak_percentage': peak_visits/total_records*100
        }
    
    def run_complete_pipeline(self):
        """Run complete feature engineering pipeline"""
        print("Starting Real Data Feature Engineering Pipeline")
        print("="*60)
        
        start_time = datetime.now()
        
        try:
            self.create_enhanced_analytics_table()
            self.add_vehicle_behavior_features()
            self.add_organization_features()
            summary = self.generate_analytics_summary()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n[SUCCESS] Real Data Feature Engineering Complete!")
            print(f"  Processing Time: {duration:.2f} seconds")
            print(f"  Enhanced {summary['total_records']:,} real records")
            print(f"  Ready for advanced analytics and AI insights!")
            
            return summary
            
        except Exception as e:
            print(f"[ERROR] Pipeline failed: {e}")
            raise

def main():
    """Main execution"""
    engineer = RealDataFeatureEngineer()
    summary = engineer.run_complete_pipeline()
    
    print(f"\n[SUCCESS] Real data feature engineering completed!")
    print(f"Your system now has {summary['total_records']:,} enhanced real records ready for analytics.")

if __name__ == "__main__":
    main()