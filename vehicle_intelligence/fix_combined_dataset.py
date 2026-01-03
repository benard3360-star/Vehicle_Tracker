#!/usr/bin/env python3
"""
Combined Dataset Inspector
Checks the combined_dataset table structure and data
"""

import os
import sys
import django
from django.db import connection

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def inspect_combined_dataset():
    """Inspect the combined_dataset table"""
    
    with connection.cursor() as cursor:
        # Check columns in combined_dataset
        print("Columns in combined_dataset:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'combined_dataset'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM combined_dataset;")
        count = cursor.fetchone()[0]
        print(f"\nTotal records: {count:,}")
        
        # Check if Location column exists
        location_columns = [col[0] for col in columns if 'location' in col[0].lower()]
        org_columns = [col[0] for col in columns if 'organization' in col[0].lower()]
        
        print(f"\nLocation-related columns: {location_columns}")
        print(f"Organization-related columns: {org_columns}")
        
        # Show sample data
        if count > 0:
            cursor.execute("SELECT * FROM combined_dataset LIMIT 2;")
            sample = cursor.fetchall()
            print(f"\nSample data (first 2 rows):")
            column_names = [col[0] for col in columns]
            
            for i, row in enumerate(sample, 1):
                print(f"\nRow {i}:")
                for j, value in enumerate(row):
                    if j < len(column_names):
                        print(f"  {column_names[j]}: {value}")

def fix_combined_dataset_column():
    """Fix the Location column in combined_dataset table"""
    
    with connection.cursor() as cursor:
        # Check if Location column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'combined_dataset' 
            AND column_name IN ('Location', 'location', 'Organization', 'organization')
            ORDER BY column_name;
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing location/organization columns: {existing_columns}")
        
        if 'Location' in existing_columns:
            print("Found 'Location' column, renaming to 'Organization'...")
            cursor.execute("ALTER TABLE combined_dataset RENAME COLUMN \"Location\" TO \"Organization\";")
            print("Successfully renamed 'Location' to 'Organization'")
            
        elif 'location' in existing_columns:
            print("Found 'location' column, renaming to 'organization'...")
            cursor.execute("ALTER TABLE combined_dataset RENAME COLUMN location TO organization;")
            print("Successfully renamed 'location' to 'organization'")
            
        elif 'Organization' in existing_columns or 'organization' in existing_columns:
            print("Organization column already exists correctly")
            
        else:
            print("No Location or Organization column found!")
            return False
        
        return True

def main():
    """Main execution function"""
    print("Combined Dataset Inspector & Fixer")
    print("=" * 45)
    
    try:
        inspect_combined_dataset()
        
        print("\n" + "=" * 45)
        print("Fixing column names...")
        
        success = fix_combined_dataset_column()
        
        if success:
            print("\nColumn fix completed! Re-inspecting...")
            inspect_combined_dataset()
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise e

if __name__ == "__main__":
    main()