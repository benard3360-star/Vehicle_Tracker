#!/usr/bin/env python
"""
Test script for organization analytics implementation
Run this from the Django project directory: python test_org_analytics.py
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vehicle_intelligence.settings')
django.setup()

from main_app.org_analytics import OrgAnalytics
from django.db import connection

def test_org_analytics():
    """Test the organization analytics functions"""
    
    print("Testing Organization Analytics Implementation...")
    print("=" * 50)
    
    # Test with a sample organization name
    test_org = "JKIA"
    
    print(f"Testing with organization: {test_org}")
    print("-" * 30)
    
    # Test 1: Parking Duration Analysis
    print("1. Testing Parking Duration Analysis...")
    try:
        result = OrgAnalytics.get_org_parking_duration_analysis(test_org)
        print("   ✓ Parking Duration Analysis - Success")
        print(f"   Data length: {len(result)} characters")
    except Exception as e:
        print(f"   ✗ Parking Duration Analysis - Error: {e}")
    
    # Test 2: Hourly Entries Chart
    print("2. Testing Hourly Entries Chart...")
    try:
        result = OrgAnalytics.get_org_hourly_entries_chart(test_org)
        print("   ✓ Hourly Entries Chart - Success")
        print(f"   Data length: {len(result)} characters")
    except Exception as e:
        print(f"   ✗ Hourly Entries Chart - Error: {e}")
    
    # Test 3: Vehicles Count Chart
    print("3. Testing Vehicles Count Chart...")
    try:
        result = OrgAnalytics.get_org_vehicles_count_chart(test_org)
        print("   ✓ Vehicles Count Chart - Success")
        print(f"   Data length: {len(result)} characters")
    except Exception as e:
        print(f"   ✗ Vehicles Count Chart - Error: {e}")
    
    # Test 4: Revenue Analysis Chart
    print("4. Testing Revenue Analysis Chart...")
    try:
        result = OrgAnalytics.get_org_revenue_analysis_chart(test_org)
        print("   ✓ Revenue Analysis Chart - Success")
        print(f"   Data length: {len(result)} characters")
    except Exception as e:
        print(f"   ✗ Revenue Analysis Chart - Error: {e}")
    
    # Test 5: Average Stay by Type Chart
    print("5. Testing Average Stay by Type Chart...")
    try:
        result = OrgAnalytics.get_org_avg_stay_by_type_chart(test_org)
        print("   ✓ Average Stay by Type Chart - Success")
        print(f"   Data length: {len(result)} characters")
    except Exception as e:
        print(f"   ✗ Average Stay by Type Chart - Error: {e}")
    
    # Test database connection
    print("\n6. Testing Database Connection...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM real_movement_analytics WHERE organization ILIKE %s", [f'%{test_org}%'])
            count = cursor.fetchone()[0]
            print(f"   ✓ Database Connection - Success")
            print(f"   Records found for {test_org}: {count}")
    except Exception as e:
        print(f"   ✗ Database Connection - Error: {e}")
    
    print("\n" + "=" * 50)
    print("Organization Analytics Test Complete!")

if __name__ == "__main__":
    test_org_analytics()