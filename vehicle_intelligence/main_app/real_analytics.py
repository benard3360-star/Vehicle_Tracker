from django.db import connection
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

class RealAnalytics:
    """Enhanced analytics using real_movement_analytics data with Plotly visualizations"""
    
    @staticmethod
    def get_parking_duration_analysis(organization=None):
        """Get parking duration analysis using pre-calculated duration_minutes"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'AND organization = %s' if organization else ""
                params = [organization] if organization else []
                
                cursor.execute(f"""
                    SELECT 
                        duration_category,
                        COUNT(*) as visit_count,
                        AVG(duration_minutes) as avg_minutes
                    FROM real_movement_analytics 
                    WHERE duration_minutes IS NOT NULL
                    {where_clause}
                    GROUP BY duration_category
                    ORDER BY 
                        CASE duration_category
                            WHEN 'Short' THEN 1
                            WHEN 'Medium' THEN 2
                            WHEN 'Long' THEN 3
                            ELSE 4
                        END
                """, params)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No parking duration data available'}})
                
                categories = [row[0] for row in results]
                counts = [row[1] for row in results]
                avg_durations = [round(row[2], 1) for row in results]
                
                fig = go.Figure()
                
                # Add bar chart
                fig.add_trace(go.Bar(
                    x=categories,
                    y=counts,
                    name='Visit Count',
                    marker_color=['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'],
                    text=[f'{count}<br>Avg: {avg:.1f}min' for count, avg in zip(counts, avg_durations)],
                    textposition='auto'
                ))
                
                fig.update_layout(
                    title=f'Parking Duration Analysis{" - " + organization if organization else ""}',
                    xaxis_title='Duration Category',
                    yaxis_title='Number of Visits',
                    height=400,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_parking_duration_analysis: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_hourly_entries_chart(organization=None):
        """Get hourly vehicle entries showing peak time analysis"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE organization = %s' if organization else ""
                params = [organization] if organization else []
                
                # Extract hour from entry_time and count entries
                cursor.execute(f"""
                    SELECT 
                        hour_of_day,
                        COUNT(*) as entry_count
                    FROM real_movement_analytics 
                    WHERE hour_of_day IS NOT NULL
                    {where_clause}
                    GROUP BY hour_of_day
                    ORDER BY hour_of_day
                """, params)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No hourly entry data available'}})
                
                hours = [f"{int(row[0]):02d}:00" for row in results]
                counts = [row[1] for row in results]
                
                # Identify peak hours (top 3)
                peak_indices = sorted(range(len(counts)), key=lambda i: counts[i], reverse=True)[:3]
                colors = ['#ef4444' if i in peak_indices else '#16a34a' for i in range(len(counts))]
                
                fig = go.Figure()
                
                # Add line chart
                fig.add_trace(go.Scatter(
                    x=hours,
                    y=counts,
                    mode='lines+markers',
                    name='Vehicle Entries',
                    line=dict(color='#16a34a', width=3),
                    marker=dict(size=8, color=colors),
                    text=[f'{count} entries' for count in counts],
                    hovertemplate='<b>%{x}</b><br>Entries: %{y}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Hourly Vehicle Entries{" - " + organization if organization else ""}',
                    xaxis_title='Hour of Day',
                    yaxis_title='Number of Entries',
                    height=400,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_hourly_entries_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_vehicles_per_organization_chart():
        """Get vehicles that visited each organization"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        organization,
                        COUNT(DISTINCT plate_number) as vehicle_count
                    FROM real_movement_analytics 
                    WHERE organization IS NOT NULL
                    GROUP BY organization
                    ORDER BY vehicle_count DESC
                """)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No vehicle data available'}})
                
                organizations = [row[0] for row in results]
                counts = [row[1] for row in results]
                
                fig = go.Figure()
                
                # Add pie chart
                fig.add_trace(go.Pie(
                    labels=organizations,
                    values=counts,
                    hole=0.3,
                    marker_colors=['#16a34a', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'],
                    textinfo='label+percent+value',
                    textposition='outside',
                    hovertemplate='<b>%{label}</b><br>Vehicles: %{value}<br>Percentage: %{percent}<extra></extra>'
                ))
                
                fig.update_layout(
                    title='Vehicles that Visited Each Organization',
                    height=400,
                    showlegend=True,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_vehicles_per_organization_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_revenue_per_organization_chart():
        """Get revenue analysis showing total amount paid by all vehicles in each organization"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        organization,
                        SUM(amount_paid) as total_revenue,
                        COUNT(*) as visit_count,
                        COUNT(DISTINCT plate_number) as unique_vehicles,
                        AVG(amount_paid) as avg_amount
                    FROM real_movement_analytics 
                    WHERE organization IS NOT NULL AND amount_paid IS NOT NULL
                    GROUP BY organization
                    ORDER BY total_revenue DESC
                """)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No revenue data available'}})
                
                organizations = [row[0] for row in results]
                revenues = [float(row[1]) for row in results]
                visit_counts = [row[2] for row in results]
                unique_vehicles = [row[3] for row in results]
                avg_amounts = [float(row[4]) for row in results]
                
                fig = go.Figure()
                
                # Add bar chart
                fig.add_trace(go.Bar(
                    x=organizations,
                    y=revenues,
                    name='Total Revenue',
                    marker_color='#16a34a',
                    text=[f'KSh {rev:,.0f}' for rev in revenues],
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Total Revenue: KSh %{y:,.0f}<br>' +
                                 'Visits: %{customdata[0]}<br>' +
                                 'Unique Vehicles: %{customdata[1]}<br>' +
                                 'Avg Amount: KSh %{customdata[2]:.0f}<extra></extra>',
                    customdata=list(zip(visit_counts, unique_vehicles, avg_amounts))
                ))
                
                fig.update_layout(
                    title='Revenue Analysis by Organization',
                    xaxis_title='Organization',
                    yaxis_title='Total Revenue (KSh)',
                    height=400,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_revenue_per_organization_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_visit_patterns_chart(organization=None):
        """Get vehicle visit patterns by analyzing frequency and behavior"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE organization = %s' if organization else ""
                params = [organization] if organization else []
                
                # Analyze visit patterns by grouping vehicles by visit frequency
                cursor.execute(f"""
                    WITH vehicle_visits AS (
                        SELECT 
                            plate_number,
                            COUNT(*) as visit_count,
                            CASE 
                                WHEN COUNT(*) >= 50 THEN 'Frequent (50+ visits)'
                                WHEN COUNT(*) >= 20 THEN 'Regular (20-49 visits)'
                                WHEN COUNT(*) >= 5 THEN 'Occasional (5-19 visits)'
                                ELSE 'Rare (1-4 visits)'
                            END as visit_pattern
                        FROM real_movement_analytics 
                        {where_clause}
                        GROUP BY plate_number
                    )
                    SELECT 
                        visit_pattern,
                        COUNT(*) as vehicle_count
                    FROM vehicle_visits
                    GROUP BY visit_pattern
                    ORDER BY 
                        CASE visit_pattern
                            WHEN 'Frequent (50+ visits)' THEN 1
                            WHEN 'Regular (20-49 visits)' THEN 2
                            WHEN 'Occasional (5-19 visits)' THEN 3
                            ELSE 4
                        END
                """, params)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No visit pattern data available'}})
                
                patterns = [row[0] for row in results]
                counts = [row[1] for row in results]
                
                fig = go.Figure()
                
                # Add donut chart
                fig.add_trace(go.Pie(
                    labels=patterns,
                    values=counts,
                    hole=0.4,
                    marker_colors=['#ef4444', '#f59e0b', '#3b82f6', '#16a34a'],
                    textinfo='label+percent+value',
                    textposition='outside',
                    hovertemplate='<b>%{label}</b><br>Vehicles: %{value}<br>Percentage: %{percent}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Visit Patterns{" - " + organization if organization else ""}',
                    height=400,
                    showlegend=True,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_visit_patterns_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_avg_stay_by_type_chart(organization=None):
        """Get average stay by vehicle type comparing parking duration (exit_time - entry_time)"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE organization = %s' if organization else ""
                params = [organization] if organization else []
                
                # Calculate average parking duration by vehicle type
                cursor.execute(f"""
                    SELECT 
                        COALESCE(vehicle_type, 'Unknown') as vehicle_type,
                        AVG(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) as avg_duration_minutes,
                        COUNT(*) as visit_count,
                        MIN(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) as min_duration,
                        MAX(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) as max_duration
                    FROM real_movement_analytics 
                    WHERE exit_time IS NOT NULL AND entry_time IS NOT NULL
                    AND EXTRACT(EPOCH FROM (exit_time - entry_time))/60 > 0
                    AND EXTRACT(EPOCH FROM (exit_time - entry_time))/60 < 1440  -- Less than 24 hours
                    {where_clause}
                    GROUP BY vehicle_type
                    HAVING COUNT(*) >= 5  -- At least 5 visits for meaningful average
                    ORDER BY avg_duration_minutes DESC
                    LIMIT 15
                """, params)
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No vehicle type duration data available'}})
                
                vehicle_types = [row[0] for row in results]
                avg_durations = [round(row[1], 1) for row in results]
                visit_counts = [row[2] for row in results]
                min_durations = [round(row[3], 1) for row in results]
                max_durations = [round(row[4], 1) for row in results]
                
                fig = go.Figure()
                
                # Add bar chart with error bars showing min/max range
                fig.add_trace(go.Bar(
                    x=vehicle_types,
                    y=avg_durations,
                    name='Average Duration',
                    marker_color='#3b82f6',
                    text=[f'{dur:.1f} min<br>({count} visits)' for dur, count in zip(avg_durations, visit_counts)],
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Avg Duration: %{y:.1f} minutes<br>' +
                                 'Visits: %{customdata[0]}<br>' +
                                 'Min: %{customdata[1]:.1f} min<br>' +
                                 'Max: %{customdata[2]:.1f} min<extra></extra>',
                    customdata=list(zip(visit_counts, min_durations, max_durations))
                ))
                
                fig.update_layout(
                    title=f'Average Stay by Vehicle Type{" - " + organization if organization else ""}',
                    xaxis_title='Vehicle Type',
                    yaxis_title='Average Duration (minutes)',
                    height=400,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis={'tickangle': -45}
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_avg_stay_by_type_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_route_analysis(organization=None):
        """Get route analysis data for the organization"""
        try:
            with connection.cursor() as cursor:
                where_clause = 'WHERE organization = %s' if organization else ""
                params = [organization] if organization else []
                
                cursor.execute(f"""
                    SELECT 
                        organization,
                        COUNT(*) as frequency,
                        AVG(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) as avg_duration,
                        AVG(amount_paid) as avg_cost,
                        SUM(amount_paid) as total_revenue
                    FROM real_movement_analytics 
                    WHERE exit_time IS NOT NULL AND entry_time IS NOT NULL
                    {where_clause}
                    GROUP BY organization
                    ORDER BY frequency DESC
                    LIMIT 10
                """, params)
                
                results = cursor.fetchall()
                return [{
                    'route': org or 'Unknown',
                    'frequency': freq,
                    'avg_duration': float(duration or 0),
                    'avg_cost': float(cost or 0),
                    'total_revenue': float(revenue or 0),
                    'avg_distance': 0,  # Not available in parking data
                    'total_fuel': 0     # Not available in parking data
                } for org, freq, duration, cost, revenue in results]
        except Exception as e:
            print(f"Error in get_route_analysis: {e}")
            return []
    
    @staticmethod
    def get_fleet_summary(organization=None, filters=None):
        """Get comprehensive fleet summary for specific organization"""
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause properly
                where_conditions = ["exit_time IS NOT NULL AND entry_time IS NOT NULL"]
                params = []
                
                if organization:
                    where_conditions.append("organization = %s")
                    params.append(organization)
                
                # Apply additional filters
                if filters:
                    if filters.get('month'):
                        where_conditions.append("EXTRACT(MONTH FROM entry_time) = %s")
                        params.append(int(filters['month']))
                    if filters.get('vehicle_type'):
                        where_conditions.append("vehicle_type = %s")
                        params.append(filters['vehicle_type'])
                    if filters.get('vehicle_brand'):
                        where_conditions.append("vehicle_brand = %s")
                        params.append(filters['vehicle_brand'])
                    if filters.get('payment_method'):
                        where_conditions.append("payment_method = %s")
                        params.append(filters['payment_method'])
                    if filters.get('plate_color'):
                        where_conditions.append("plate_color = %s")
                        params.append(filters['plate_color'])
                    if filters.get('year'):
                        where_conditions.append("EXTRACT(YEAR FROM entry_time) = %s")
                        params.append(int(filters['year']))
                
                where_clause = " AND ".join(where_conditions)
                
                cursor.execute(f"""
                    SELECT 
                        COUNT(DISTINCT plate_number) as total_vehicles,
                        COUNT(*) as total_visits,
                        SUM(amount_paid) as total_revenue,
                        AVG(EXTRACT(EPOCH FROM (exit_time - entry_time))/60) as avg_duration_minutes,
                        COUNT(CASE WHEN entry_time >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as recent_visits
                    FROM real_movement_analytics 
                    WHERE {where_clause}
                """, params)
                
                result = cursor.fetchone()
                
                if result:
                    total_vehicles = result[0] or 0
                    total_visits = result[1] or 0
                    total_revenue = float(result[2] or 0)
                    avg_duration = float(result[3] or 0)
                    recent_visits = result[4] or 0
                    
                    # Calculate utilization rate based on recent activity
                    utilization_rate = min(100, (recent_visits / max(1, total_vehicles)) * 2) if total_vehicles > 0 else 0
                    
                    return {
                        'total_vehicles': total_vehicles,
                        'total_visits': total_visits,
                        'total_revenue': total_revenue,
                        'avg_parking_duration': round(avg_duration, 1),
                        'utilization_rate': round(utilization_rate, 1),
                        'active_vehicles': total_vehicles,
                        'recent_visits': recent_visits
                    }
                return {
                    'total_vehicles': 0,
                    'total_visits': 0,
                    'total_revenue': 0,
                    'avg_parking_duration': 0,
                    'utilization_rate': 0,
                    'active_vehicles': 0,
                    'recent_visits': 0
                }
        except Exception as e:
            print(f"Error in get_fleet_summary: {e}")
            return {
                'total_vehicles': 0,
                'total_visits': 0,
                'total_revenue': 0,
                'avg_parking_duration': 0,
                'utilization_rate': 0,
                'active_vehicles': 0,
                'recent_visits': 0
            }
    
    @staticmethod
    def get_route_analysis(organization=None):
        """Get route analysis data"""
        with connection.cursor() as cursor:
            where_clause = 'WHERE organization ILIKE %s' if organization else ""
            params = [f'%{organization.split()[0]}%'] if organization else []
            
            cursor.execute(f"""
                SELECT 
                    organization,
                    COUNT(*) as frequency,
                    AVG(duration_minutes) as avg_duration,
                    AVG(amount_paid) as avg_cost
                FROM real_movement_analytics 
                {where_clause}
                GROUP BY organization
                ORDER BY frequency DESC
                LIMIT 10
            """, params)
            
            results = cursor.fetchall()
            return [{
                'route': org,
                'frequency': freq,
                'avg_duration': float(duration),
                'avg_cost': float(cost)
            } for org, freq, duration, cost in results]