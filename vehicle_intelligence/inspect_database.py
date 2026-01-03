#!/usr/bin/env python3
"""
Database Inspector Script
Checks what tables and columns exist in the database
"""

import os
import sys
import django
from django.db import connection

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def inspect_database():
    """Inspect the database structure"""
    
    with connection.cursor() as cursor:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Available tables: {tables}")
        
        # Check for parking-related tables
        parking_tables = [t for t in tables if 'parking' in t.lower()]
        print(f"Parking-related tables: {parking_tables}")
        
        # Check each parking table
        for table in parking_tables:
            print(f"\nColumns in {table}:")
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = '{table}'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
            
            # Get sample data
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"  Total records: {count:,}")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table} LIMIT 3;")
                sample = cursor.fetchall()
                print(f"  Sample data (first 3 rows):")
                for i, row in enumerate(sample, 1):
                    print(f"    Row {i}: {row}")

def main():
    """Main execution function"""
    print("Database Inspector Script")
    print("=" * 40)
    
    try:
        inspect_database()
        print("\nDatabase inspection completed!")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise e

if __name__ == "__main__":
    main()