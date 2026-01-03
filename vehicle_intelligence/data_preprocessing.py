"""
Data Preprocessing Script
Combines Excel datasets and loads them into PostgreSQL database
"""
import os
import glob
import pandas as pd
import numpy as np
import django
from datetime import datetime
import sys
import sqlite3

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
    
    # Ensure we're using the correct column name
    org_column = 'Organization' if 'Organization' in df.columns else 'organization'
    
    for org_name in df[org_column].unique():
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
    """Apply comprehensive feature engineering to the dataset"""
    print("\nApplying comprehensive feature engineering...")
    
    # Convert time columns to datetime
    time_cols = ["Entry Time", "Exit Time", "Payment Time"]
    for col in time_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    
    # Create Vehicle ID from Plate Number
    df["Vehicle Id"] = df["Plate Number"].apply(
        lambda x: f"VH_{abs(hash(x)) % 1000000}"
    )
    
    # === TEMPORAL FEATURES ===
    df["entry_hour"] = df["Entry Time"].dt.hour
    df["entry_day_of_week"] = df["Entry Time"].dt.dayofweek
    df["entry_month"] = df["Entry Time"].dt.month
    df["entry_quarter"] = df["Entry Time"].dt.quarter
    df["entry_season"] = df["entry_month"].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
    df["is_weekend"] = (df["entry_day_of_week"] >= 5).astype(int)
    df["is_business_hours"] = df["entry_hour"].between(9, 17).astype(int)
    df["is_peak_hours"] = df["entry_hour"].isin([8, 9, 17, 18]).astype(int)
    df["is_night_entry"] = df["entry_hour"].between(22, 5).astype(int)
    
    # === DURATION FEATURES ===
    df["duration_minutes"] = ((df["Exit Time"] - df["Entry Time"]).dt.total_seconds() / 60).fillna(0)
    df["duration_category"] = pd.cut(df["duration_minutes"], 
                                   bins=[0, 30, 120, 480, float('inf')], 
                                   labels=[0, 1, 2, 3], include_lowest=True).astype(float)
    df["duration_efficiency_score"] = np.clip(100 - (df["duration_minutes"] - 60).abs() / 10, 0, 100)
    df["is_overstay"] = (df["duration_minutes"] > 240).astype(int)
    
    # === VEHICLE BEHAVIOR FEATURES ===
    vehicle_stats = df.groupby("Vehicle Id").agg({
        "Entry Time": "count",
        "Amount Paid": "sum",
        "Organization": "nunique"
    }).rename(columns={
        "Entry Time": "visit_frequency",
        "Amount Paid": "total_revenue",
        "Organization": "unique_sites"
    })
    
    df = df.merge(vehicle_stats, left_on="Vehicle Id", right_index=True, how="left")
    
    df["vehicle_usage_category"] = pd.cut(df["visit_frequency"], 
                                        bins=[0, 2, 5, 10, float('inf')], 
                                        labels=[0, 1, 2, 3]).astype(float)
    df["vehicle_revenue_tier"] = pd.cut(df["total_revenue"], 
                                      bins=[0, 100, 500, 1000, float('inf')], 
                                      labels=[0, 1, 2, 3]).astype(float)
    df["is_multi_site_vehicle"] = (df["unique_sites"] > 1).astype(int)
    
    # === ORGANIZATION FEATURES ===
    org_stats = df.groupby("Organization").agg({
        "Vehicle Id": "nunique",
        "Amount Paid": "sum"
    }).rename(columns={
        "Vehicle Id": "org_vehicle_count",
        "Amount Paid": "org_total_revenue"
    })
    
    df = df.merge(org_stats, left_on="Organization", right_index=True, how="left")
    
    df["organization_size_category"] = pd.cut(df["org_vehicle_count"], 
                                            bins=[0, 50, 200, 500, float('inf')], 
                                            labels=[0, 1, 2, 3]).astype(float)
    df["organization_performance_tier"] = pd.cut(df["org_total_revenue"], 
                                               bins=[0, 1000, 5000, 10000, float('inf')], 
                                               labels=[0, 1, 2, 3]).astype(float)
    
    # === BEHAVIORAL FEATURES ===
    df["days_since_last_visit"] = df.groupby("Vehicle Id")["Entry Time"].diff().dt.days.fillna(0)
    df["visit_frequency_category"] = pd.cut(df["days_since_last_visit"], 
                                          bins=[0, 1, 7, 30, float('inf')], 
                                          labels=[3, 2, 1, 0]).astype(float)
    
    # Duration anomaly detection
    duration_mean = df["duration_minutes"].mean()
    duration_std = df["duration_minutes"].std()
    df["is_duration_anomaly"] = (abs(df["duration_minutes"] - duration_mean) > 2 * duration_std).astype(int)
    
    # Payment anomaly detection
    payment_mean = df["Amount Paid"].mean()
    payment_std = df["Amount Paid"].std()
    df["is_payment_anomaly"] = (abs(df["Amount Paid"] - payment_mean) > 2 * payment_std).astype(int)
    
    # === FINANCIAL FEATURES ===
    df["revenue_per_minute"] = (df["Amount Paid"] / df["duration_minutes"]).replace([np.inf, -np.inf], 0).fillna(0)
    df["is_digital_payment"] = df["Payment Method"].isin(["Card", "Mobile", "Digital"]).astype(int)
    df["payment_efficiency_score"] = np.where(df["Amount Paid"] > 0, 
                                            np.clip(df["revenue_per_minute"] * 10, 0, 100), 0)
    
    # === LEGACY FEATURES (for compatibility) ===
    df["Parking Status"] = df["Exit Time"].apply(
        lambda x: "Active / Overnight" if pd.isna(x) else "Completed"
    )
    df["Parking Duration Min"] = df["duration_minutes"]
    df["Entry Hour"] = df["entry_hour"]
    df["Entry Day"] = df["Entry Time"].dt.day
    df["Entry Weekday"] = df["Entry Time"].dt.day_name()
    df["Entry Week"] = df["Entry Time"].dt.isocalendar().week
    df["Entry Month"] = df["Entry Time"].dt.month_name()
    df["Is Weekend"] = df["is_weekend"]
    df["Exit Hour"] = df["Exit Time"].dt.hour
    df["Exit Weekday"] = df["Exit Time"].dt.day_name()
    df["Payment Status"] = df["Amount Paid"].apply(
        lambda x: "Paid" if pd.notna(x) and x > 0
        else "Zero Payment" if pd.notna(x) and x == 0
        else "No Record"
    )
    df["Visit Count Per Vehicle"] = df["visit_frequency"]
    df["Unique Sites Per Vehicle"] = df["unique_sites"]
    df["Is Night Entry"] = df["is_night_entry"]
    df["Is Overstay"] = df["is_overstay"]
    df["Is Multi Site Vehicle"] = df["is_multi_site_vehicle"]
    
    print(f"Feature engineering complete. New shape: {df.shape}")
    print(f"Total features created: {len([col for col in df.columns if col not in ['Entry Time', 'Exit Time', 'Payment Time', 'Plate Number', 'Vehicle Type', 'Plate Color', 'Vehicle Brand', 'Amount Paid', 'Payment Method', 'Organization']])}")
    
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
        'Organization': 'organization',  # Ensure this maps to organization
        'Location': 'organization'  # Handle both Location and Organization columns
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


