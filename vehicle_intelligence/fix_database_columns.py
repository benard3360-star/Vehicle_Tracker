#!/usr/bin/env python3
"""
Database Column Fix Script
Checks and renames 'Location' column to 'Organization' in PostgreSQL database
"""

import os
import sys
import django
from django.db import connection

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def check_and_fix_column():
    """Check if Location column exists and rename it to Organization"""
    
    with connection.cursor() as cursor:
        # Check if Location column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'parking_records' 
            AND column_name IN ('location', 'organization')
            ORDER BY column_name;
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        print(f"Existing columns: {existing_columns}")
        
        if 'location' in existing_columns and 'organization' not in existing_columns:
            print("Found 'location' column, renaming to 'organization'...")
            
            # Rename the column
            cursor.execute("ALTER TABLE parking_records RENAME COLUMN location TO organization;")
            print("Successfully renamed 'location' to 'organization'")
            
        elif 'location' in existing_columns and 'organization' in existing_columns:
            print("Both 'location' and 'organization' columns exist!")
            
            # Check if location has data that organization doesn't
            cursor.execute("""
                SELECT COUNT(*) FROM parking_records 
                WHERE location IS NOT NULL AND location != ''
                AND (organization IS NULL OR organization = '');
            """)
            
            location_data_count = cursor.fetchone()[0]
            
            if location_data_count > 0:
                print(f"Found {location_data_count} records with location data but no organization data")
                print("Copying location data to organization column...")
                
                cursor.execute("""
                    UPDATE parking_records 
                    SET organization = location 
                    WHERE location IS NOT NULL AND location != ''
                    AND (organization IS NULL OR organization = '');
                """)
                
                print("Copied location data to organization column")
            
            # Drop the location column
            print("Dropping redundant 'location' column...")
            cursor.execute("ALTER TABLE parking_records DROP COLUMN location;")
            print("Dropped 'location' column")
            
        elif 'organization' in existing_columns:
            print("'organization' column already exists and is correct")
            
        else:
            print("Neither 'location' nor 'organization' column found!")
            return False
        
        # Verify the final state
        cursor.execute("""
            SELECT COUNT(*) FROM parking_records 
            WHERE organization IS NOT NULL AND organization != '';
        """)
        
        org_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM parking_records;")
        total_count = cursor.fetchone()[0]
        
        print(f"\nFinal Status:")
        print(f"   Total records: {total_count:,}")
        print(f"   Records with organization: {org_count:,}")
        print(f"   Records missing organization: {total_count - org_count:,}")
        
        # Show sample data
        cursor.execute("""
            SELECT plate_number, organization, entry_time, amount_paid 
            FROM parking_records 
            WHERE organization IS NOT NULL 
            ORDER BY entry_time DESC 
            LIMIT 5;
        """)
        
        sample_data = cursor.fetchall()
        print(f"\nSample Data:")
        for row in sample_data:
            print(f"   {row[0]} | {row[1]} | {row[2]} | KSh {row[3]}")
        
        return True

def main():
    """Main execution function"""
    print("Database Column Fix Script")
    print("=" * 40)
    
    try:
        success = check_and_fix_column()
        
        if success:
            print("\nDatabase column fix completed successfully!")
            print("The 'organization' column is now ready for feature engineering.")
        else:
            print("\nDatabase column fix failed!")
            
    except Exception as e:
        print(f"\nError: {str(e)}")
        raise e

if __name__ == "__main__":
    main()