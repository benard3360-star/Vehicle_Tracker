# Fix Migration History Issue

The error occurs because Django's admin migrations were applied before main_app migrations in the database. Here are solutions:

## Solution 1: Fake Initial Migrations (Recommended if database already has tables)

If your database tables already exist and you just need to align migration history:

```powershell
# Fake the initial migrations to match database state
python manage.py migrate --fake-initial
```

## Solution 2: Reset Migration History (Use only if data loss is acceptable)

If you can afford to lose data in Django-managed tables:

```powershell
# 1. Drop all Django tables (WARNING: This deletes data!)
# Connect to PostgreSQL and run:
# DROP TABLE IF EXISTS django_migrations CASCADE;
# DROP TABLE IF EXISTS django_content_type CASCADE;
# DROP TABLE IF EXISTS django_session CASCADE;
# DROP TABLE IF EXISTS auth_permission CASCADE;
# DROP TABLE IF EXISTS auth_group CASCADE;
# DROP TABLE IF EXISTS auth_group_permissions CASCADE;
# ... (drop all other Django tables)

# 2. Then run migrations fresh
python manage.py migrate
```

## Solution 3: Manual Fix (Safest - Keeps data)

Manually fix the migration history in PostgreSQL:

```sql
-- Connect to your database
psql -U postgres -d vehicle

-- Check current migration state
SELECT * FROM django_migrations ORDER BY id;

-- Delete problematic migration records (if needed)
DELETE FROM django_migrations WHERE app = 'admin' AND name = '0001_initial';

-- Then run migrations normally
```

## Solution 4: Use --run-syncdb (Quick fix)

```powershell
python manage.py migrate --run-syncdb
```

## Recommended Approach

For development, try Solution 1 first (--fake-initial). If that doesn't work, try Solution 4. Only use Solution 2 if you're okay with losing data.




