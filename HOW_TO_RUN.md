# How to Run the Vehicle Intelligence System

## Prerequisites

1. **Python 3.11** installed on your system
2. **PostgreSQL** installed and running
3. **Virtual environment** (venv) - already created in the project

## Step-by-Step Instructions

### Step 1: Activate Virtual Environment

Open PowerShell or Command Prompt in the project root directory and run:

```powershell
# Navigate to project root (if not already there)
cd "C:\Users\user\OneDrive - Strathmore University\Projects\vehicle-intelligence-system"

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 2: Verify PostgreSQL is Running

Make sure PostgreSQL is running with these credentials:
- **Database Name**: `vehicle`
- **User**: `postgres`
- **Password**: `2000`
- **Host**: `localhost`
- **Port**: `5432`

You can verify by opening pgAdmin or running:
```powershell
psql -U postgres -d vehicle
```

### Step 3: Install/Update Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Navigate to Django Project Directory

```powershell
cd vehicle_intelligence
```

### Step 5: Run Database Migrations

```powershell
# Create any new migrations (if needed)
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate
```

### Step 6: Create Vehicle Users (IMPORTANT)

**This step creates user accounts for all vehicle plates in your database:**

```powershell
cd vehicle_intelligence
python manage.py create_vehicle_users
```

This command will:
- Create user accounts for each vehicle plate number
- Assign users to their respective organizations (JKIA, KNH, etc.)
- Generate automatic passwords for each user
- Display the login credentials for organization admins

### Step 7: Create Superuser (if you don't have one)

```powershell
python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### Step 8: Run the Development Server

```powershell
python manage.py runserver
```

You should see output like:
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Step 9: Access the Application

Open your web browser and go to:
- **Main URL**: http://127.0.0.1:8000
- **Admin Panel**: http://127.0.0.1:8000/admin
- **Analytics**: http://127.0.0.1:8000/analytics/
- **Dashboard**: http://127.0.0.1:8000/dashboard/

## Quick Start (All-in-One Command)

If you're already in the project root with venv activated:

```powershell
cd vehicle_intelligence
python manage.py migrate
python manage.py create_vehicle_users
python manage.py runserver
```

## Troubleshooting

### Issue: "relation 'vehicles' does not exist"
**Solution**: This is already fixed! The code now uses `combined_dataset` table instead.

### Issue: "column 'Location' does not exist"
**Solution**: This is already fixed! The code now uses `"Organization"` column.

### Issue: "No module named 'django'"
**Solution**: Make sure virtual environment is activated and dependencies are installed:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue: "could not connect to server"
**Solution**: 
1. Make sure PostgreSQL is running
2. Check database credentials in `vehicle_intelligence/vehicle_intelligence/settings.py`
3. Verify database `vehicle` exists:
```sql
CREATE DATABASE vehicle;
```

### Issue: "ProgrammingError: column does not exist"
**Solution**: Make sure the `combined_dataset` table exists in PostgreSQL with the correct column names:
- `"Organization"` (with capital O and quotes)
- `"Plate Number"`
- `"Amount Paid"`
- `"Vehicle Brand"`
- `"Vehicle Type"`

## Important Notes

1. **Database**: The application uses PostgreSQL. Make sure it's running before starting the server.

2. **Virtual Environment**: Always activate the virtual environment before running commands.

3. **Port**: The default port is 8000. If it's busy, use:
   ```powershell
   python manage.py runserver 8001
   ```

4. **Data**: Make sure your `combined_dataset` table in PostgreSQL has data for the analytics to work properly.

## Files Modified (All Saved)

✅ `vehicle_intelligence/main_app/analytics.py` - Fixed column names
✅ `vehicle_intelligence/main_app/views.py` - Fixed Vehicle.objects queries
✅ `vehicle_intelligence/main_app/templates/org_admin_dashboard.html` - Fixed chart rendering
✅ `vehicle_intelligence/main_app/templates/analytics.html` - Fixed chart rendering

All changes have been saved and are ready to use!

## Next Steps After Running

1. Login with your superuser credentials
2. Navigate to Analytics page to see visualizations
3. Check Organization Admin Dashboard for charts
4. All visualizations should now display correctly!




