from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Query real vehicle movement analytics data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--report',
            type=str,
            choices=['summary', 'temporal', 'vehicles', 'organizations', 'revenue'],
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
            self.style.SUCCESS(f'Real Vehicle Analytics - {report_type.title()} Report')
        )
        self.stdout.write('=' * 60)
        
        with connection.cursor() as cursor:
            if report_type == 'summary':
                self.generate_summary_report(cursor)
            elif report_type == 'temporal':
                self.generate_temporal_report(cursor)
            elif report_type == 'vehicles':
                self.generate_vehicle_report(cursor, limit)
            elif report_type == 'organizations':
                self.generate_organization_report(cursor)
            elif report_type == 'revenue':
                self.generate_revenue_report(cursor, limit)
    
    def generate_summary_report(self, cursor):
        """Generate overall summary statistics"""
        cursor.execute("SELECT COUNT(*) FROM real_movement_analytics")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT plate_number) FROM real_movement_analytics")
        vehicles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT organization) FROM real_movement_analytics")
        orgs = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(duration_minutes) FROM real_movement_analytics")
        avg_duration = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(amount_paid) FROM real_movement_analytics")
        total_revenue = cursor.fetchone()[0]
        
        self.stdout.write(f"Total Records: {total:,}")
        self.stdout.write(f"Unique Vehicles: {vehicles:,}")
        self.stdout.write(f"Organizations: {orgs}")
        self.stdout.write(f"Average Duration: {avg_duration:.1f} minutes")
        self.stdout.write(f"Total Revenue: KSh {total_revenue:,.2f}")
    
    def generate_temporal_report(self, cursor):
        """Generate temporal analysis"""
        self.stdout.write("Hourly Distribution:")
        cursor.execute("""
            SELECT entry_hour, COUNT(*) as count
            FROM real_movement_analytics 
            GROUP BY entry_hour 
            ORDER BY entry_hour
        """)
        
        for hour, count in cursor.fetchall():
            bar = '█' * (count // 500)
            self.stdout.write(f"  {hour:02d}:00 - {count:4d} visits {bar}")
        
        self.stdout.write("\\nWeekly Distribution:")
        cursor.execute("""
            SELECT 
                CASE day_of_week
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                    WHEN 0 THEN 'Sunday'
                END as day_name,
                COUNT(*) as count
            FROM real_movement_analytics 
            GROUP BY day_of_week 
            ORDER BY day_of_week
        """)
        
        for day, count in cursor.fetchall():
            bar = '█' * (count // 1000)
            self.stdout.write(f"  {day:9s} - {count:5d} visits {bar}")
    
    def generate_vehicle_report(self, cursor, limit):
        """Generate vehicle activity report"""
        self.stdout.write(f"Top {limit} Most Active Vehicles:")
        cursor.execute("""
            SELECT 
                plate_number,
                vehicle_visit_count,
                vehicle_total_revenue,
                vehicle_avg_duration,
                vehicle_usage_type,
                vehicle_revenue_tier
            FROM real_movement_analytics 
            GROUP BY plate_number, vehicle_visit_count, vehicle_total_revenue, 
                     vehicle_avg_duration, vehicle_usage_type, vehicle_revenue_tier
            ORDER BY vehicle_visit_count DESC 
            LIMIT %s
        """, [limit])
        
        for plate, visits, revenue, avg_dur, usage, tier in cursor.fetchall():
            self.stdout.write(
                f"  {plate}: {visits} visits, KSh {revenue:,.0f}, "
                f"{avg_dur:.0f}min avg, {usage}/{tier}"
            )
    
    def generate_organization_report(self, cursor):
        """Generate organization analysis"""
        self.stdout.write("Organization Performance:")
        cursor.execute("""
            SELECT 
                organization,
                org_total_vehicles,
                org_total_revenue,
                org_avg_duration,
                org_size_category,
                org_performance_tier,
                COUNT(*) as total_visits
            FROM real_movement_analytics 
            GROUP BY organization, org_total_vehicles, org_total_revenue, 
                     org_avg_duration, org_size_category, org_performance_tier
            ORDER BY total_visits DESC
        """)
        
        for org, vehicles, revenue, avg_dur, size, perf, visits in cursor.fetchall():
            self.stdout.write(
                f"  {org}: {visits:,} visits, {vehicles:,} vehicles, "
                f"KSh {revenue:,.0f}, {size}/{perf}"
            )
    
    def generate_revenue_report(self, cursor, limit):
        """Generate revenue analysis"""
        self.stdout.write("Revenue Analysis:")
        
        cursor.execute("""
            SELECT revenue_category, COUNT(*), SUM(amount_paid), AVG(amount_paid)
            FROM real_movement_analytics 
            GROUP BY revenue_category 
            ORDER BY SUM(amount_paid) DESC
        """)
        
        for category, count, total, avg in cursor.fetchall():
            self.stdout.write(
                f"  {category.title()}: {count:,} visits, "
                f"KSh {total:,.0f} total, KSh {avg:.0f} avg"
            )
        
        self.stdout.write(f"\\nTop {limit} Revenue Generating Vehicles:")
        cursor.execute("""
            SELECT plate_number, vehicle_total_revenue, vehicle_visit_count
            FROM real_movement_analytics 
            GROUP BY plate_number, vehicle_total_revenue, vehicle_visit_count
            ORDER BY vehicle_total_revenue DESC 
            LIMIT %s
        """, [limit])
        
        for plate, revenue, visits in cursor.fetchall():
            self.stdout.write(f"  {plate}: KSh {revenue:,.0f} ({visits} visits)")