def create_parking_records(df):
    """Create parking records from the dataset with engineered features"""
    from main_app.models import ParkingRecord
    from django.utils import timezone as django_timezone
    
    records_created = 0
    
    for index, row in df.iterrows():
        try:
            # Parse datetime fields
            entry_time_raw = row.get('Entry Time')
            exit_time_raw = row.get('Exit Time')
            payment_time_raw = row.get('Payment Time')
            
            # Skip if entry time is invalid
            if pd.isna(entry_time_raw):
                continue
            
            # Convert to timezone-aware datetime
            entry_time = django_timezone.make_aware(entry_time_raw.to_pydatetime())
            
            # Handle exit time (might be NaT for active parking)
            exit_time = None
            if not pd.isna(exit_time_raw):
                exit_time = django_timezone.make_aware(exit_time_raw.to_pydatetime())
            
            # Handle payment time
            payment_time = None
            if not pd.isna(payment_time_raw):
                payment_time = django_timezone.make_aware(payment_time_raw.to_pydatetime())
            
            # Calculate parking duration
            parking_duration = row.get('duration_minutes', 0)
            if pd.isna(parking_duration):
                parking_duration = 0
            
            # Create parking record with engineered features
            record, created = ParkingRecord.objects.get_or_create(
                plate_number=str(row.get('Plate Number', '')),
                entry_time=entry_time,
                defaults={
                    'exit_time': exit_time,
                    'vehicle_type': str(row.get('Vehicle Type', 'Unknown')),
                    'plate_color': str(row.get('Plate Color', 'Unknown')),
                    'vehicle_brand': str(row.get('Vehicle Brand', 'Unknown')),
                    'amount_paid': float(row.get('Amount Paid', 0) or 0),
                    'payment_time': payment_time,
                    'payment_method': str(row.get('Payment Method', 'Unknown')),
                    'organization': str(row.get('Organization', 'Unknown')),
                    'parking_duration_minutes': int(parking_duration),
                    'parking_status': 'completed' if exit_time else 'active',
                    # Engineered features
                    'entry_hour': int(row.get('entry_hour', 0)),
                    'entry_day_of_week': int(row.get('entry_day_of_week', 0)),
                    'entry_month': int(row.get('entry_month', 1)),
                    'entry_quarter': int(row.get('entry_quarter', 1)),
                    'entry_season': int(row.get('entry_season', 0)),
                    'is_weekend': bool(row.get('is_weekend', False)),
                    'is_business_hours': bool(row.get('is_business_hours', False)),
                    'is_peak_hours': bool(row.get('is_peak_hours', False)),
                    'is_night_entry': bool(row.get('is_night_entry', False)),
                    'duration_category': int(row.get('duration_category', 0)) if not pd.isna(row.get('duration_category')) else 0,
                    'duration_efficiency_score': float(row.get('duration_efficiency_score', 0)),
                    'is_overstay': bool(row.get('is_overstay', False)),
                    'visit_frequency': int(row.get('visit_frequency', 1)),
                    'total_revenue': float(row.get('total_revenue', 0)),
                    'unique_sites': int(row.get('unique_sites', 1)),
                    'vehicle_usage_category': int(row.get('vehicle_usage_category', 0)) if not pd.isna(row.get('vehicle_usage_category')) else 0,
                    'vehicle_revenue_tier': int(row.get('vehicle_revenue_tier', 0)) if not pd.isna(row.get('vehicle_revenue_tier')) else 0,
                    'is_multi_site_vehicle': bool(row.get('is_multi_site_vehicle', False)),
                    'org_vehicle_count': int(row.get('org_vehicle_count', 0)),
                    'org_total_revenue': float(row.get('org_total_revenue', 0)),
                    'organization_size_category': int(row.get('organization_size_category', 0)) if not pd.isna(row.get('organization_size_category')) else 0,
                    'organization_performance_tier': int(row.get('organization_performance_tier', 0)) if not pd.isna(row.get('organization_performance_tier')) else 0,
                    'days_since_last_visit': float(row.get('days_since_last_visit', 0)),
                    'visit_frequency_category': int(row.get('visit_frequency_category', 0)) if not pd.isna(row.get('visit_frequency_category')) else 0,
                    'is_duration_anomaly': bool(row.get('is_duration_anomaly', False)),
                    'is_payment_anomaly': bool(row.get('is_payment_anomaly', False)),
                    'revenue_per_minute': float(row.get('revenue_per_minute', 0)),
                    'is_digital_payment': bool(row.get('is_digital_payment', False)),
                    'payment_efficiency_score': float(row.get('payment_efficiency_score', 0))
                }
            )
            
            if created:
                records_created += 1
                
        except Exception as e:
            print(f"Error creating parking record for row {index}: {e}")
            continue
    
    print(f"Created {records_created} parking records with engineered features")
    return records_created


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


