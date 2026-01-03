import json
from django.db import connection
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

class SimpleCharts:
    """Simple chart generation using combined_dataset table"""
    
    @staticmethod
    def get_simple_parking_duration_chart(org_name=None):
        """Generate simple parking duration chart"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE "Organization" = %s' if org_name else ''
                params = [org_name] if org_name else []
                
                cursor.execute(f'''
                    SELECT 
                        "Vehicle Type",
                        COUNT(*) as count
                    FROM combined_dataset 
                    {where_clause}
                    GROUP BY "Vehicle Type"
                    ORDER BY count DESC
                    LIMIT 10
                ''', params)
                
                results = cursor.fetchall()
                if not results:
                    return None
                
                types = [row[0] or 'Unknown' for row in results]
                counts = [row[1] for row in results]
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=types,
                    y=counts,
                    marker_color='#16a34a',
                    text=counts,
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title=f'Vehicle Types Distribution{" - " + org_name if org_name else ""}',
                    xaxis_title='Vehicle Type',
                    yaxis_title='Count',
                    height=300
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
        except Exception as e:
            print(f"Error in simple parking duration chart: {e}")
            return None
    
    @staticmethod
    def get_simple_hourly_chart(org_name=None):
        """Generate simple hourly chart"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE "Organization" = %s' if org_name else ''
                params = [org_name] if org_name else []
                
                cursor.execute(f'''
                    SELECT 
                        "Vehicle Brand",
                        COUNT(*) as count
                    FROM combined_dataset 
                    {where_clause}
                    GROUP BY "Vehicle Brand"
                    ORDER BY count DESC
                    LIMIT 10
                ''', params)
                
                results = cursor.fetchall()
                if not results:
                    return None
                
                brands = [row[0] or 'Unknown' for row in results]
                counts = [row[1] for row in results]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=brands,
                    y=counts,
                    mode='lines+markers',
                    marker_color='#3b82f6',
                    line=dict(width=3)
                ))
                
                fig.update_layout(
                    title=f'Vehicle Brands Distribution{" - " + org_name if org_name else ""}',
                    xaxis_title='Vehicle Brand',
                    yaxis_title='Count',
                    height=300
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
        except Exception as e:
            print(f"Error in simple hourly chart: {e}")
            return None
    
    @staticmethod
    def get_simple_vehicles_per_org_chart():
        """Generate simple vehicles per organization chart"""
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT 
                        "Organization",
                        COUNT(DISTINCT "Plate Number") as vehicle_count
                    FROM combined_dataset 
                    WHERE "Organization" IS NOT NULL
                    GROUP BY "Organization"
                    ORDER BY vehicle_count DESC
                ''')
                
                results = cursor.fetchall()
                if not results:
                    return None
                
                orgs = [row[0] for row in results]
                counts = [row[1] for row in results]
                
                fig = go.Figure()
                fig.add_trace(go.Pie(
                    labels=orgs,
                    values=counts,
                    hole=0.3,
                    marker_colors=['#16a34a', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']
                ))
                
                fig.update_layout(
                    title='Vehicles per Organization',
                    height=300
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
        except Exception as e:
            print(f"Error in simple vehicles per org chart: {e}")
            return None
    
    @staticmethod
    def get_simple_revenue_chart():
        """Generate simple revenue chart"""
        try:
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT 
                        "Organization",
                        SUM("Amount Paid") as total_revenue
                    FROM combined_dataset 
                    WHERE "Organization" IS NOT NULL AND "Amount Paid" IS NOT NULL
                    GROUP BY "Organization"
                    ORDER BY total_revenue DESC
                ''')
                
                results = cursor.fetchall()
                if not results:
                    return None
                
                orgs = [row[0] for row in results]
                revenues = [float(row[1]) for row in results]
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=orgs,
                    y=revenues,
                    marker_color='#16a34a',
                    text=[f'KSh {rev:,.0f}' for rev in revenues],
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title='Revenue by Organization',
                    xaxis_title='Organization',
                    yaxis_title='Total Revenue (KSh)',
                    height=300
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
        except Exception as e:
            print(f"Error in simple revenue chart: {e}")
            return None