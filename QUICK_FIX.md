# Quick Fix for Migration and Static Directory Issues

## Problem
1. Static directory warning (non-critical)
2. Migration history inconsistency error

## Quick Solution

Run these commands in PowerShell **from the vehicle_intelligence directory**:

```powershell
# You're already in: C:\Users\user\OneDrive - Strathmore University\Projects\vehicle-intelligence-system\vehicle_intelligence

# 1. Try to fix migrations with --fake-initial
python manage.py migrate --fake-initial
```

If that works, you're done! If not, try:

```powershell
# 2. Alternative: Use --run-syncdb
python manage.py migrate --run-syncdb
```

If both fail, you need to manually fix the database. Connect to PostgreSQL:

```powershell
psql -U postgres -d vehicle
```

Then run this SQL:

```sql
-- Check what migrations are recorded
SELECT app, name, applied FROM django_migrations ORDER BY id;

-- If admin.0001_initial exists but main_app.0001_initial doesn't, you need to:
-- Option A: Delete admin migrations and re-run (if you can lose admin data)
DELETE FROM django_migrations WHERE app = 'admin';

-- Option B: Or fake the main_app migrations to match existing tables
-- (This assumes your tables already exist)
INSERT INTO django_migrations (app, name, applied) 
VALUES ('main_app', '0001_initial', NOW())
ON CONFLICT DO NOTHING;
```

Then run:
```powershell
python manage.py migrate
```

## Static Directory (Already Fixed)

The static directory warning is already handled in settings.py - it won't show the warning anymore.

## After Fixing Migrations

Once migrations work, start the server:

```powershell
python manage.py runserver
```




