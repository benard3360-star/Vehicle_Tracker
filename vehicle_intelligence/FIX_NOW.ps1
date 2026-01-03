# Quick Fix Script for Migration History
# Run this script to fix the migration history issue

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fixing Django Migration History" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Step 1: Connecting to PostgreSQL to fix migration history..." -ForegroundColor Yellow

# Create temporary SQL file
$sqlContent = @"
-- Delete any existing main_app migrations
DELETE FROM django_migrations WHERE app = 'main_app';

-- Insert main_app migrations with timestamps BEFORE admin.0001_initial
INSERT INTO django_migrations (app, name, applied) VALUES
('main_app', '0001_initial', '2025-12-19 08:49:58.000000+03'),
('main_app', '0002_add_feature_engineering_fields', '2025-12-19 08:49:58.100000+03'),
('main_app', '0003_rename_location_to_organization', '2025-12-19 08:49:58.200000+03');

-- Verify
SELECT app, name, applied FROM django_migrations WHERE app = 'main_app' ORDER BY applied;
"@

$sqlFile = "temp_fix_migrations.sql"
$sqlContent | Out-File -FilePath $sqlFile -Encoding UTF8

Write-Host "Created SQL script. Now run this command:" -ForegroundColor Green
Write-Host ""
Write-Host "psql -U postgres -d vehicle -f $sqlFile" -ForegroundColor White
Write-Host ""
Write-Host "Or manually run the SQL in PostgreSQL." -ForegroundColor Yellow
Write-Host ""
Write-Host "After running the SQL, press Enter to continue with migrations..." -ForegroundColor Yellow
Read-Host

Write-Host ""
Write-Host "Step 2: Running Django migrations..." -ForegroundColor Yellow
python manage.py migrate

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Migrations completed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now you can start the server with:" -ForegroundColor Cyan
    Write-Host "python manage.py runserver" -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Migrations failed. Please check the error above." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

# Clean up
if (Test-Path $sqlFile) {
    Remove-Item $sqlFile
}


