from django.db import connection
import json

class VehicleAlertAnalytics:
    """Analytics functions for Vehicle Alert dashboard"""
    
    @staticmethod
    def get_vehicle_analytics_charts(plate_number):
        """Get all visualization charts for a specific vehicle"""
        
        with connection.cursor() as cursor:
            # 1. Parking Duration Analysis for this vehicle
            cursor.execute("""
                SELECT 
                    duration_category,
                    COUNT(*) as count
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY duration_category
                ORDER BY 
                    CASE duration_category
                        WHEN 'short' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'long' THEN 3
                        WHEN 'extended' THEN 4
                        ELSE 5
                    END
            """, [plate_number])
            
            duration_data = cursor.fetchall()
            parking_duration_chart = {
                'labels': [cat.title() if cat else 'Unknown' for cat, _ in duration_data],
                'data': [count for _, count in duration_data],
                'type': 'doughnut'
            }
            
            # 2. Hourly Visit Pattern for this vehicle
            cursor.execute("""
                SELECT 
                    entry_hour,
                    COUNT(*) as visit_count
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY entry_hour
                ORDER BY entry_hour
            """, [plate_number])
            
            hourly_data = cursor.fetchall()
            hourly_chart = {
                'labels': [f"{hour:02d}:00" for hour, _ in hourly_data],
                'data': [count for _, count in hourly_data],
                'type': 'line'
            }
            
            # 3. Organization Visits for this vehicle
            cursor.execute("""
                SELECT 
                    organization,
                    COUNT(*) as visit_count,
                    SUM(amount_paid) as total_revenue
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY organization
                ORDER BY visit_count DESC
            """, [plate_number])
            
            org_data = cursor.fetchall()
            organization_chart = {
                'labels': [org for org, _, _ in org_data],
                'data': [count for _, count, _ in org_data],
                'revenue_data': [float(revenue) for _, _, revenue in org_data],
                'type': 'bar'
            }
            
            # 4. Revenue Analysis for this vehicle
            cursor.execute("""
                SELECT 
                    revenue_category,
                    COUNT(*) as count,
                    SUM(amount_paid) as total_amount
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY revenue_category
                ORDER BY 
                    CASE revenue_category
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        WHEN 'minimal' THEN 4
                        ELSE 5
                    END
            """, [plate_number])
            
            revenue_data = cursor.fetchall()
            revenue_chart = {
                'labels': [cat.title() if cat else 'Unknown' for cat, _, _ in revenue_data],
                'data': [float(amount) for _, _, amount in revenue_data],
                'visit_counts': [count for _, count, _ in revenue_data],
                'type': 'pie'
            }
            
            # 5. Visit Patterns (Time of Day)
            cursor.execute("""
                SELECT 
                    time_category,
                    COUNT(*) as count
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY time_category
                ORDER BY 
                    CASE time_category
                        WHEN 'morning' THEN 1
                        WHEN 'afternoon' THEN 2
                        WHEN 'evening' THEN 3
                        WHEN 'night' THEN 4
                        ELSE 5
                    END
            """, [plate_number])
            
            time_data = cursor.fetchall()
            time_pattern_chart = {
                'labels': [cat.title() if cat else 'Unknown' for cat, _ in time_data],
                'data': [count for _, count in time_data],
                'type': 'radar'
            }
            
            # 6. Monthly Trend (if enough data)
            cursor.execute("""
                SELECT 
                    entry_month,
                    COUNT(*) as visit_count,
                    AVG(duration_minutes) as avg_duration
                FROM real_movement_analytics 
                WHERE plate_number = %s
                GROUP BY entry_month
                ORDER BY entry_month
            """, [plate_number])
            
            monthly_data = cursor.fetchall()
            monthly_chart = {
                'labels': [f"Month {month}" for month, _, _ in monthly_data],
                'visit_data': [count for _, count, _ in monthly_data],
                'duration_data': [float(duration) for _, _, duration in monthly_data],
                'type': 'line'
            }
            
            return {
                'parking_duration': parking_duration_chart,
                'hourly_pattern': hourly_chart,
                'organization_visits': organization_chart,
                'revenue_analysis': revenue_chart,
                'time_patterns': time_pattern_chart,
                'monthly_trend': monthly_chart
            }
    
    @staticmethod
    def get_vehicle_comparison_data(plate_number):
        """Get comparison data for vehicle vs fleet average"""
        
        with connection.cursor() as cursor:
            # Vehicle stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as visits,
                    AVG(duration_minutes) as avg_duration,
                    SUM(amount_paid) as total_revenue,
                    COUNT(DISTINCT organization) as orgs_visited
                FROM real_movement_analytics 
                WHERE plate_number = %s
            """, [plate_number])
            
            vehicle_stats = cursor.fetchone()
            
            # Fleet averages
            cursor.execute("""
                SELECT 
                    AVG(visit_count) as avg_visits,
                    AVG(avg_duration) as fleet_avg_duration,
                    AVG(total_revenue) as avg_revenue,
                    AVG(orgs_count) as avg_orgs
                FROM (
                    SELECT 
                        plate_number,
                        COUNT(*) as visit_count,
                        AVG(duration_minutes) as avg_duration,
                        SUM(amount_paid) as total_revenue,
                        COUNT(DISTINCT organization) as orgs_count
                    FROM real_movement_analytics 
                    GROUP BY plate_number
                ) fleet_stats
            """)
            
            fleet_stats = cursor.fetchone()
            
            if vehicle_stats and fleet_stats:
                return {
                    'vehicle': {
                        'visits': vehicle_stats[0],
                        'avg_duration': float(vehicle_stats[1] or 0),
                        'total_revenue': float(vehicle_stats[2] or 0),
                        'orgs_visited': vehicle_stats[3]
                    },
                    'fleet_average': {
                        'visits': float(fleet_stats[0] or 0),
                        'avg_duration': float(fleet_stats[1] or 0),
                        'total_revenue': float(fleet_stats[2] or 0),
                        'orgs_visited': float(fleet_stats[3] or 0)
                    }
                }
            
            return None