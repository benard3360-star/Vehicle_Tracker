#!/usr/bin/env python
"""
Check real_movement_analytics data
"""
import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from django.db import connection

def check_real_data():
    """Check what data is available in real_movement_analytics"""
    
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'real_movement_analytics'
            )
        """)
        table_exists = cursor.fetchone()[0]
        print(f"real_movement_analytics table exists: {table_exists}")
        
        if table_exists:
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM real_movement_analytics')
            total_records = cursor.fetchone()[0]
            print(f"Total records: {total_records}")
            
            # Get sample plate numbers and organizations
            cursor.execute("""
                SELECT DISTINCT plate_number, organization 
                FROM real_movement_analytics 
                WHERE plate_number IS NOT NULL 
                LIMIT 15
            """)
            plates = cursor.fetchall()
            print(f"\nSample plates and organizations:")
            for plate, org in plates:
                print(f"- {plate} ({org})")
            
            # Get all organizations
            cursor.execute("""
                SELECT DISTINCT organization 
                FROM real_movement_analytics 
                WHERE organization IS NOT NULL
            """)
            orgs = cursor.fetchall()
            print(f"\nAll organizations: {[org[0] for org in orgs]}")
            
            # Count plates per organization
            cursor.execute("""
                SELECT organization, COUNT(DISTINCT plate_number) as plate_count
                FROM real_movement_analytics 
                WHERE organization IS NOT NULL AND plate_number IS NOT NULL
                GROUP BY organization
                ORDER BY plate_count DESC
            """)
            org_counts = cursor.fetchall()
            print(f"\nPlates per organization:")
            for org, count in org_counts:
                print(f"- {org}: {count} plates")
        
        # Also check combined_dataset
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'combined_dataset'
            )
        """)
        combined_exists = cursor.fetchone()[0]
        print(f"\ncombined_dataset table exists: {combined_exists}")
        
        if combined_exists:
            cursor.execute('SELECT COUNT(*) FROM combined_dataset')
            combined_count = cursor.fetchone()[0]
            print(f"Combined dataset records: {combined_count}")
            
            cursor.execute("""
                SELECT DISTINCT "Organization", COUNT(DISTINCT "Plate Number") as plate_count
                FROM combined_dataset 
                WHERE "Organization" IS NOT NULL AND "Plate Number" IS NOT NULL
                GROUP BY "Organization"
                ORDER BY plate_count DESC
                LIMIT 5
            """)
            combined_orgs = cursor.fetchall()
            print(f"\nTop organizations in combined_dataset:")
            for org, count in combined_orgs:
                print(f"- {org}: {count} plates")

if __name__ == "__main__":
    check_real_data()