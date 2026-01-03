-- COPY AND PASTE THIS ENTIRE BLOCK INTO PostgreSQL
-- This fixes the migration history by inserting main_app migrations with correct timestamps

-- Delete any existing main_app migrations (to avoid duplicates)
DELETE FROM django_migrations WHERE app = 'main_app';

-- Insert main_app migrations with timestamps BETWEEN contenttypes.0001_initial and admin.0001_initial
-- contenttypes.0001_initial: 2025-12-19 08:49:59.989482+03
-- admin.0001_initial: 2025-12-19 08:50:00.159107+03
-- So we insert at 08:50:00.000000+03 (right before admin)

INSERT INTO django_migrations (app, name, applied) VALUES
('main_app', '0001_initial', '2025-12-19 08:50:00.000000+03'),
('main_app', '0002_add_feature_engineering_fields', '2025-12-19 08:50:00.050000+03'),
('main_app', '0003_rename_location_to_organization', '2025-12-19 08:50:00.100000+03');

-- Verify they were added correctly (should show 3 rows)
SELECT app, name, applied FROM django_migrations WHERE app = 'main_app' ORDER BY applied;

-- Show full migration order to verify
SELECT app, name, applied FROM django_migrations ORDER BY applied;


