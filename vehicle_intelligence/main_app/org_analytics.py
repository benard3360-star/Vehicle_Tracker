from django.db import connection
import json
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

class OrgAnalytics:
    """Organization-specific analytics for admin dashboard with Plotly visualizations"""
    
    @staticmethod
    def _build_filter_conditions(organization_name, filters=None):
        """Helper method to build WHERE conditions and parameters for filters"""
        where_conditions = []
        params = []
        
        # Organization filter
        where_conditions.append("(organization = %s OR organization ILIKE %s)")
        params.extend([organization_name, f'%{organization_name.split()[0]}%'])
        
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
        
        return " AND ".join(where_conditions), params
    
    @staticmethod
    def get_filter_options(organization_name):
        """Get available filter options from the dataset for the organization"""
        try:
            with connection.cursor() as cursor:
                filters = {}
                
                # Get months
                cursor.execute("""
                    SELECT DISTINCT EXTRACT(MONTH FROM entry_time) as month
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND entry_time IS NOT NULL
                    ORDER BY month
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['months'] = [{'value': int(row[0]), 'label': datetime(2024, int(row[0]), 1).strftime('%B')} for row in cursor.fetchall() if row[0]]
                
                # Get vehicle types
                cursor.execute("""
                    SELECT DISTINCT vehicle_type
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND vehicle_type IS NOT NULL
                    ORDER BY vehicle_type
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['vehicle_types'] = [row[0] for row in cursor.fetchall()]
                
                # Get vehicle brands
                cursor.execute("""
                    SELECT DISTINCT vehicle_brand
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND vehicle_brand IS NOT NULL
                    ORDER BY vehicle_brand
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['vehicle_brands'] = [row[0] for row in cursor.fetchall()]
                
                # Get payment methods
                cursor.execute("""
                    SELECT DISTINCT payment_method
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND payment_method IS NOT NULL
                    ORDER BY payment_method
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['payment_methods'] = [row[0] for row in cursor.fetchall()]
                
                # Get plate colors
                cursor.execute("""
                    SELECT DISTINCT plate_color
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND plate_color IS NOT NULL
                    ORDER BY plate_color
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['plate_colors'] = [row[0] for row in cursor.fetchall()]
                
                # Get years
                cursor.execute("""
                    SELECT DISTINCT EXTRACT(YEAR FROM entry_time) as year
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND entry_time IS NOT NULL
                    ORDER BY year DESC
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                filters['years'] = [int(row[0]) for row in cursor.fetchall() if row[0]]
                
                return filters
        except Exception as e:
            print(f"Error getting filter options: {e}")
            return {
                'months': [],
                'vehicle_types': [],
                'vehicle_brands': [],
                'payment_methods': [],
                'plate_colors': [],
                'years': []
            }
    
    @staticmethod
    def get_org_parking_duration_analysis(organization_name, filters=None):
        """Get parking duration analysis for specific organization using duration_minutes column"""
        try:
            with connection.cursor() as cursor:
                # Use duration_minutes column if available, otherwise calculate
                cursor.execute("""
                    SELECT 
                        duration_category,
                        COUNT(*) as visit_count,
                        AVG(duration_minutes) as avg_minutes
                    FROM (
                        SELECT 
                            CASE 
                                WHEN duration_minutes <= 30 THEN 'Short (≤30 min)'
                                WHEN duration_minutes <= 120 THEN 'Medium (30-120 min)'
                                WHEN duration_minutes <= 480 THEN 'Long (2-8 hours)'
                                ELSE 'Extended (>8 hours)'
                            END as duration_category,
                            duration_minutes
                        FROM real_movement_analytics 
                        WHERE duration_minutes IS NOT NULL AND duration_minutes > 0
                        AND (organization = %s OR organization ILIKE %s)
                    ) categorized
                    GROUP BY duration_category
                    ORDER BY 
                        CASE duration_category
                            WHEN 'Short (≤30 min)' THEN 1
                            WHEN 'Medium (30-120 min)' THEN 2
                            WHEN 'Long (2-8 hours)' THEN 3
                            ELSE 4
                        END
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No parking duration data available'}})
                
                categories = [row[0] for row in results]
                counts = [row[1] for row in results]
                avg_durations = [round(row[2], 1) for row in results]
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=categories,
                    y=counts,
                    name='Visit Count',
                    marker_color=['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'],
                    hovertemplate='<b>%{x}</b><br>Visits: %{y}<br>Avg Duration: %{customdata:.1f} min<extra></extra>',
                    customdata=avg_durations
                ))
                
                fig.update_layout(
                    title=f'Parking Duration Analysis - {organization_name}',
                    xaxis_title='Duration Category',
                    yaxis_title='Number of Visits',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_parking_duration_analysis: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_hourly_entries_chart(organization_name, filters=None):
        """Get hourly vehicle entries for specific organization showing peak time analysis"""
        try:
            with connection.cursor() as cursor:
                # Build WHERE clause with filters
                where_clause, params = OrgAnalytics._build_filter_conditions(organization_name, filters)
                
                # Extract hour from entry_time and count entries for specific organization
                cursor.execute(f"""
                    SELECT 
                        EXTRACT(HOUR FROM entry_time) as hour,
                        COUNT(*) as entry_count
                    FROM real_movement_analytics 
                    WHERE entry_time IS NOT NULL
                    AND {where_clause}
                    GROUP BY EXTRACT(HOUR FROM entry_time)
                    ORDER BY hour
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
                    hovertemplate='<b>%{x}</b><br>Entries: %{y}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Peak Time Analysis - {organization_name}',
                    xaxis_title='Hour of Day',
                    yaxis_title='Number of Entries',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_hourly_entries_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_vehicles_count_chart(organization_name, filters=None):
        """Get number of vehicles that visited this particular organization"""
        try:
            with connection.cursor() as cursor:
                # Get vehicle count and visit statistics for the organization
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT plate_number) as unique_vehicles,
                        COUNT(*) as total_visits,
                        AVG(amount_paid) as avg_amount,
                        SUM(amount_paid) as total_revenue
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND plate_number IS NOT NULL
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                result = cursor.fetchone()
                if not result or result[0] == 0:
                    return json.dumps({'data': [], 'layout': {'title': 'No vehicle data available'}})
                
                unique_vehicles = result[0]
                total_visits = result[1]
                avg_amount = float(result[2] or 0)
                total_revenue = float(result[3] or 0)
                
                # Create a simple metric display
                fig = go.Figure()
                
                # Add gauge chart for vehicle count
                fig.add_trace(go.Indicator(
                    mode="gauge+number",
                    value=unique_vehicles,
                    domain={'x': [0, 1], 'y': [0, 1]},
                    title={'text': f"Vehicles Visited {organization_name}"},
                    gauge={
                        'axis': {'range': [None, max(100, unique_vehicles * 1.2)]},
                        'bar': {'color': "#16a34a"},
                        'steps': [
                            {'range': [0, unique_vehicles * 0.5], 'color': "lightgray"},
                            {'range': [unique_vehicles * 0.5, unique_vehicles], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': unique_vehicles * 0.9
                        }
                    }
                ))
                
                fig.update_layout(
                    height=300,
                    margin=dict(l=40, r=40, t=60, b=40),
                    annotations=[
                        dict(
                            text=f"Total Visits: {total_visits}",
                            x=0.5, y=0.25,
                            showarrow=False,
                            font=dict(size=14)
                        ),
                        dict(
                            text=f"Avg Amount: KSh {avg_amount:.0f}",
                            x=0.5, y=0.1,
                            showarrow=False,
                            font=dict(size=14)
                        )
                    ]
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_vehicles_count_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_revenue_analysis_chart(organization_name, filters=None):
        """Get revenue analysis showing total amount paid by all vehicles in this organization"""
        try:
            with connection.cursor() as cursor:
                # Get revenue breakdown by time periods
                cursor.execute("""
                    SELECT 
                        DATE_TRUNC('month', entry_time) as month,
                        SUM(amount_paid) as monthly_revenue,
                        COUNT(*) as monthly_visits,
                        COUNT(DISTINCT plate_number) as monthly_vehicles
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND amount_paid IS NOT NULL
                    AND entry_time >= CURRENT_DATE - INTERVAL '12 months'
                    GROUP BY DATE_TRUNC('month', entry_time)
                    ORDER BY month
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No revenue data available'}})
                
                months = [row[0].strftime('%b %Y') for row in results]
                revenues = [float(row[1]) for row in results]
                visits = [row[2] for row in results]
                vehicles = [row[3] for row in results]
                
                fig = go.Figure()
                
                # Add bar chart for revenue
                fig.add_trace(go.Bar(
                    x=months,
                    y=revenues,
                    name='Monthly Revenue',
                    marker_color='#16a34a',
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Revenue: KSh %{y:,.0f}<br>' +
                                 'Visits: %{customdata[0]}<br>' +
                                 'Vehicles: %{customdata[1]}<extra></extra>',
                    customdata=list(zip(visits, vehicles))
                ))
                
                fig.update_layout(
                    title=f'Revenue Analysis - {organization_name}',
                    xaxis_title='Month',
                    yaxis_title='Revenue (KSh)',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_revenue_analysis_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_avg_stay_by_type_chart(organization_name, filters=None):
        """Get average stay by vehicle type for specific organization comparing parking duration (exit_time - entry_time)"""
        try:
            with connection.cursor() as cursor:
                # Calculate average parking duration by vehicle type for specific organization
                cursor.execute("""
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
                    AND (organization = %s OR organization ILIKE %s)
                    GROUP BY vehicle_type
                    HAVING COUNT(*) >= 3  -- At least 3 visits for meaningful average
                    ORDER BY avg_duration_minutes DESC
                    LIMIT 10
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No vehicle type duration data available'}})
                
                vehicle_types = [row[0] for row in results]
                avg_durations = [round(row[1], 1) for row in results]
                visit_counts = [row[2] for row in results]
                min_durations = [round(row[3], 1) for row in results]
                max_durations = [round(row[4], 1) for row in results]
                
                fig = go.Figure()
                
                # Add bar chart
                # Create colorful bar chart
                colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
                
                fig.add_trace(go.Bar(
                    x=vehicle_types,
                    y=avg_durations,
                    name='Average Duration',
                    marker_color=colors[:len(vehicle_types)],
                    hovertemplate='<b>%{x}</b><br>' +
                                 'Avg Duration: %{y:.1f} minutes<br>' +
                                 'Visits: %{customdata[0]}<br>' +
                                 'Min: %{customdata[1]:.1f} min<br>' +
                                 'Max: %{customdata[2]:.1f} min<extra></extra>',
                    customdata=list(zip(visit_counts, min_durations, max_durations))
                ))
                
                fig.update_layout(
                    title=f'Average Stay by Vehicle Type - {organization_name}',
                    xaxis_title='Vehicle Type',
                    yaxis_title='Average Duration (minutes)',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis={'tickangle': -45},
                    margin=dict(l=40, r=40, t=60, b=60)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_avg_stay_by_type_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_capacity_utilization_chart(organization_name, filters=None):
        """Get capacity utilization showing peak vs off-peak usage"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 7 AND 9 THEN 'Morning Peak (7-9 AM)'
                            WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 17 AND 19 THEN 'Evening Peak (5-7 PM)'
                            WHEN EXTRACT(HOUR FROM entry_time) BETWEEN 10 AND 16 THEN 'Midday (10 AM-4 PM)'
                            ELSE 'Off-Peak Hours'
                        END as time_period,
                        COUNT(*) as visit_count,
                        AVG(amount_paid) as avg_revenue
                    FROM real_movement_analytics 
                    WHERE entry_time IS NOT NULL
                    AND (organization = %s OR organization ILIKE %s)
                    GROUP BY time_period
                    ORDER BY visit_count DESC
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No capacity data available'}})
                
                periods = [row[0] for row in results]
                counts = [row[1] for row in results]
                revenues = [float(row[2] or 0) for row in results]
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=periods,
                    y=counts,
                    name='Visits',
                    marker_color=['#ef4444', '#f59e0b', '#3b82f6', '#6b7280'],
                    hovertemplate='<b>%{x}</b><br>Visits: %{y}<br>Avg Revenue: KSh %{customdata:.0f}<extra></extra>',
                    customdata=revenues
                ))
                
                fig.update_layout(
                    title=f'Capacity Utilization - {organization_name}',
                    xaxis_title='Time Period',
                    yaxis_title='Number of Visits',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=60)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_capacity_utilization_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_customer_loyalty_chart(organization_name, filters=None):
        """Get customer loyalty analysis showing repeat vs new visitors"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        plate_number,
                        COUNT(*) as visit_count,
                        SUM(amount_paid) as total_spent
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND amount_paid IS NOT NULL
                    GROUP BY plate_number
                    ORDER BY visit_count DESC
                    LIMIT 20
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No customer data available'}})
                
                plates = [row[0][:8] + '...' if len(row[0]) > 8 else row[0] for row in results]
                visits = [row[1] for row in results]
                spent = [float(row[2]) for row in results]
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=visits,
                    y=spent,
                    mode='markers',
                    marker=dict(
                        size=[min(40, v*2) for v in visits],
                        color=visits,
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title='Visits')
                    ),
                    text=plates,
                    hovertemplate='<b>%{text}</b><br>Visits: %{x}<br>Total Spent: KSh %{y:,.0f}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Top 20 Customers by Loyalty - {organization_name}',
                    xaxis_title='Number of Visits',
                    yaxis_title='Total Amount Spent (KSh)',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_customer_loyalty_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_revenue_trends_chart(organization_name, filters=None):
        """Get revenue trends over the last 6 months with growth indicators"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        DATE_TRUNC('week', entry_time) as week,
                        SUM(amount_paid) as weekly_revenue,
                        COUNT(*) as weekly_visits,
                        COUNT(DISTINCT plate_number) as unique_customers
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND entry_time >= CURRENT_DATE - INTERVAL '12 weeks'
                    AND amount_paid IS NOT NULL
                    GROUP BY DATE_TRUNC('week', entry_time)
                    ORDER BY week
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No revenue trend data available'}})
                
                weeks = [row[0].strftime('%b %d') for row in results]
                revenues = [float(row[1]) for row in results]
                visits = [row[2] for row in results]
                customers = [row[3] for row in results]
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=weeks,
                    y=revenues,
                    mode='lines+markers',
                    name='Weekly Revenue',
                    line=dict(color='#16a34a', width=3),
                    marker=dict(size=8),
                    hovertemplate='<b>Week of %{x}</b><br>Revenue: KSh %{y:,.0f}<br>Visits: %{customdata[0]}<br>Customers: %{customdata[1]}<extra></extra>',
                    customdata=list(zip(visits, customers))
                ))
                
                fig.update_layout(
                    title=f'Revenue Trends (12 weeks) - {organization_name}',
                    xaxis_title='Week',
                    yaxis_title='Revenue (KSh)',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_revenue_trends_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_payment_behavior_chart(organization_name, filters=None):
        """Get payment methods analysis showing comparison of payment methods with total amounts"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                # Check if payment_method column exists
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'real_movement_analytics' AND column_name = 'payment_method'
                """)
                has_payment_method = cursor.fetchone() is not None
                
                if has_payment_method:
                    cursor.execute("""
                        SELECT 
                            COALESCE(payment_method, 'Cash') as method,
                            COUNT(*) as transaction_count,
                            SUM(amount_paid) as total_amount,
                            AVG(amount_paid) as avg_amount
                        FROM real_movement_analytics 
                        WHERE (organization = %s OR organization ILIKE %s)
                        AND amount_paid IS NOT NULL AND amount_paid > 0
                        GROUP BY payment_method
                        ORDER BY total_amount DESC
                    """, [organization_name, f'%{organization_name.split()[0]}%'])
                else:
                    # Simulate payment methods based on amount ranges
                    cursor.execute("""
                        SELECT 
                            CASE 
                                WHEN amount_paid <= 100 THEN 'Cash'
                                WHEN amount_paid <= 500 THEN 'Mobile Money'
                                ELSE 'Card Payment'
                            END as method,
                            COUNT(*) as transaction_count,
                            SUM(amount_paid) as total_amount,
                            AVG(amount_paid) as avg_amount
                        FROM real_movement_analytics 
                        WHERE (organization = %s OR organization ILIKE %s)
                        AND amount_paid IS NOT NULL AND amount_paid > 0
                        GROUP BY method
                        ORDER BY total_amount DESC
                    """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No payment data available'}})
                
                methods = [row[0] for row in results]
                counts = [row[1] for row in results]
                amounts = [float(row[2]) for row in results]
                avg_amounts = [float(row[3]) for row in results]
                
                fig = go.Figure()
                
                # Create pie chart for payment methods
                fig = go.Figure()
                
                fig.add_trace(go.Pie(
                    labels=methods,
                    values=amounts,
                    hole=0.3,
                    marker_colors=['#16a34a', '#3b82f6', '#f59e0b', '#ef4444'],
                    hovertemplate='<b>%{label}</b><br>Amount: KSh %{value:,.0f}<br>Percentage: %{percent}<br>Transactions: %{customdata}<extra></extra>',
                    customdata=counts,
                    textinfo='percent',
                    texttemplate='%{percent}'
                ))
                
                fig.update_layout(
                    title=f'Payment Methods Analysis - {organization_name}',
                    height=350,
                    showlegend=True,
                    legend=dict(
                        orientation="v", 
                        yanchor="middle", 
                        y=0.5, 
                        xanchor="left", 
                        x=1.05,
                        font=dict(size=10)
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=120, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_payment_behavior_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_vehicle_brand_performance_chart(organization_name):
        """Get vehicle brand performance showing which brands generate most revenue"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COALESCE(vehicle_brand, 'Unknown') as brand,
                        COUNT(*) as visits,
                        SUM(amount_paid) as total_revenue,
                        AVG(amount_paid) as avg_payment,
                        COUNT(DISTINCT plate_number) as unique_vehicles
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND amount_paid IS NOT NULL
                    GROUP BY vehicle_brand
                    HAVING COUNT(*) >= 5
                    ORDER BY total_revenue DESC
                    LIMIT 10
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No vehicle brand data available'}})
                
                brands = [row[0] for row in results]
                visits = [row[1] for row in results]
                revenues = [float(row[2]) for row in results]
                avg_payments = [float(row[3]) for row in results]
                vehicles = [row[4] for row in results]
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=visits,
                    y=revenues,
                    mode='markers+text',
                    marker=dict(
                        size=[min(50, v*3) for v in vehicles],
                        color=avg_payments,
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title='Avg Payment')
                    ),
                    text=brands,
                    textposition='middle center',
                    hovertemplate='<b>%{text}</b><br>Visits: %{x}<br>Revenue: KSh %{y:,.0f}<br>Vehicles: %{customdata[0]}<br>Avg Payment: KSh %{customdata[1]:.0f}<extra></extra>',
                    customdata=list(zip(vehicles, avg_payments))
                ))
                
                fig.update_layout(
                    title=f'Vehicle Brand Performance - {organization_name}',
                    xaxis_title='Total Visits',
                    yaxis_title='Total Revenue (KSh)',
                    height=300,
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_vehicle_brand_performance_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })
    
    @staticmethod
    def get_org_seasonal_patterns_chart(organization_name):
        """Get seasonal patterns showing monthly trends with heatmap"""
        if not organization_name:
            return json.dumps({'data': [], 'layout': {'title': 'No organization specified'}})
            
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        EXTRACT(MONTH FROM entry_time) as month,
                        EXTRACT(HOUR FROM entry_time) as hour,
                        COUNT(*) as visit_count
                    FROM real_movement_analytics 
                    WHERE (organization = %s OR organization ILIKE %s)
                    AND entry_time >= CURRENT_DATE - INTERVAL '12 months'
                    GROUP BY EXTRACT(MONTH FROM entry_time), EXTRACT(HOUR FROM entry_time)
                    ORDER BY month, hour
                """, [organization_name, f'%{organization_name.split()[0]}%'])
                
                results = cursor.fetchall()
                if not results:
                    return json.dumps({'data': [], 'layout': {'title': 'No seasonal data available'}})
                
                # Create matrix for heatmap
                months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                hours = list(range(24))
                
                # Initialize matrix
                matrix = [[0 for _ in range(24)] for _ in range(12)]
                
                for row in results:
                    month_idx = int(row[0]) - 1
                    hour_idx = int(row[1])
                    count = row[2]
                    if 0 <= month_idx < 12 and 0 <= hour_idx < 24:
                        matrix[month_idx][hour_idx] = count
                
                fig = go.Figure()
                
                fig.add_trace(go.Heatmap(
                    z=matrix,
                    x=hours,
                    y=months,
                    colorscale='Viridis',
                    hoverongaps=False,
                    hovertemplate='<b>%{y} at %{x}:00</b><br>Visits: %{z}<extra></extra>'
                ))
                
                fig.update_layout(
                    title=f'Seasonal Activity Patterns - {organization_name}',
                    xaxis_title='Hour of Day',
                    yaxis_title='Month',
                    height=300,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                return json.dumps(fig, cls=PlotlyJSONEncoder)
                
        except Exception as e:
            print(f"Error in get_org_seasonal_patterns_chart: {e}")
            return json.dumps({
                'data': [{'x': ['Error'], 'y': [0], 'type': 'bar'}],
                'layout': {'title': f'Error loading data: {str(e)}'}
            })