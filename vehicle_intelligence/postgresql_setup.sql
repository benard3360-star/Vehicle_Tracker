
-- Create combined_dataset table with all engineered features
DROP TABLE IF EXISTS combined_dataset;

CREATE TABLE combined_dataset (
    id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20),
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    vehicle_type VARCHAR(50),
    plate_color VARCHAR(30),
    vehicle_brand VARCHAR(50),
    amount_paid DECIMAL(10,2),
    payment_time TIMESTAMP,
    payment_method VARCHAR(30),
    organization VARCHAR(100),
    parking_duration_minutes INTEGER,
    parking_status VARCHAR(20),
    created_at TIMESTAMP,
    vehicle_id VARCHAR(50),
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
    duration_category INTEGER,
    duration_efficiency_score REAL,
    is_overstay INTEGER,
    visit_frequency INTEGER,
    total_revenue REAL,
    unique_sites INTEGER,
    vehicle_usage_category INTEGER,
    vehicle_revenue_tier INTEGER,
    is_multi_site_vehicle INTEGER,
    org_vehicle_count INTEGER,
    org_total_revenue REAL,
    organization_size_category INTEGER,
    organization_performance_tier INTEGER,
    days_since_last_visit REAL,
    visit_frequency_category INTEGER,
    is_duration_anomaly INTEGER,
    is_payment_anomaly INTEGER,
    revenue_per_minute REAL,
    is_digital_payment INTEGER,
    payment_efficiency_score REAL
);

-- Copy data from CSV (run this after creating the table)
-- COPY combined_dataset FROM 'c:\Users\user\OneDrive - Strathmore University\Projects\vehicle-intelligence-system\vehicle_intelligence\combined_dataset_with_features.csv' DELIMITER ',' CSV HEADER;

-- Verify data
SELECT COUNT(*) as total_records FROM combined_dataset;
SELECT organization, COUNT(*) as records FROM combined_dataset GROUP BY organization;
