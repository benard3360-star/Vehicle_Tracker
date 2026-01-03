from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Query vehicle movement analytics data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--report',
            type=str,
            choices=['summary', 'temporal', 'vehicles', 'organizations', 'routes'],
            default='summary',
            help='Type of report to generate',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Limit number of results',
        )
    
    def handle(self, *args, **options):
        report_type = options['report']
        limit = options['limit']
        
        self.stdout.write(
            self.style.SUCCESS(f'Vehicle Movement Analytics - {report_type.title()} Report')
        )
        self.stdout.write('=' * 60)
        
        with connection.cursor() as cursor:
            if report_type == 'summary':
                self.generate_summary_report(cursor)
            elif report_type == 'temporal':
                self.generate_temporal_report(cursor, limit)
            elif report_type == 'vehicles':
                self.generate_vehicle_report(cursor, limit)
            elif report_type == 'organizations':
                self.generate_organization_report(cursor, limit)
            elif report_type == 'routes':
                self.generate_route_report(cursor, limit)
    
    def generate_summary_report(self, cursor):
        """Generate overall summary statistics"""
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM movement_analytics")
        total_movements = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT vehicle_plate) FROM movement_analytics")
        unique_vehicles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT organization_from) FROM movement_analytics")
        unique_organizations = cursor.fetchone()[0]
        
        # Temporal patterns
        cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_weekend = true")
        weekend_movements = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_peak_hours = true")
        peak_movements = cursor.fetchone()[0]
        
        # Movement types
        cursor.execute("SELECT COUNT(*) FROM movement_analytics WHERE is_inter_org_movement = true")
        inter_org = cursor.fetchone()[0]
        
        self.stdout.write(f"Total Movements: {total_movements:,}")
        self.stdout.write(f"Unique Vehicles: {unique_vehicles:,}")
        self.stdout.write(f"Unique Organizations: {unique_organizations:,}")
        self.stdout.write(f"Weekend Movements: {weekend_movements:,} ({weekend_movements/total_movements*100:.1f}%)")
        self.stdout.write(f"Peak Hour Movements: {peak_movements:,} ({peak_movements/total_movements*100:.1f}%)")
        self.stdout.write(f"Inter-Org Movements: {inter_org:,} ({inter_org/total_movements*100:.1f}%)")
    
    def generate_temporal_report(self, cursor, limit):
        """Generate temporal analysis report"""
        self.stdout.write("Hourly Movement Distribution:")
        cursor.execute("""
            SELECT hour_of_day, COUNT(*) as movement_count
            FROM movement_analytics 
            GROUP BY hour_of_day 
            ORDER BY hour_of_day
        """)
        
        for hour, count in cursor.fetchall():
            bar = '█' * (count // 10)  # Simple bar chart
            self.stdout.write(f"  {hour:02d}:00 - {count:3d} movements {bar}")
        
        self.stdout.write("\\nWeekly Movement Distribution:")
        cursor.execute("""
            SELECT 
                CASE day_of_week
                    WHEN 0 THEN 'Monday'
                    WHEN 1 THEN 'Tuesday'
                    WHEN 2 THEN 'Wednesday'
                    WHEN 3 THEN 'Thursday'
                    WHEN 4 THEN 'Friday'
                    WHEN 5 THEN 'Saturday'
                    WHEN 6 THEN 'Sunday'
                END as day_name,
                COUNT(*) as movement_count
            FROM movement_analytics 
            GROUP BY day_of_week 
            ORDER BY day_of_week
        """)
        
        for day, count in cursor.fetchall():
            bar = '█' * (count // 20)
            self.stdout.write(f"  {day:9s} - {count:3d} movements {bar}")
    
    def generate_vehicle_report(self, cursor, limit):
        """Generate vehicle activity report"""
        self.stdout.write(f"Top {limit} Most Active Vehicles:")
        cursor.execute("""
            SELECT 
                vehicle_plate,
                COUNT(*) as total_movements,
                AVG(duration_minutes) as avg_duration,
                movement_frequency,
                MAX(vehicle_activity_score) as activity_score
            FROM movement_analytics 
            GROUP BY vehicle_plate, movement_frequency
            ORDER BY total_movements DESC 
            LIMIT %s
        """, [limit])
        
        for vehicle, movements, avg_duration, frequency, score in cursor.fetchall():
            self.stdout.write(
                f"  {vehicle}: {movements:3d} movements, "
                f"avg {avg_duration:.0f}min, {frequency}, score: {score}"
            )
    
    def generate_organization_report(self, cursor, limit):
        """Generate organization traffic report"""
        self.stdout.write(f"Top {limit} Organizations by Traffic:")
        cursor.execute("""
            SELECT 
                organization_from as org_name,
                COUNT(*) as total_traffic,
                COUNT(DISTINCT vehicle_plate) as unique_vehicles,
                AVG(duration_minutes) as avg_duration,
                MAX(organization_traffic_score) as traffic_score
            FROM movement_analytics 
            GROUP BY organization_from
            ORDER BY total_traffic DESC 
            LIMIT %s
        """, [limit])
        
        for org, traffic, vehicles, avg_duration, score in cursor.fetchall():
            self.stdout.write(
                f"  {org}: {traffic:3d} movements, "
                f"{vehicles} vehicles, avg {avg_duration:.0f}min, score: {score}"
            )
    
    def generate_route_report(self, cursor, limit):
        """Generate popular routes report"""
        self.stdout.write(f"Top {limit} Most Popular Routes:")
        cursor.execute("""
            SELECT 
                organization_from,
                organization_to,
                COUNT(*) as route_frequency,
                AVG(duration_minutes) as avg_duration,
                MAX(route_popularity) as popularity_score
            FROM movement_analytics 
            WHERE is_inter_org_movement = true
            GROUP BY organization_from, organization_to
            ORDER BY route_frequency DESC 
            LIMIT %s
        """, [limit])
        
        for org_from, org_to, frequency, avg_duration, popularity in cursor.fetchall():
            self.stdout.write(
                f"  {org_from} → {org_to}: {frequency:2d} trips, "
                f"avg {avg_duration:.0f}min, popularity: {popularity}"
            )