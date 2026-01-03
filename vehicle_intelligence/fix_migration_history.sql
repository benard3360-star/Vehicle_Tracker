-- Fix Django Migration History
-- This script inserts the missing main_app migrations with timestamps BEFORE admin migrations
-- Run this in PostgreSQL: psql -U postgres -d vehicle -f fix_migration_history.sql

-- Delete main_app migrations if they exist (to avoid conflicts)
DELETE FROM django_migrations WHERE app = 'main_app';

-- Insert main_app migrations with timestamps BEFORE admin.0001_initial
-- admin.0001_initial was applied at: 2025-12-19 08:50:00.159107+03
-- So we'll insert main_app migrations at 08:49:59 (just before contenttypes)

INSERT INTO django_migrations (app, name, applied) VALUES
('main_app', '0001_initial', '2025-12-19 08:49:58.000000+03'),
('main_app', '0002_add_feature_engineering_fields', '2025-12-19 08:49:58.100000+03'),
('main_app', '0003_rename_location_to_organization', '2025-12-19 08:49:58.200000+03')
ON CONFLICT DO NOTHING;

-- Verify the migrations were added correctly
SELECT app, name, applied FROM django_migrations WHERE app = 'main_app' ORDER BY applied;

-- Show all migrations in chronological order
SELECT app, name, applied FROM django_migrations ORDER BY applied;


