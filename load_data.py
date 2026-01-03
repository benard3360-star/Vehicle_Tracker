#!/usr/bin/env python
"""
Quick script to load Excel data into the database
"""
import os
import sys
import django

# Add the project directory to Python path
project_dir = os.path.join(os.path.dirname(__file__), 'vehicle_intelligence')
sys.path.insert(0, project_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

# Now import and run the data preprocessing
from data_preprocessing import main

if __name__ == "__main__":
    print("Loading Excel data into database...")
    main()
    print("Data loading complete!")