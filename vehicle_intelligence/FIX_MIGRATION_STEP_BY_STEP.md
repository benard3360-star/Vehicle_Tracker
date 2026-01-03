# Fix Migration History - Step by Step

The problem is that `admin.0001_initial` was applied before `main_app.0001_initial`, but admin depends on main_app (because it uses CustomUser). We need to fix the migration history.

## Solution: Insert main_app migrations with earlier timestamps

### Step 1: Connect to PostgreSQL

```powershell
psql -U postgres -d vehicle
```

### Step 2: Run this SQL in PostgreSQL

```sql
-- Delete any existing main_app migrations (if they exist)
DELETE FROM django_migrations WHERE app = 'main_app';

-- Insert main_app migrations with timestamps BEFORE admin.0001_initial
-- admin.0001_initial was at: 2025-12-19 08:50:00.159107+03
-- contenttypes.0001_initial was at: 2025-12-19 08:49:59.989482+03
-- So we'll insert main_app migrations at 08:49:58 (before contenttypes)

INSERT INTO django_migrations (app, name, applied) VALUES
('main_app', '0001_initial', '2025-12-19 08:49:58.000000+03'),
('main_app', '0002_add_feature_engineering_fields', '2025-12-19 08:49:58.100000+03'),
('main_app', '0003_rename_location_to_organization', '2025-12-19 08:49:58.200000+03');

-- Verify they were added (should show 3 rows)
SELECT app, name, applied FROM django_migrations WHERE app = 'main_app' ORDER BY applied;

-- Exit PostgreSQL
\q
```

### Step 3: Run Django Migrations

```powershell
python manage.py migrate
```

This should now work without errors!

### Step 4: Start the Server

```powershell
python manage.py runserver
```

## Alternative: Use the SQL file

Or you can run the SQL file directly:

```powershell
psql -U postgres -d vehicle -f fix_migration_history.sql
```

Then run:
```powershell
python manage.py migrate
python manage.py runserver
```


