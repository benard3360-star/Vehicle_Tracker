import os
import glob
import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone
from main_app.models import Organization, ParkingRecord


class Command(BaseCommand):
    help = 'Load Excel data from Data folder into PostgreSQL database'

    def handle(self, *args, **options):
        self.stdout.write('Starting data preprocessing...')
        
        # Get Excel files from Data folder
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Data')
        excel_files = glob.glob(os.path.join(data_path, "*.xlsx"))
        
        if not excel_files:
            self.stdout.write(self.style.ERROR(f'No Excel files found in {data_path}'))
            return
        
        self.stdout.write(f'Found {len(excel_files)} Excel files')
        
        # Combine all Excel files
        df_list = []
        for file in excel_files:
            self.stdout.write(f'Processing: {os.path.basename(file)}')
            df = pd.read_excel(file)
            location_name = os.path.splitext(os.path.basename(file))[0].split('-')[-1]
            df['Organization'] = location_name
            df_list.append(df)
        
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
        
        self.stdout.write(f'Combined dataset shape: {master_df.shape}')
        
        # Convert time columns to datetime
        time_cols = ["Entry Time", "Exit Time", "Payment Time"]
        for col in time_cols:
            if col in master_df.columns:
                master_df[col] = pd.to_datetime(master_df[col], errors="coerce")
        
        # Create organizations
        organizations = {}
        for org_name in master_df['Organization'].unique():
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
                self.stdout.write(f'Created organization: {org_name}')
        
        # Create parking records
        records_created = 0
        skipped_records = 0
        for index, row in master_df.iterrows():
            try:
                # Parse datetime fields
                entry_time_raw = row.get('Entry Time')
                exit_time_raw = row.get('Exit Time')
                payment_time_raw = row.get('Payment Time')
                
                if pd.isna(entry_time_raw) or entry_time_raw is pd.NaT:
                    skipped_records += 1
                    continue
                
                entry_time = timezone.make_aware(entry_time_raw.to_pydatetime()) if hasattr(entry_time_raw, 'to_pydatetime') else timezone.make_aware(entry_time_raw)
                
                exit_time = None
                if not pd.isna(exit_time_raw) and exit_time_raw is not pd.NaT:
                    exit_time = timezone.make_aware(exit_time_raw.to_pydatetime()) if hasattr(exit_time_raw, 'to_pydatetime') else timezone.make_aware(exit_time_raw)
                
                payment_time = None
                if not pd.isna(payment_time_raw) and payment_time_raw is not pd.NaT:
                    payment_time = timezone.make_aware(payment_time_raw.to_pydatetime()) if hasattr(payment_time_raw, 'to_pydatetime') else timezone.make_aware(payment_time_raw)
                
                parking_duration = 0
                if exit_time:
                    parking_duration = (exit_time - entry_time).total_seconds() / 60
                
                plate_number = str(row.get('Plate Number', ''))
                organization = str(row.get('Organization', 'Unknown'))
                
                # Skip if record already exists
                if ParkingRecord.objects.filter(
                    plate_number=plate_number,
                    entry_time=entry_time,
                    organization=organization
                ).exists():
                    skipped_records += 1
                    continue
                
                # Create new record
                record = ParkingRecord.objects.create(
                    plate_number=plate_number,
                    entry_time=entry_time,
                    exit_time=exit_time,
                    vehicle_type=str(row.get('Vehicle Type', 'Unknown')),
                    plate_color=str(row.get('Plate Color', 'Unknown')),
                    vehicle_brand=str(row.get('Vehicle Brand', 'Unknown')),
                    amount_paid=float(row.get('Amount Paid', 0) or 0),
                    payment_time=payment_time,
                    payment_method=str(row.get('Payment Method', 'Unknown')),
                    organization=organization,
                    parking_duration_minutes=int(parking_duration),
                    parking_status='completed' if exit_time else 'active'
                )
                
                records_created += 1
                
                if records_created % 1000 == 0:
                    self.stdout.write(f'Created {records_created} records...')
                    
            except Exception as e:
                self.stdout.write(f'Error processing row {index}: {e}')
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Data loading complete!\n'
                f'Organizations: {len(organizations)}\n'
                f'Parking Records: {records_created}\n'
                f'Skipped Records: {skipped_records}\n'
                f'Total rows processed: {len(master_df)}'
            )
        )