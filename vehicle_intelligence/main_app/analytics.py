"""
Vehicle Analytics Module
Real-time analytics using PostgreSQL data
"""
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
from django.db import connection
from django.db.models import Sum, Avg, Count, Q, Case, When, CharField, Value
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Vehicle, VehicleMovement, CustomUser, Organization
try:
    from .models import FuelTransaction
except ImportError:
    FuelTransaction = None


class VehicleAnalytics:
    """Main analytics class for vehicle data"""
    
    def __init__(self, organization=None, vehicle_brand=None, vehicle_type=None):
        self.organization = organization
        self.vehicle_brand = vehicle_brand
        self.vehicle_type = vehicle_type
    
    def _apply_filters(self, queryset):
        """Apply common filters to ParkingRecord queryset"""
        if self.organization:
            queryset = queryset.filter(organization=self.organization.name)
        if self.vehicle_brand:
            queryset = queryset.filter(vehicle_brand=self.vehicle_brand)
        if self.vehicle_type:
            queryset = queryset.filter(vehicle_type=self.vehicle_type)
        return queryset
    def get_fleet_summary(self, days=30):
        """Get fleet summary analytics"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get filtered vehicle count from ParkingRecord
        from .models import ParkingRecord
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        total_vehicles = parking_qs.values('plate_number').distinct().count()
        
        movements_qs = VehicleMovement.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            trip_status='completed'
        )
        if self.organization:
            movements_qs = movements_qs.filter(vehicle__organization=self.organization)
        
        # Calculate metrics
        active_vehicles = movements_qs.values('vehicle__license_plate').distinct().count()
        total_trips = movements_qs.count()
        avg_parking_duration = movements_qs.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0
        
        return {
            'total_vehicles': total_vehicles,
            'active_vehicles': active_vehicles,
            'total_trips': total_trips,
            'avg_parking_duration': round(avg_parking_duration, 1),
            'utilization_rate': round((active_vehicles / total_vehicles) * 100, 1) if total_vehicles > 0 else 0
        }
    

    def get_parking_duration_chart(self, days=30):
        """Generate parking duration analysis chart"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Use filtered ParkingRecord data
        from .models import ParkingRecord
        parking_qs = ParkingRecord.objects.filter(
            entry_time__date__gte=start_date,
            entry_time__date__lte=end_date
        )
        parking_qs = self._apply_filters(parking_qs)
        
        # Group by organization and calculate average parking duration
        org_data = parking_qs.values(
            'organization'
        ).annotate(
            avg_duration=Avg('parking_duration_minutes'),
            total_visits=Count('id')
        ).order_by('-avg_duration')[:10]
        
        if not org_data:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Prepare data for plotting
        org_names = [item['organization'] for item in org_data]
        avg_durations = [float(item['avg_duration'] or 0) for item in org_data]
        
        # Create bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=org_names,
                y=avg_durations,
                name='Average Parking Duration',
                marker_color='#3b82f6'
            )
        ])
        
        fig.update_layout(
            title='Average Parking Duration by Organization',
            xaxis_title='Organization',
            yaxis_title='Average Duration (Minutes)',
            template='plotly_white',
            height=400,
            xaxis_tickangle=-45
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def get_hourly_entries_chart(self, organization=None):
        """Generate hourly site entries line chart - optimized query"""
        from django.db.models.functions import Extract
        from .models import ParkingRecord
        
        # Use filtered ParkingRecord data
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        
        # Limit to recent data for performance
        recent_date = timezone.now().date() - timedelta(days=30)
        parking_qs = parking_qs.filter(entry_time__date__gte=recent_date)
        
        # Group by organization and hour
        hourly_data = parking_qs.annotate(
            entry_hour=Extract('entry_time', 'hour')
        ).values(
            'organization', 'entry_hour'
        ).annotate(
            vehicle_count=Count('id')
        ).order_by('organization', 'entry_hour')
        
        if not hourly_data:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Convert to DataFrame
        df = pd.DataFrame(list(hourly_data))
        df.columns = ['organization', 'entry_hour', 'vehicles']
        
        fig = px.line(
            df,
            x="entry_hour",
            y="vehicles",
            color="organization",
            markers=True,
            title="Hourly Vehicle Entries (Last 30 Days)",
            labels={"entry_hour": "Entry Hour", "vehicles": "Number of Vehicles"}
        )
        
        fig.update_layout(
            height=400,
            showlegend=True,
            xaxis_title="Hour of Day",
            yaxis_title="Number of Vehicles"
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def get_vehicles_per_site_chart(self, organization=None):
        """Generate vehicles per organization pie chart"""
        from .models import ParkingRecord
        from django.db.models import Count
        
        # Get filtered vehicle counts from ParkingRecord
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        
        if self.organization:
            # For single organization, show vehicle count
            count = parking_qs.values('plate_number').distinct().count()
            data = [{
                'organization': self.organization.name,
                'vehicles': count
            }]
        else:
            # For all organizations (or filtered data)
            data = []
            vehicle_counts = parking_qs.values(
                'organization'
            ).annotate(
                vehicles=Count('plate_number', distinct=True)
            ).order_by('-vehicles')
            
            for item in vehicle_counts:
                data.append({
                    'organization': item['organization'],
                    'vehicles': item['vehicles']
                })
        
        if not data:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Prepare data for pie chart
        org_names = [item['organization'] for item in data]
        vehicle_counts = [item['vehicles'] for item in data]
        
        # Create pie chart
        fig = go.Figure(data=[
            go.Pie(
                labels=org_names,
                values=vehicle_counts,
                name='Vehicles',
                hovertemplate='<b>%{label}</b><br>Vehicles: %{value}<br>Percentage: %{percent}<extra></extra>',
                textinfo='label+percent',
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='Vehicle Distribution by Organization',
            template='plotly_white',
            height=400,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def get_revenue_per_site_chart(self, organization=None):
        """Generate parking revenue per organization bar chart"""
        from django.db.models import Sum
        from .models import ParkingRecord
        
        # Get filtered revenue from parking records
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        
        revenue_data = parking_qs.values(
            'organization'
        ).annotate(
            total_revenue=Sum('amount_paid')
        ).order_by('-total_revenue')
        
        if not revenue_data:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Prepare data
        org_names = [item['organization'] for item in revenue_data if item['total_revenue']]
        revenues = [float(item['total_revenue'] or 0) for item in revenue_data if item['total_revenue']]
        
        if not org_names:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Create bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=org_names,
                y=revenues,
                name='Revenue',
                marker_color='#16a34a',
                hovertemplate='<b>%{x}</b><br>Revenue: KSh %{y:,.0f}<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title='Revenue per Organization',
            xaxis_title='Organization',
            yaxis_title='Revenue (KSh)',
            template='plotly_white',
            height=400,
            xaxis_tickangle=-45,
            showlegend=False,
            yaxis=dict(type='log')
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def get_visit_patterns_chart(self, organization=None):
        """Generate visit patterns chart - optimized with aggregation"""
        from django.db.models import Case, When, IntegerField
        from .models import ParkingRecord
        
        # Get filtered parking records and count visits per plate
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        
        # Count visits per vehicle plate
        visit_counts = parking_qs.values('plate_number').annotate(
            visit_count=Count('id')
        ).annotate(
            visit_group=Case(
                When(visit_count=1, then=Value('1')),
                When(visit_count__lte=3, then=Value('2-3')),
                default=Value('5+'),
                output_field=CharField()
            )
        ).values('visit_group').annotate(
            vehicle_count=Count('plate_number')
        ).order_by('visit_group')
        
        if not visit_counts:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Convert to lists
        visit_groups = [item['visit_group'] for item in visit_counts]
        vehicle_counts = [item['vehicle_count'] for item in visit_counts]
        
        fig = px.bar(
            x=visit_groups,
            y=vehicle_counts,
            title='Vehicle Visit Patterns',
            labels={'x': 'Visit Group', 'y': 'Vehicle Count'},
            color=vehicle_counts,
            color_continuous_scale='Blues'
        )
        
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis_title='Visit Group',
            yaxis_title='Number of Vehicles'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def get_avg_stay_by_type_chart(self, organization=None):
        """Generate average stay by vehicle type chart"""
        from .models import ParkingRecord
        
        # Get filtered parking records
        parking_qs = ParkingRecord.objects.all()
        parking_qs = self._apply_filters(parking_qs)
        parking_qs = parking_qs.filter(parking_duration_minutes__gt=0)
        
        # Group by vehicle type and calculate average duration
        type_data = parking_qs.values('vehicle_type').annotate(
            avg_stay_min=Avg('parking_duration_minutes'),
            total_visits=Count('id')
        ).order_by('-avg_stay_min')
        
        if not type_data:
            return json.dumps({}, cls=PlotlyJSONEncoder)
        
        # Prepare data for plotting
        vehicle_types = [item['vehicle_type'] for item in type_data]
        avg_stays = [float(item['avg_stay_min'] or 0) for item in type_data]
        
        fig = px.bar(
            x=vehicle_types,
            y=avg_stays,
            title='Average Stay Duration by Vehicle Type',
            labels={'x': 'Vehicle Type', 'y': 'Average Stay (Minutes)'},
            color=avg_stays,
            color_continuous_scale='Oranges'
        )
        
        fig.update_layout(
            height=400,
            showlegend=False,
            xaxis_title='Vehicle Type',
            yaxis_title='Average Stay (Minutes)'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    

    def get_route_analysis(self, days=30):
        """Analyze most frequent routes"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Use Django ORM
        movements_qs = VehicleMovement.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            trip_status='completed'
        )
        
        if self.organization:
            movements_qs = movements_qs.filter(vehicle__organization=self.organization)
        
        # Group by route and aggregate
        route_data = movements_qs.values(
            'start_location', 'end_location'
        ).annotate(
            frequency=Count('id'),
            avg_duration=Avg('duration_minutes')
        ).filter(frequency__gt=1).order_by('-frequency')[:20]
        
        # Convert to list and add route field
        routes = []
        for item in route_data:
            route_info = {
                'start_location': item['start_location'],
                'end_location': item['end_location'],
                'frequency': item['frequency'],
                'avg_duration': float(item['avg_duration'] or 0),
                'route': f"{item['start_location']} → {item['end_location']}"
            }
            routes.append(route_info)
        
        return routes
    
    def get_driver_performance(self, days=30):
        """Get driver performance analytics"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Use Django ORM - note: driver field might be null for parking data
        movements_qs = VehicleMovement.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            trip_status='completed',
            driver__isnull=False  # Only movements with drivers
        )
        
        if self.organization:
            movements_qs = movements_qs.filter(vehicle__organization=self.organization)
        
        # Group by driver and aggregate
        driver_data = movements_qs.values(
            'driver__first_name', 'driver__last_name', 'driver__username'
        ).annotate(
            total_trips=Count('id'),
            total_duration=Sum('duration_minutes'),
            avg_duration=Avg('duration_minutes')
        ).order_by('-total_trips')
        
        # Convert to list and add calculated fields
        drivers = []
        for item in driver_data:
            driver_info = {
                'first_name': item['driver__first_name'] or '',
                'last_name': item['driver__last_name'] or '',
                'username': item['driver__username'] or '',
                'total_trips': item['total_trips'],
                'total_duration': float(item['total_duration'] or 0),
                'avg_duration': float(item['avg_duration'] or 0),
                'driver_name': f"{item['driver__first_name'] or ''} {item['driver__last_name'] or ''}".strip()
            }
            drivers.append(driver_info)
        
        return drivers
    
    def get_cost_analysis(self, days=30):
        """Analyze fleet costs"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get fuel transactions if they exist
        fuel_cost = 0
        try:
            fuel_transactions = FuelTransaction.objects.filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date,
                transaction_type='purchase'
            )
            if self.organization:
                fuel_transactions = fuel_transactions.filter(vehicle__organization=self.organization)
            
            fuel_cost = fuel_transactions.aggregate(Sum('total_cost'))['total_cost__sum'] or 0
        except:
            fuel_cost = 0
        
        # Get trip-based costs from movements
        movements_qs = VehicleMovement.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            trip_status='completed'
        )
        
        if self.organization:
            movements_qs = movements_qs.filter(vehicle__organization=self.organization)
        
        trip_data = movements_qs.aggregate(
            trip_fuel_cost=Sum('fuel_cost'),
            total_trips=Count('id')
        )
        
        trip_fuel_cost = float(trip_data['trip_fuel_cost'] or 0)
        total_trips = int(trip_data['total_trips'] or 0)
        
        return {
            'fuel_cost': float(fuel_cost),
            'trip_fuel_cost': trip_fuel_cost,
            'total_trips': total_trips,
            'cost_per_trip': float(fuel_cost / total_trips) if total_trips > 0 else 0
        }
    
    def get_analytics_summary(self, organization=None):
        """Get complete analytics summary"""
        return {
            'fleet_summary': self.get_fleet_summary(),
            'parking_duration_chart': self.get_parking_duration_chart(),
            'hourly_entries_chart': self.get_hourly_entries_chart(organization),
            'vehicles_per_site_chart': self.get_vehicles_per_site_chart(organization),
            'revenue_per_site_chart': self.get_revenue_per_site_chart(organization),
            'visit_patterns_chart': self.get_visit_patterns_chart(organization),
            'avg_stay_by_type_chart': self.get_avg_stay_by_type_chart(organization),
            'route_analysis': self.get_route_analysis(),
            'driver_performance': self.get_driver_performance(),
            'cost_analysis': self.get_cost_analysis()
        }


def generate_sample_data(organization):
    """Generate sample vehicle data for testing"""
    from random import randint, uniform, choice
    from datetime import datetime, timedelta
    import uuid
    
    # Create sample vehicles
    makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan']
    models = ['Camry', 'Civic', 'F-150', 'Silverado', 'Altima']
    fuel_types = ['gasoline', 'diesel', 'hybrid']
    
    vehicles = []
    for i in range(10):
        vehicle = Vehicle.objects.create(
            vehicle_id=f"VH{str(i+1).zfill(3)}",
            make=choice(makes),
            model=choice(models),
            year=randint(2018, 2024),
            vin=f"1HGBH41JXMN{str(randint(100000, 999999))}",
            license_plate=f"ABC{str(randint(1000, 9999))}",
            fuel_type=choice(fuel_types),
            organization=organization
        )
        vehicles.append(vehicle)
    
    # Create sample movements
    locations = [
        'Downtown Office', 'Warehouse District', 'Airport', 'Shopping Mall',
        'Industrial Park', 'City Center', 'Suburbs', 'Port Area'
    ]
    
    users = list(CustomUser.objects.filter(organization=organization))
    
    for _ in range(500):  # 500 sample trips
        vehicle = choice(vehicles)
        driver = choice(users) if users else None
        start_time = datetime.now() - timedelta(days=randint(1, 30), hours=randint(0, 23))
        duration = randint(15, 180)  # 15 minutes to 3 hours
        distance = uniform(5, 150)  # 5 to 150 km
        
        VehicleMovement.objects.create(
            vehicle=vehicle,
            driver=driver,
            trip_id=str(uuid.uuid4())[:8],
            start_location=choice(locations),
            end_location=choice(locations),
            start_latitude=uniform(40.0, 41.0),
            start_longitude=uniform(-74.0, -73.0),
            end_latitude=uniform(40.0, 41.0),
            end_longitude=uniform(-74.0, -73.0),
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration),
            duration_minutes=duration,
            distance_km=distance,
            fuel_consumed_liters=distance * uniform(0.08, 0.15),  # 8-15L/100km
            fuel_cost=distance * uniform(0.08, 0.15) * uniform(1.2, 1.8),  # fuel price
            average_speed_kmh=distance / (duration / 60),
            max_speed_kmh=uniform(60, 120)
        )
    
    return f"Generated sample data: {len(vehicles)} vehicles, 500 trips"