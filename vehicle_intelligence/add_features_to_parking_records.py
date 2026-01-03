"""
Add engineered features to the existing parking_records table
"""
import sqlite3
import pandas as pd
import numpy as np

def add_engineered_features_to_parking_records():
    """Add engineered features to existing parking_records table"""
    conn = sqlite3.connect('db.sqlite3')
    
    try:
        # Load existing data from parking_records
        print("Loading existing data from parking_records table...")
        df = pd.read_sql_query("SELECT * FROM parking_records", conn)
        print(f"Loaded {len(df)} records")
        
        # Display current columns
        print(f"\\nCurrent columns: {list(df.columns)}")
        
        # Convert datetime columns
        df['entry_time'] = pd.to_datetime(df['entry_time'], errors='coerce')
        df['exit_time'] = pd.to_datetime(df['exit_time'], errors='coerce')
        df['payment_time'] = pd.to_datetime(df['payment_time'], errors='coerce')
        
        print("\\nCalculating engineered features...")
        
        # Create Vehicle ID from plate number
        df['vehicle_id'] = df['plate_number'].apply(lambda x: f"VH_{abs(hash(str(x))) % 1000000}")
        
        # === TEMPORAL FEATURES ===
        print("  - Temporal features...")
        df['entry_hour'] = df['entry_time'].dt.hour
        df['entry_day_of_week'] = df['entry_time'].dt.dayofweek
        df['entry_month'] = df['entry_time'].dt.month
        df['entry_quarter'] = df['entry_time'].dt.quarter
        df['entry_season'] = df['entry_month'].map({12:0, 1:0, 2:0, 3:1, 4:1, 5:1, 6:2, 7:2, 8:2, 9:3, 10:3, 11:3})
        df['is_weekend'] = (df['entry_day_of_week'] >= 5).astype(int)
        df['is_business_hours'] = df['entry_hour'].between(9, 17).astype(int)
        df['is_peak_hours'] = df['entry_hour'].isin([8, 9, 17, 18]).astype(int)
        df['is_night_entry'] = df['entry_hour'].between(22, 5).astype(int)
        
        # === DURATION FEATURES ===
        print("  - Duration features...")
        df['duration_minutes'] = ((df['exit_time'] - df['entry_time']).dt.total_seconds() / 60).fillna(0)
        df['duration_category'] = pd.cut(df['duration_minutes'], 
                                       bins=[0, 30, 120, 480, float('inf')], 
                                       labels=[0, 1, 2, 3], include_lowest=True).astype(float).fillna(0).astype(int)
        df['duration_efficiency_score'] = np.clip(100 - (df['duration_minutes'] - 60).abs() / 10, 0, 100)
        df['is_overstay'] = (df['duration_minutes'] > 240).astype(int)
        
        # === VEHICLE BEHAVIOR FEATURES ===
        print("  - Vehicle behavior features...")
        vehicle_stats = df.groupby('vehicle_id').agg({
            'entry_time': 'count',
            'amount_paid': 'sum',
            'organization': 'nunique'
        }).rename(columns={
            'entry_time': 'visit_frequency',
            'amount_paid': 'total_revenue',
            'organization': 'unique_sites'
        })
        
        df = df.merge(vehicle_stats, left_on='vehicle_id', right_index=True, how='left')
        
        df['vehicle_usage_category'] = pd.cut(df['visit_frequency'], 
                                            bins=[0, 2, 5, 10, float('inf')], 
                                            labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['vehicle_revenue_tier'] = pd.cut(df['total_revenue'], 
                                          bins=[0, 100, 500, 1000, float('inf')], 
                                          labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['is_multi_site_vehicle'] = (df['unique_sites'] > 1).astype(int)
        
        # === ORGANIZATION FEATURES ===
        print("  - Organization features...")
        org_stats = df.groupby('organization').agg({
            'vehicle_id': 'nunique',
            'amount_paid': 'sum'
        }).rename(columns={
            'vehicle_id': 'org_vehicle_count',
            'amount_paid': 'org_total_revenue'
        })
        
        df = df.merge(org_stats, left_on='organization', right_index=True, how='left')
        
        df['organization_size_category'] = pd.cut(df['org_vehicle_count'], 
                                                bins=[0, 50, 200, 500, float('inf')], 
                                                labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        df['organization_performance_tier'] = pd.cut(df['org_total_revenue'], 
                                                   bins=[0, 1000, 5000, 10000, float('inf')], 
                                                   labels=[0, 1, 2, 3]).astype(float).fillna(0).astype(int)
        
        # === BEHAVIORAL FEATURES ===
        print("  - Behavioral features...")
        df = df.sort_values(['vehicle_id', 'entry_time'])
        df['days_since_last_visit'] = df.groupby('vehicle_id')['entry_time'].diff().dt.days.fillna(0)
        df['visit_frequency_category'] = pd.cut(df['days_since_last_visit'], 
                                              bins=[0, 1, 7, 30, float('inf')], 
                                              labels=[3, 2, 1, 0]).astype(float).fillna(0).astype(int)
        
        # Anomaly detection
        duration_mean = df['duration_minutes'].mean()
        duration_std = df['duration_minutes'].std()
        df['is_duration_anomaly'] = (abs(df['duration_minutes'] - duration_mean) > 2 * duration_std).astype(int)
        
        payment_mean = df['amount_paid'].mean()
        payment_std = df['amount_paid'].std()
        df['is_payment_anomaly'] = (abs(df['amount_paid'] - payment_mean) > 2 * payment_std).astype(int)
        
        # === FINANCIAL FEATURES ===
        print("  - Financial features...")
        df['revenue_per_minute'] = (df['amount_paid'] / df['duration_minutes']).replace([np.inf, -np.inf], 0).fillna(0)
        df['is_digital_payment'] = df['payment_method'].isin(['Card', 'Mobile', 'Digital']).astype(int)
        df['payment_efficiency_score'] = np.where(df['amount_paid'] > 0, 
                                                np.clip(df['revenue_per_minute'] * 10, 0, 100), 0)
        
        # Add feature columns to database
        print("\\nAdding feature columns to parking_records table...")
        cursor = conn.cursor()
        
        feature_columns = [
            ('vehicle_id', 'TEXT'),
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
            ('duration_category', 'INTEGER'),
            ('duration_efficiency_score', 'REAL'),
            ('is_overstay', 'INTEGER'),
            ('visit_frequency', 'INTEGER'),
            ('total_revenue', 'REAL'),
            ('unique_sites', 'INTEGER'),
            ('vehicle_usage_category', 'INTEGER'),
            ('vehicle_revenue_tier', 'INTEGER'),
            ('is_multi_site_vehicle', 'INTEGER'),
            ('org_vehicle_count', 'INTEGER'),
            ('org_total_revenue', 'REAL'),
            ('organization_size_category', 'INTEGER'),
            ('organization_performance_tier', 'INTEGER'),
            ('days_since_last_visit', 'REAL'),
            ('visit_frequency_category', 'INTEGER'),
            ('is_duration_anomaly', 'INTEGER'),
            ('is_payment_anomaly', 'INTEGER'),
            ('revenue_per_minute', 'REAL'),
            ('is_digital_payment', 'INTEGER'),
            ('payment_efficiency_score', 'REAL')
        ]
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(parking_records)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Add missing feature columns
        for col_name, col_type in feature_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE parking_records ADD COLUMN {col_name} {col_type}")
                    print(f"  Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        print(f"  Error adding column {col_name}: {e}")
        
        conn.commit()
        
        # Update records with calculated features in batches
        print("\\nUpdating records with engineered features...")
        batch_size = 1000
        total_updated = 0
        
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            
            for _, row in batch_df.iterrows():
                if pd.notna(row.get('id')):
                    update_values = []
                    update_params = []
                    
                    for col_name, _ in feature_columns:
                        if col_name in row and pd.notna(row[col_name]):
                            update_values.append(f"{col_name} = ?")
                            update_params.append(row[col_name])
                    
                    if update_values:
                        update_params.append(row['id'])
                        update_sql = f"UPDATE parking_records SET {', '.join(update_values)} WHERE id = ?"
                        cursor.execute(update_sql, update_params)
                        total_updated += 1
            
            # Commit batch
            conn.commit()
            print(f"  Updated batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1} ({total_updated:,} records)")
        
        # Generate summary
        print("\\n" + "="*60)
        print("FEATURE ENGINEERING SUMMARY")
        print("="*60)
        print(f"Total Records Updated: {total_updated:,}")
        print(f"\\nTemporal Features:")
        print(f"  Weekend Visits: {df['is_weekend'].sum():,} ({df['is_weekend'].mean()*100:.1f}%)")
        print(f"  Peak Hour Visits: {df['is_peak_hours'].sum():,} ({df['is_peak_hours'].mean()*100:.1f}%)")
        print(f"  Night Entries: {df['is_night_entry'].sum():,} ({df['is_night_entry'].mean()*100:.1f}%)")
        
        print(f"\\nDuration Features:")
        print(f"  Overstays: {df['is_overstay'].sum():,} ({df['is_overstay'].mean()*100:.1f}%)")
        print(f"  Average Duration: {df['duration_minutes'].mean():.1f} minutes")
        print(f"  Completed Stays: {(df['duration_minutes'] > 0).sum():,}")
        
        print(f"\\nVehicle Features:")
        print(f"  Unique Vehicles: {df['vehicle_id'].nunique():,}")
        print(f"  Multi-site Vehicles: {df['is_multi_site_vehicle'].sum():,}")
        print(f"  Frequent Users (>10 visits): {(df['visit_frequency'] > 10).sum():,}")
        
        print(f"\\nOrganization Features:")
        print(f"  Organizations: {df['organization'].nunique():,}")
        print(f"  Average Vehicles per Org: {df['org_vehicle_count'].mean():.1f}")
        print(f"  Large Organizations (>200 vehicles): {(df['organization_size_category'] == 3).sum():,}")
        
        print(f"\\nFinancial Features:")
        print(f"  Total Revenue: KSh {df['amount_paid'].sum():,.2f}")
        print(f"  Average Revenue per Visit: KSh {df['amount_paid'].mean():.2f}")
        print(f"  Digital Payments: {df['is_digital_payment'].sum():,} ({df['is_digital_payment'].mean()*100:.1f}%)")
        print(f"  High Revenue Visits (>KSh 500): {(df['amount_paid'] > 500).sum():,}")
        
        print(f"\\nBehavioral Features:")
        print(f"  Duration Anomalies: {df['is_duration_anomaly'].sum():,} ({df['is_duration_anomaly'].mean()*100:.1f}%)")
        print(f"  Payment Anomalies: {df['is_payment_anomaly'].sum():,} ({df['is_payment_anomaly'].mean()*100:.1f}%)")
        print(f"  Daily Visitors: {(df['visit_frequency_category'] == 3).sum():,}")
        
        print(f"\\nFeature engineering completed successfully!")
        print(f"Added {len(feature_columns)} engineered features to the parking_records table.")
        print(f"The analytics system can now use these features for enhanced insights and visualizations.")
        
        # Create a summary table for quick reference
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feature_engineering_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_records INTEGER,
            unique_vehicles INTEGER,
            organizations INTEGER,
            total_revenue REAL,
            weekend_percentage REAL,
            overstay_percentage REAL,
            digital_payment_percentage REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        INSERT INTO feature_engineering_summary 
        (total_records, unique_vehicles, organizations, total_revenue, weekend_percentage, overstay_percentage, digital_payment_percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            len(df),
            df['vehicle_id'].nunique(),
            df['organization'].nunique(),
            df['amount_paid'].sum(),
            df['is_weekend'].mean() * 100,
            df['is_overstay'].mean() * 100,
            df['is_digital_payment'].mean() * 100
        ))
        
        conn.commit()
        print(f"\\nCreated feature_engineering_summary table for quick analytics reference.")
        
    except Exception as e:
        print(f"Error adding engineered features: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main execution function"""
    print("Vehicle Intelligence System - Add Engineered Features to Parking Records")
    print("="*80)
    
    add_engineered_features_to_parking_records()

if __name__ == "__main__":
    main()