def update_combined_dataset_with_features(df):
    """Update the combined_dataset table with engineered features"""
    print("\nUpdating combined_dataset table with engineered features...")
    
    # Connect to SQLite database
    db_path = 'db.sqlite3'
    conn = sqlite3.connect(db_path)
    
    try:
        # First, check if combined_dataset table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='combined_dataset';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("Creating combined_dataset table...")
            # Create table with all feature columns
            create_table_sql = """
            CREATE TABLE combined_dataset (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                "Entry Time" TEXT,
                "Exit Time" TEXT,
                "Payment Time" TEXT,
                "Plate Number" TEXT,
                "Vehicle Type" TEXT,
                "Plate Color" TEXT,
                "Vehicle Brand" TEXT,
                "Amount Paid" REAL,
                "Payment Method" TEXT,
                "Organization" TEXT,
                "Vehicle Id" TEXT,
                entry_hour INTEGER,
                entry_day_of_week INTEGER,
                entry_month INTEGER,
                entry_quarter INTEGER,
                entry_season INTEGER,
                is_weekend INTEGER,
                is_business_hours INTEGER,
                is_peak_hours INTEGER,
                is_night_entry INTEGER,
                duration_minutes REAL,
                duration_category REAL,
                duration_efficiency_score REAL,
                is_overstay INTEGER,
                visit_frequency INTEGER,
                total_revenue REAL,
                unique_sites INTEGER,
                vehicle_usage_category REAL,
                vehicle_revenue_tier REAL,
                is_multi_site_vehicle INTEGER,
                org_vehicle_count INTEGER,
                org_total_revenue REAL,
                organization_size_category REAL,
                organization_performance_tier REAL,
                days_since_last_visit REAL,
                visit_frequency_category REAL,
                is_duration_anomaly INTEGER,
                is_payment_anomaly INTEGER,
                revenue_per_minute REAL,
                is_digital_payment INTEGER,
                payment_efficiency_score REAL
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
        else:
            # Add new feature columns if they don't exist
            feature_columns = [
                ('entry_hour', 'INTEGER'),
                ('entry_day_of_week', 'INTEGER'),
                ('entry_month', 'INTEGER'),
                ('entry_quarter', 'INTEGER'),
                ('entry_season', 'INTEGER'),
                ('is_weekend', 'INTEGER'),
                ('is_business_hours', 'INTEGER'),
                ('is_peak_hours', 'INTEGER'),
                ('is_night_entry', 'INTEGER'),
                ('duration_minutes', 'REAL'),
                ('duration_category', 'REAL'),
                ('duration_efficiency_score', 'REAL'),
                ('is_overstay', 'INTEGER'),
                ('visit_frequency', 'INTEGER'),
                ('total_revenue', 'REAL'),
                ('unique_sites', 'INTEGER'),
                ('vehicle_usage_category', 'REAL'),
                ('vehicle_revenue_tier', 'REAL'),
                ('is_multi_site_vehicle', 'INTEGER'),
                ('org_vehicle_count', 'INTEGER'),
                ('org_total_revenue', 'REAL'),
                ('organization_size_category', 'REAL'),
                ('organization_performance_tier', 'REAL'),
                ('days_since_last_visit', 'REAL'),
                ('visit_frequency_category', 'REAL'),
                ('is_duration_anomaly', 'INTEGER'),
                ('is_payment_anomaly', 'INTEGER'),
                ('revenue_per_minute', 'REAL'),
                ('is_digital_payment', 'INTEGER'),
                ('payment_efficiency_score', 'REAL')
            ]
            
            # Get existing columns
            cursor.execute("PRAGMA table_info(combined_dataset)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Add missing columns
            for col_name, col_type in feature_columns:
                if col_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE combined_dataset ADD COLUMN {col_name} {col_type}")
                        print(f"Added column: {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"Error adding column {col_name}: {e}")
            
            conn.commit()
        
        # Clear existing data and insert new data with features
        cursor.execute("DELETE FROM combined_dataset")
        
        # Prepare data for insertion
        columns_to_insert = [
            'Entry Time', 'Exit Time', 'Payment Time', 'Plate Number', 'Vehicle Type',
            'Plate Color', 'Vehicle Brand', 'Amount Paid', 'Payment Method', 'Organization',
            'Vehicle Id', 'entry_hour', 'entry_day_of_week', 'entry_month', 'entry_quarter',
            'entry_season', 'is_weekend', 'is_business_hours', 'is_peak_hours', 'is_night_entry',
            'duration_minutes', 'duration_category', 'duration_efficiency_score', 'is_overstay',
            'visit_frequency', 'total_revenue', 'unique_sites', 'vehicle_usage_category',
            'vehicle_revenue_tier', 'is_multi_site_vehicle', 'org_vehicle_count', 'org_total_revenue',
            'organization_size_category', 'organization_performance_tier', 'days_since_last_visit',
            'visit_frequency_category', 'is_duration_anomaly', 'is_payment_anomaly',
            'revenue_per_minute', 'is_digital_payment', 'payment_efficiency_score'
        ]
        
        # Convert datetime columns to strings for SQLite
        df_copy = df.copy()
        for col in ['Entry Time', 'Exit Time', 'Payment Time']:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].astype(str)
        
        # Insert data
        placeholders = ','.join(['?' for _ in columns_to_insert])
        insert_sql = f"INSERT INTO combined_dataset ({','.join([f'\"{col}\"' for col in columns_to_insert])}) VALUES ({placeholders})"
        
        data_to_insert = []
        for _, row in df_copy.iterrows():
            row_data = []
            for col in columns_to_insert:
                if col in row:
                    value = row[col]
                    if pd.isna(value) or value == 'NaT':
                        row_data.append(None)
                    else:
                        row_data.append(value)
                else:
                    row_data.append(None)
            data_to_insert.append(tuple(row_data))
        
        cursor.executemany(insert_sql, data_to_insert)
        conn.commit()
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM combined_dataset")
        count = cursor.fetchone()[0]
        print(f"Successfully updated combined_dataset table with {count} records and {len(columns_to_insert)} columns")
        
    except Exception as e:
        print(f"Error updating combined_dataset table: {e}")
        conn.rollback()
    finally:
        conn.close()


def main():
    """Main data processing function"""
    print("Starting comprehensive data preprocessing with feature engineering...")
    
    # Step 1: Combine Excel files
    master_df = combine_excel_files()
    if master_df is None:
        return
    
    # Step 2: Comprehensive feature engineering
    master_df = feature_engineering(master_df)
    
    # Step 3: Update combined_dataset table with engineered features
    update_combined_dataset_with_features(master_df)
    
    # Step 4: Map columns for Django models
    master_df = map_columns(master_df)
    
    # Step 5: Create organizations
    print("\nCreating organizations...")
    organizations = create_organizations(master_df)
    
    # Step 6: Create vehicles
    print("\nCreating vehicles...")
    vehicles = create_vehicles(master_df, organizations)
    
    # Step 7: Create parking records (the main data source for analytics)
    print("\nCreating parking records...")
    parking_records_count = create_parking_records(master_df)
    
    # Step 8: Create movements (for additional analytics)
    print("\nCreating vehicle movements...")
    movements_count = create_movements(master_df, vehicles, organizations)
    
    # Summary
    print(f"\n=== DATA PROCESSING COMPLETE ===")
    print(f"Organizations: {len(organizations)}")
    print(f"Vehicles: {len(vehicles)}")
    print(f"Parking Records: {parking_records_count}")
    print(f"Movements: {movements_count}")
    print(f"Total records processed: {len(master_df)}")
    print(f"Features engineered: 40+ temporal, behavioral, financial, and anomaly detection features")
    
    # Save enhanced dataset with features
    output_file = 'enhanced_vehicle_data_with_features.xlsx'
    master_df.to_excel(output_file, index=False)
    print(f"Enhanced dataset with all features saved as: {output_file}")


if __name__ == "__main__":
    main()