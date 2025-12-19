"""
Simple script to check setup and import data to PostgreSQL
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).resolve().parent
sys.path.append(str(project_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

def check_database_connection():
    """Test database connection"""
    try:
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_data_folder():
    """Check if Data folder exists with Excel files"""
    data_path = project_dir / 'Data'
    if not data_path.exists():
        print(f"❌ Data folder not found at: {data_path}")
        return False
    
    excel_files = list(data_path.glob("*.xlsx"))
    if not excel_files:
        print(f"❌ No Excel files found in: {data_path}")
        return False
    
    print(f"✅ Found {len(excel_files)} Excel files:")
    for file in excel_files:
        print(f"   - {file.name}")
    return True

def run_migrations():
    """Run Django migrations"""
    try:
        from django.core.management import execute_from_command_line
        print("🔄 Running migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations completed")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def import_data():
    """Import data from Excel files"""
    try:
        # Import the data processing functions
        sys.path.append(str(project_dir.parent))
        from data_preprocessing import main as process_data
        
        print("🔄 Starting data import...")
        process_data()
        print("✅ Data import completed")
        return True
    except Exception as e:
        print(f"❌ Data import failed: {e}")
        return False

def check_imported_data():
    """Check if data was imported successfully"""
    try:
        from main_app.models import Organization, Vehicle, VehicleMovement
        
        org_count = Organization.objects.count()
        vehicle_count = Vehicle.objects.count()
        movement_count = VehicleMovement.objects.count()
        
        print(f"📊 Data Summary:")
        print(f"   Organizations: {org_count}")
        print(f"   Vehicles: {vehicle_count}")
        print(f"   Movements: {movement_count}")
        
        if org_count > 0 and vehicle_count > 0:
            print("✅ Data successfully imported to PostgreSQL")
            return True
        else:
            print("⚠️ Data import may have issues")
            return False
            
    except Exception as e:
        print(f"❌ Error checking data: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 Vehicle Intelligence Data Import Tool")
    print("=" * 50)
    
    # Step 1: Check database connection
    if not check_database_connection():
        return
    
    # Step 2: Check data folder
    if not check_data_folder():
        print("\n💡 Please ensure:")
        print("   1. Create a 'Data' folder in your project root")
        print("   2. Place your .xlsx files in the Data folder")
        return
    
    # Step 3: Run migrations
    if not run_migrations():
        return
    
    # Step 4: Import data
    if not import_data():
        return
    
    # Step 5: Verify import
    check_imported_data()
    
    print("\n🎉 Setup complete! You can now:")
    print("   1. Run: python manage.py runserver")
    print("   2. Login to your system")
    print("   3. Go to Analytics module")
    print("   4. View your real data analytics!")

if __name__ == "__main__":
    main()