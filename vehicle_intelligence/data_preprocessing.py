"""
Data Preprocessing Script
Combines Excel datasets and loads them into PostgreSQL database
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

from main_app.models import Organization, Vehicle, VehicleMovement, CustomUser


def combine_excel_files():
    """Combine all Excel files from Data folder"""
    file_path = 'Data'
    
    # Get all Excel files in the folder
    all_files = glob.glob(os.path.join(file_path, "*.xlsx"))
    
    if not all_files:
        print("No Excel files found in Data folder")
        return None
    
    print(f"Found {len(all_files)} Excel files")
    
    # List to hold all DataFrames
    df_list = []
    
    for file in all_files:
        print(f"Processing: {file}")
        # Read the Excel file
        df = pd.read_excel(file)
        
        # Extract the last part of the filename as Organization
        location_name = os.path.splitext(os.path.basename(file))[0].split('-')[-1]
        df['Organization'] = location_name
        
        # Append to the list
        df_list.append(df)
    
    # Concatenate all DataFrames vertically
    master_df = pd.concat(df_list, ignore_index=True)
    
    # Clean organization names
    master_df['Organization'].replace('1st December United Mall', 'United Mall', regex=True, inplace=True)
    
    # Clean column names
    master_df.columns = (
        master_df.columns
        .str.replace(r"\(Kenyan Time\)", "", regex=True)
        .str.strip()
        .str.title()
    )
    
    print(f"Combined dataset shape: {master_df.shape}")
    print(f"Organizations found: {master_df['Organization'].unique()}")
    print(f"Columns: {list(master_df.columns)}")
    
    return master_df


def create_organizations(df):
    """Create organizations from the dataset"""
    organizations = {}
    
    for org_name in df['organization'].unique():
        org, created = Organization.objects.get_or_create(
            name=org_name,
            defaults={
                'slug': org_name.lower().replace(' ', '-'),
                'email': f'admin@{org_name.lower().replace(" ", "")}.com',
                'is_active': True
            }
        )
        organizations[org_name] = org
        if created:
            print(f"Created organization: {org_name}")
    
    return organizations


def feature_engineering(df):
    """Apply feature engineering to the dataset"""
    print("\nApplying feature engineering...")
    
    # Convert time columns to datetime
    time_cols = ["Entry Time", "Exit Time", "Payment Time"]
    for col in time_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # Create Vehicle ID from Plate Number
    df["Vehicle Id"] = df["Plate Number"].apply(
        lambda x: f"VH_{abs(hash(x)) % 1000000}"
    )
    
    # Parking Status
    df["Parking Status"] = df["Exit Time"].apply(
        lambda x: "Active / Overnight" if pd.isna(x) else "Completed"
    )
    
    # Parking Duration in Minutes
    df["Parking Duration Min"] = (
        (df["Exit Time"] - df["Entry Time"])
        .dt.total_seconds()
        .div(60)
    )
    df.loc[df["Exit Time"].isna(), "Parking Duration Min"] = pd.NA
    
    # Features from Entry Time
    df["Entry Hour"] = df["Entry Time"].dt.hour
    df["Entry Day"] = df["Entry Time"].dt.day
    df["Entry Weekday"] = df["Entry Time"].dt.day_name()
    df["Entry Week"] = df["Entry Time"].dt.isocalendar().week
    df["Entry Month"] = df["Entry Time"].dt.month_name()
    df["Is Weekend"] = df["Entry Time"].dt.weekday >= 5
    
    # Features from Exit Time (where present)
    df["Exit Hour"] = df["Exit Time"].dt.hour
    df["Exit Weekday"] = df["Exit Time"].dt.day_name()
    
    # Payment Status
    df["Payment Status"] = df["Amount Paid"].apply(
        lambda x: "Paid" if pd.notna(x) and x > 0
        else "Zero Payment" if pd.notna(x) and x == 0
        else "No Record"
    )
    
    # Visit count per vehicle
    visit_count = (
        df.groupby("Vehicle Id")
        .size()
        .rename("Visit Count Per Vehicle")
    )
    df = df.join(visit_count, on="Vehicle Id")
    
    # Unique sites per vehicle (using Organization as Site Name)
    unique_sites = (
        df.groupby("Vehicle Id")["Organization"]
        .nunique()
        .rename("Unique Sites Per Vehicle")
    )
    df = df.join(unique_sites, on="Vehicle Id")
    
    # Helper thresholds
    POLICY_OVERSTAY_MIN = 240  # 4 hours
    
    # Night entry
    df["Is Night Entry"] = df["Entry Hour"].between(0, 5)
    
    # Overstay (completed only)
    df["Is Overstay"] = (
        (df["Parking Status"] == "Completed") &
        (df["Parking Duration Min"] > POLICY_OVERSTAY_MIN)
    )
    
    # Multi-site vehicle
    df["Is Multi Site Vehicle"] = df["Unique Sites Per Vehicle"] > 1
    
    print(f"Feature engineering complete. New shape: {df.shape}")
    print(f"New columns added: {df.columns.tolist()[-15:]}")
    
    # Summary statistics
    print("\n=== DATASET SUMMARY ===")
    
    # Unique vehicles
    total_vehicles = df["Vehicle Id"].nunique()
    print(f"Total Unique Vehicles: {total_vehicles}")
    
    # Active / Overnight vehicles (unique)
    active_overnight = (
        df[df["Parking Status"] == "Active / Overnight"]
        ["Vehicle Id"]
        .nunique()
    )
    print(f"Active / Overnight Unique Vehicles: {active_overnight}")
    
    # Completed stays (events, not vehicles)
    completed_stays = (df["Parking Status"] == "Completed").sum()
    print(f"Total Completed Stays: {completed_stays}")
    
    # Overstay % (based on completed stays)
    overstay_pct = (
        df["Is Overstay"].sum() / completed_stays * 100
        if completed_stays > 0 else 0
    )
    print(f"Overstay Percentage: {overstay_pct:.1f}%")
    
    return df


def map_columns(df):
    """Map dataset columns to our model fields"""
    # Print available columns to help with mapping
    print("Available columns:")
    for i, col in enumerate(df.columns):
        print(f"{i}: {col}")
    
    # Map your actual parking data columns to vehicle movement fields
    column_mapping = {
        'Vehicle Id': 'vehicle_id',  # Use the engineered Vehicle Id
        'Entry Time': 'start_time', 
        'Exit Time': 'end_time',
        'Vehicle Type': 'vehicle_type',
        'Plate Color': 'plate_color',
        'Vehicle Brand': 'vehicle_brand',
        'Amount Paid': 'amount_paid',
        'Payment Time': 'payment_time',
        'Payment Method': 'payment_method',
        'Organization': 'organization'
    }
    
    # Rename columns
    df_mapped = df.rename(columns=column_mapping)
    
    return df_mapped


def create_vehicles(df, organizations):
    """Create vehicles from the dataset"""
    vehicles = {}
    
    for _, row in df.drop_duplicates('vehicle_id').iterrows():
        if pd.isna(row['vehicle_id']):
            continue
            
        org = organizations.get(row['organization'])
        if not org:
            continue
        
        # Extract make from vehicle_brand if available
        brand = str(row.get('vehicle_brand', 'Unknown'))
        make = brand.split()[0] if brand != 'Unknown' else 'Unknown'
        
        vehicle, created = Vehicle.objects.get_or_create(
            vehicle_id=str(row['vehicle_id']),
            defaults={
                'make': make,
                'model': brand,
                'year': 2020,
                'vin': f"VIN{str(row['vehicle_id']).replace(' ', '').replace('-', '')[:10].zfill(10)}",
                'license_plate': str(row['vehicle_id']),
                'fuel_type': 'gasoline',
                'organization': org,
                'is_active': True
            }
        )
        vehicles[str(row['vehicle_id'])] = vehicle
        if created:
            print(f"Created vehicle: {row['vehicle_id']}")
    
    return vehicles


def create_movements(df, vehicles, organizations):
    """Create vehicle movements from parking data with enhanced features"""
    from django.utils import timezone as django_timezone
    movements_created = 0
    
    for index, row in df.iterrows():
        if pd.isna(row['vehicle_id']):
            continue
        
        vehicle = vehicles.get(str(row['vehicle_id']))
        if not vehicle:
            continue
        
        # Parse datetime fields with proper timezone handling
        try:
            start_time_raw = row.get('start_time')
            end_time_raw = row.get('end_time')
            
            # Skip if start time is invalid or NaT
            if pd.isna(start_time_raw) or start_time_raw is pd.NaT:
                continue
            
            # Convert to timezone-aware datetime
            start_time = django_timezone.make_aware(start_time_raw.to_pydatetime())
            
            # Handle end time (might be NaT for active parking)
            if pd.isna(end_time_raw) or end_time_raw is pd.NaT:
                end_time = None
                trip_status = 'active'
                duration_minutes = 0
                estimated_distance = 0
                estimated_fuel = 0
                estimated_speed = 0
            else:
                end_time = django_timezone.make_aware(end_time_raw.to_pydatetime())
                # Calculate duration for completed trips
                duration_minutes = (end_time - start_time).total_seconds() / 60
                if duration_minutes <= 0:
                    continue
                
                trip_status = 'completed'
                # Estimate distance based on parking duration
                estimated_distance = min(50, max(5, duration_minutes / 10))
                estimated_fuel = estimated_distance * 0.1
                estimated_speed = min(60, max(20, estimated_distance / (duration_minutes / 60)))
        
        except Exception as e:
            print(f"Error processing row {index}: {e}")
            continue
        
        # Generate trip ID from parking session
        trip_id = f"PARK_{row['organization']}_{start_time.strftime('%Y%m%d_%H%M')}_{index}"
        
        # Create movement record with enhanced data
        try:
            movement, created = VehicleMovement.objects.get_or_create(
                trip_id=trip_id,
                defaults={
                    'vehicle': vehicle,
                    'start_location': 'Origin',
                    'end_location': str(row['organization']),
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_minutes': int(duration_minutes),
                    'distance_km': round(estimated_distance, 2),
                    'fuel_consumed_liters': round(estimated_fuel, 2),
                    'average_speed_kmh': round(estimated_speed, 2),
                    'max_speed_kmh': round(estimated_speed * 1.2, 2),
                    'trip_status': trip_status
                }
            )
            
            if created:
                movements_created += 1
        except Exception as e:
            print(f"Error creating movement for trip {trip_id}: {e}")
            continue
    
    print(f"Created {movements_created} movement records")
    return movements_created


def main():
    """Main data processing function"""
    print("Starting data preprocessing...")
    
    # Step 1: Combine Excel files
    master_df = combine_excel_files()
    if master_df is None:
        return
    
    # Step 2: Feature engineering
    master_df = feature_engineering(master_df)
    
    # Step 3: Map columns
    master_df = map_columns(master_df)
    
    # Step 4: Create organizations
    print("\nCreating organizations...")
    organizations = create_organizations(master_df)
    
    # Step 5: Create vehicles
    print("\nCreating vehicles...")
    vehicles = create_vehicles(master_df, organizations)
    
    # Step 6: Create movements
    print("\nCreating vehicle movements...")
    movements_count = create_movements(master_df, vehicles, organizations)
    
    # Summary
    print(f"\n=== DATA PROCESSING COMPLETE ===")
    print(f"Organizations: {len(organizations)}")
    print(f"Vehicles: {len(vehicles)}")
    print(f"Movements: {movements_count}")
    print(f"Total records processed: {len(master_df)}")
    
    # Save enhanced dataset with features
    output_file = 'enhanced_vehicle_data.xlsx'
    master_df.to_excel(output_file, index=False)
    print(f"Enhanced dataset with features saved as: {output_file}")


if __name__ == "__main__":
    main()