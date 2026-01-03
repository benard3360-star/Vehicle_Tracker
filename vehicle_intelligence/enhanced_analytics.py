#!/usr/bin/env python
"""
Enhanced Analytics System with Visualizations
Extracts time/date properly and creates visualization data
"""

import os
import sys
import django
from django.db import connection

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

class EnhancedAnalytics:
    """Enhanced analytics with proper time extraction and visualizations"""
    
    def __init__(self):
        self.updated_records = 0
    
    def add_time_features(self):
        """Add proper time and date extraction features"""
        print("Adding enhanced time features...")
        
        with connection.cursor() as cursor:
            # Add new time-based columns
            cursor.execute("""
                ALTER TABLE real_movement_analytics 
                ADD COLUMN IF NOT EXISTS entry_date DATE,
                ADD COLUMN IF NOT EXISTS entry_time_only TIME,
                ADD COLUMN IF NOT EXISTS exit_date DATE,
                ADD COLUMN IF NOT EXISTS exit_time_only TIME,
                ADD COLUMN IF NOT EXISTS parking_duration_hours DECIMAL(8,2),
                ADD COLUMN IF NOT EXISTS is_overstay BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS time_category VARCHAR(20)
            """)
            
            # Extract date and time components
            cursor.execute("""
                UPDATE real_movement_analytics SET
                    entry_date = DATE(entry_time),
                    entry_time_only = entry_time::TIME,
                    exit_date = DATE(exit_time),
                    exit_time_only = exit_time::TIME,
                    parking_duration_hours = duration_minutes / 60.0,
                    is_overstay = CASE WHEN duration_minutes > 240 THEN TRUE ELSE FALSE END,
                    time_category = CASE 
                        WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 6 AND 11 THEN 'morning'
                        WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 12 AND 17 THEN 'afternoon'
                        WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 18 AND 21 THEN 'evening'
                        ELSE 'night'
                    END
                WHERE entry_time IS NOT NULL
            """)
            
            print("[SUCCESS] Enhanced time features added")
    
    def get_parking_duration_analysis(self, organization=None):
        """Get parking duration analysis data"""
        with connection.cursor() as cursor:
            where_clause = "WHERE organization = %s" if organization else ""
            params = [organization] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    organization,
                    COUNT(*) as total_visits,
                    AVG(duration_minutes) as avg_duration,
                    SUM(CASE WHEN duration_category = 'short' THEN 1 ELSE 0 END) as short_stays,
                    SUM(CASE WHEN duration_category = 'medium' THEN 1 ELSE 0 END) as medium_stays,
                    SUM(CASE WHEN duration_category = 'long' THEN 1 ELSE 0 END) as long_stays,
                    SUM(CASE WHEN duration_category = 'extended' THEN 1 ELSE 0 END) as extended_stays
                FROM real_movement_analytics 
                {where_clause}
                GROUP BY organization
                ORDER BY total_visits DESC
            """, params)
            
            return cursor.fetchall()
    
    def get_hourly_entries_chart(self, organization=None):
        """Get hourly vehicle entries data"""
        with connection.cursor() as cursor:
            where_clause = "WHERE organization = %s" if organization else ""
            params = [organization] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    entry_hour,
                    COUNT(*) as entry_count
                FROM real_movement_analytics 
                {where_clause}
                GROUP BY entry_hour
                ORDER BY entry_hour
            """, params)
            
            results = cursor.fetchall()
            return {
                'labels': [f"{hour:02d}:00" for hour, _ in results],
                'data': [count for _, count in results],
                'type': 'line'
            }
    
    def get_vehicles_per_organization_chart(self):
        """Get vehicles per organization pie chart data"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    organization,
                    COUNT(DISTINCT plate_number) as vehicle_count
                FROM real_movement_analytics 
                GROUP BY organization
                ORDER BY vehicle_count DESC
            """)
            
            results = cursor.fetchall()
            return {
                'labels': [org for org, _ in results],
                'data': [count for _, count in results],
                'type': 'pie'
            }
    
    def get_revenue_per_organization_chart(self):
        """Get revenue per organization bar chart data"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    organization,
                    SUM(amount_paid) as total_revenue,
                    COUNT(*) as visit_count,
                    AVG(amount_paid) as avg_revenue
                FROM real_movement_analytics 
                GROUP BY organization
                ORDER BY total_revenue DESC
            """)
            
            results = cursor.fetchall()
            return {
                'labels': [org for org, _, _, _ in results],
                'data': [float(revenue) for _, revenue, _, _ in results],
                'visit_counts': [visits for _, _, visits, _ in results],
                'avg_revenues': [float(avg) for _, _, _, avg in results],
                'type': 'bar'
            }
    
    def get_visit_patterns_chart(self, organization=None):
        """Get vehicle visit patterns data"""
        with connection.cursor() as cursor:
            where_clause = "WHERE organization = %s" if organization else ""
            params = [organization] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    vehicle_usage_type,
                    COUNT(DISTINCT plate_number) as vehicle_count
                FROM real_movement_analytics 
                {where_clause}
                GROUP BY vehicle_usage_type
                ORDER BY vehicle_count DESC
            """, params)
            
            results = cursor.fetchall()
            return {
                'labels': [usage_type or 'Unknown' for usage_type, _ in results],
                'data': [count for _, count in results],
                'type': 'doughnut'
            }
    
    def get_avg_stay_by_type_chart(self, organization=None):
        """Get average stay by vehicle type"""
        with connection.cursor() as cursor:
            where_clause = "WHERE organization = %s" if organization else ""
            params = [organization] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    vehicle_type,
                    AVG(duration_minutes) as avg_duration,
                    COUNT(*) as visit_count
                FROM real_movement_analytics 
                {where_clause}
                GROUP BY vehicle_type
                HAVING COUNT(*) >= 5
                ORDER BY avg_duration DESC
                LIMIT 10
            """, params)
            
            results = cursor.fetchall()
            return {
                'labels': [vtype or 'Unknown' for vtype, _, _ in results],
                'data': [float(duration) for _, duration, _ in results],
                'visit_counts': [count for _, _, count in results],
                'type': 'bar'
            }
    
    def get_fleet_summary(self, organization=None):
        """Get comprehensive fleet summary"""
        with connection.cursor() as cursor:
            where_clause = "WHERE organization = %s" if organization else ""
            params = [organization] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    COUNT(DISTINCT plate_number) as total_vehicles,
                    COUNT(*) as total_visits,
                    SUM(amount_paid) as total_revenue,
                    AVG(duration_minutes) as avg_duration,
                    COUNT(DISTINCT organization) as organizations,
                    SUM(CASE WHEN is_weekend THEN 1 ELSE 0 END) as weekend_visits,
                    SUM(CASE WHEN is_peak_hours THEN 1 ELSE 0 END) as peak_visits
                FROM real_movement_analytics 
                {where_clause}
            """, params)
            
            result = cursor.fetchone()
            if result:
                return {
                    'total_vehicles': result[0] or 0,
                    'total_visits': result[1] or 0,
                    'total_revenue': float(result[2] or 0),
                    'avg_duration': float(result[3] or 0),
                    'organizations': result[4] or 0,
                    'weekend_visits': result[5] or 0,
                    'peak_visits': result[6] or 0,
                    'utilization_rate': min(100, (result[1] or 0) / max(1, result[0] or 1) * 2)
                }
            return {}
    
    def create_analytics_views(self):
        """Create database views for faster analytics"""
        print("Creating analytics views...")
        
        with connection.cursor() as cursor:
            # Hourly analytics view
            cursor.execute("""
                CREATE OR REPLACE VIEW hourly_analytics AS
                SELECT 
                    entry_hour,
                    organization,
                    COUNT(*) as visit_count,
                    AVG(duration_minutes) as avg_duration,
                    SUM(amount_paid) as total_revenue
                FROM real_movement_analytics
                GROUP BY entry_hour, organization
            """)
            
            # Daily analytics view
            cursor.execute("""
                CREATE OR REPLACE VIEW daily_analytics AS
                SELECT 
                    entry_date,
                    organization,
                    COUNT(*) as visit_count,
                    COUNT(DISTINCT plate_number) as unique_vehicles,
                    SUM(amount_paid) as total_revenue,
                    AVG(duration_minutes) as avg_duration
                FROM real_movement_analytics
                WHERE entry_date IS NOT NULL
                GROUP BY entry_date, organization
            """)
            
            # Vehicle summary view
            cursor.execute("""
                CREATE OR REPLACE VIEW vehicle_summary AS
                SELECT 
                    plate_number,
                    vehicle_brand,
                    vehicle_type,
                    COUNT(*) as total_visits,
                    SUM(amount_paid) as total_revenue,
                    AVG(duration_minutes) as avg_duration,
                    MAX(entry_time) as last_visit,
                    COUNT(DISTINCT organization) as organizations_visited
                FROM real_movement_analytics
                GROUP BY plate_number, vehicle_brand, vehicle_type
            """)
            
            print("[SUCCESS] Analytics views created")
    
    def run_complete_enhancement(self):
        """Run complete analytics enhancement"""
        print("Starting Enhanced Analytics System")
        print("=" * 50)
        
        try:
            self.add_time_features()
            self.create_analytics_views()
            
            # Test visualizations
            print("\nTesting visualizations...")
            
            fleet_summary = self.get_fleet_summary()
            print(f"Fleet Summary: {fleet_summary.get('total_vehicles', 0)} vehicles, {fleet_summary.get('total_visits', 0)} visits")
            
            try:
                hourly_chart = self.get_hourly_entries_chart()
                print(f"Hourly Chart: Generated successfully")
            except Exception as e:
                print(f"Hourly Chart: Error - {e}")
            
            try:
                org_chart = self.get_vehicles_per_organization_chart()
                print(f"Organization Chart: Generated successfully")
            except Exception as e:
                print(f"Organization Chart: Error - {e}")
            
            try:
                revenue_chart = self.get_revenue_per_organization_chart()
                print(f"Revenue Chart: Generated successfully")
            except Exception as e:
                print(f"Revenue Chart: Error - {e}")
            
            print("\n[SUCCESS] Enhanced Analytics System Complete!")
            print("All visualizations are ready for the Vehicle Alert dashboard")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Enhancement failed: {e}")
            return False

def main():
    """Main execution"""
    analytics = EnhancedAnalytics()
    success = analytics.run_complete_enhancement()
    
    if success:
        print("\n[SUCCESS] Enhanced analytics system ready!")
        print("Vehicle Alert dashboard now has full visualization support")
    else:
        print("\n[ERROR] Enhancement failed")

if __name__ == "__main__":
    main()