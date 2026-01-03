# Generated migration for feature engineering fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0001_initial'),
    ]

    operations = [
        # Temporal Features
        migrations.AddField(
            model_name='parkingrecord',
            name='entry_hour',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='entry_day_of_week',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='entry_week_of_year',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='entry_month',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='entry_quarter',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_weekend',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_business_hours',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_peak_hours',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_night_entry',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='season',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        
        # Duration Features
        migrations.AddField(
            model_name='parkingrecord',
            name='duration_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='duration_category',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_overstay',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='duration_efficiency',
            field=models.FloatField(blank=True, null=True),
        ),
        
        # Vehicle Features
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_visit_count',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_total_revenue',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_avg_duration',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_unique_sites',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_usage_type',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_is_multi_site',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='vehicle_revenue_tier',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        
        # Organization Features
        migrations.AddField(
            model_name='parkingrecord',
            name='org_total_vehicles',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='org_total_revenue',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='org_avg_duration',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='org_size_category',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='org_performance_tier',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        
        # Behavioral Features
        migrations.AddField(
            model_name='parkingrecord',
            name='is_duration_anomaly',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_payment_anomaly',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='days_since_last_visit',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='visit_frequency',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        
        # Financial Features
        migrations.AddField(
            model_name='parkingrecord',
            name='revenue_per_minute',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='payment_efficiency',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='revenue_category',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='parkingrecord',
            name='is_digital_payment',
            field=models.BooleanField(default=False),
        ),
        
        # Add indexes for better performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_parking_weekend_entry ON parking_records(is_weekend, entry_time);",
            reverse_sql="DROP INDEX IF EXISTS idx_parking_weekend_entry;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_parking_peak_hours ON parking_records(is_peak_hours, entry_time);",
            reverse_sql="DROP INDEX IF EXISTS idx_parking_peak_hours;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_parking_usage_type ON parking_records(vehicle_usage_type);",
            reverse_sql="DROP INDEX IF EXISTS idx_parking_usage_type;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_parking_duration_category ON parking_records(duration_category);",
            reverse_sql="DROP INDEX IF EXISTS idx_parking_duration_category;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_parking_revenue_category ON parking_records(revenue_category);",
            reverse_sql="DROP INDEX IF EXISTS idx_parking_revenue_category;"
        ),
    ]