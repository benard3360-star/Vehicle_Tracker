"""
Check what tables exist in the database
"""
import sqlite3

def check_database_tables():
    """Check all tables in the database"""
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("All tables in database:")
        print("="*40)
        
        if not tables:
            print("No tables found in database!")
            return
        
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  Records: {count:,}")
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"  Columns ({len(columns)}):")
            for col in columns:
                print(f"    - {col[1]} ({col[2]})")
            
            # Show sample data if records exist
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                sample_data = cursor.fetchall()
                print(f"  Sample data (first 3 rows):")
                for i, row in enumerate(sample_data, 1):
                    print(f"    Row {i}: {row[:5]}...")  # Show first 5 columns
        
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_tables()