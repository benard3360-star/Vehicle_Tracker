"""
Load parking data into ParkingRecord table
"""
import os
import glob
import pandas as pd
import django
from datetime import datetime
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.models import ParkingRecord
from django.utils import timezone

def load_parking_data():
    """Load parking data from Excel files into ParkingRecord table"""
    file_path = 'Data'
    
    # Get all Excel files
    all_files = glob.glob(os.path.join(file_path, "*.xlsx"))
    
    if not all_files:
        print("No Excel files found in Data folder")
        return
    
    print(f"Found {len(all_files)} Excel files")
    
    # Clear existing records
    ParkingRecord.objects.all().delete()
    print("Cleared existing parking records")
    
    total_records = 0
    
    for file in all_files:
        print(f"Processing: {file}")
        df = pd.read_excel(file)
        
        # Extract organization name from filename
        org_name = os.path.splitext(os.path.basename(file))[0].split('-')[-1]
        org_name = org_name.replace('1st December United Mall', 'United Mall')
        
        # Clean column names
        df.columns = df.columns.str.replace(r"\(Kenyan Time\)", "", regex=True).str.strip()
        
        # Convert time columns
        df['Entry Time'] = pd.to_datetime(df['Entry Time'], errors='coerce')
        df['Exit Time'] = pd.to_datetime(df['Exit Time'], errors='coerce')
        df['Payment Time'] = pd.to_datetime(df['Payment Time'], errors='coerce')
        
        # Create parking records
        for _, row in df.iterrows():
            if pd.isna(row['Entry Time']) or pd.isna(row['Plate Number']):
                continue
            
            try:
                # Calculate parking duration
                duration_minutes = None
                if pd.notna(row['Exit Time']):
                    duration_minutes = (row['Exit Time'] - row['Entry Time']).total_seconds() / 60
                
                # Create record
                ParkingRecord.objects.create(
                    plate_number=str(row['Plate Number']).strip(),
                    entry_time=timezone.make_aware(row['Entry Time'].to_pydatetime()),
                    exit_time=timezone.make_aware(row['Exit Time'].to_pydatetime()) if pd.notna(row['Exit Time']) else None,
                    vehicle_type=str(row.get('Vehicle Type', 'Unknown')),
                    plate_color=str(row.get('Plate Color', 'Unknown')),
                    vehicle_brand=str(row.get('Vehicle Brand', 'Unknown')),
                    amount_paid=float(row.get('Amount Paid', 0)),
                    payment_time=timezone.make_aware(row['Payment Time'].to_pydatetime()) if pd.notna(row['Payment Time']) else None,
                    payment_method=str(row.get('Payment Method', 'Unknown')),
                    organization=org_name,
                    parking_duration_minutes=int(duration_minutes) if duration_minutes else None,
                    parking_status='completed' if pd.notna(row['Exit Time']) else 'active'
                )
                total_records += 1
                
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
    
    print(f"Loaded {total_records} parking records successfully")

if __name__ == "__main__":
    load_parking_data()