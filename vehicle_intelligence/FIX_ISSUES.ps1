# Fix Migration and Static Directory Issues

Write-Host "Step 1: Creating static directory..." -ForegroundColor Green
if (-not (Test-Path "static")) {
    New-Item -ItemType Directory -Path "static" | Out-Null
    Write-Host "Static directory created!" -ForegroundColor Green
} else {
    Write-Host "Static directory already exists." -ForegroundColor Yellow
}

Write-Host "`nStep 2: Attempting to fix migrations..." -ForegroundColor Green
Write-Host "Trying --fake-initial approach..." -ForegroundColor Yellow
python manage.py migrate --fake-initial

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n--fake-initial didn't work. Trying --run-syncdb..." -ForegroundColor Yellow
    python manage.py migrate --run-syncdb
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nBoth methods failed. Please check FIX_MIGRATIONS.md for manual solutions." -ForegroundColor Red
        Write-Host "You may need to manually fix the django_migrations table in PostgreSQL." -ForegroundColor Red
    }
} else {
    Write-Host "`nMigrations fixed successfully!" -ForegroundColor Green
}

Write-Host "`nDone! You can now try running the server with: python manage.py runserver" -ForegroundColor Green

