# ai_assistant.py
import json
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from .models import ParkingRecord, Organization, CustomUser
from django.db.models import Count, Sum, Avg, Q
from datetime import datetime, timedelta
import logging

# Optional OpenAI import
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIAssistant:
    def __init__(self):
        # Initialize OpenAI client when API key is available
        self.client = None
        if OPENAI_AVAILABLE and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai

    def get_context_data(self, user, page_type, filters=None):
        """Get relevant data context for AI analysis"""
        context = {
            'user_role': user.role,
            'organization': user.organization.name if user.organization else 'System',
            'page_type': page_type,
            'timestamp': datetime.now().isoformat()
        }
        
        if page_type == 'analytics':
            context.update(self._get_analytics_context(user, filters))
        elif page_type == 'vehicle_alert':
            context.update(self._get_vehicle_context(user, filters))
        elif page_type == 'dashboard' or page_type == 'org_admin_dashboard':
            context.update(self._get_dashboard_context(user))
            
        return context

    def _get_analytics_context(self, user, filters):
        """Get analytics-specific context"""
        queryset = ParkingRecord.objects.all()
        
        if user.role != 'super_admin' and user.organization:
            queryset = queryset.filter(organization=user.organization)
            
        if filters:
            if filters.get('organization'):
                queryset = queryset.filter(organization_id=filters['organization'])
            if filters.get('vehicle_brand'):
                queryset = queryset.filter(vehicle_brand=filters['vehicle_brand'])
            if filters.get('vehicle_type'):
                queryset = queryset.filter(vehicle_type=filters['vehicle_type'])
        
        # Calculate key metrics
        total_vehicles = queryset.values('license_plate').distinct().count()
        total_revenue = queryset.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        avg_duration = queryset.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0
        
        # Get top organizations
        top_orgs = queryset.values('organization__name').annotate(
            vehicle_count=Count('license_plate', distinct=True),
            total_revenue=Sum('amount_paid')
        ).order_by('-total_revenue')[:5]
        
        return {
            'total_vehicles': total_vehicles,
            'total_revenue': float(total_revenue),
            'avg_duration': float(avg_duration),
            'top_organizations': list(top_orgs),
            'record_count': queryset.count()
        }

    def _get_vehicle_context(self, user, filters):
        """Get vehicle-specific context"""
        if not filters or not filters.get('license_plate'):
            return {'vehicle_found': False}
            
        license_plate = filters['license_plate'].upper()
        vehicle_records = ParkingRecord.objects.filter(license_plate=license_plate)
        
        if not vehicle_records.exists():
            return {'vehicle_found': False, 'searched_plate': license_plate}
            
        # Calculate vehicle metrics
        total_visits = vehicle_records.count()
        total_amount = vehicle_records.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        avg_duration = vehicle_records.aggregate(Avg('duration_minutes'))['duration_minutes__avg'] or 0
        
        # Get destinations
        destinations = vehicle_records.values('organization__name').annotate(
            visits=Count('id'),
            total_amount=Sum('amount_paid'),
            avg_duration=Avg('duration_minutes')
        ).order_by('-visits')
        
        return {
            'vehicle_found': True,
            'license_plate': license_plate,
            'total_visits': total_visits,
            'total_amount': float(total_amount),
            'avg_duration': float(avg_duration),
            'destinations': list(destinations),
            'last_visit': vehicle_records.order_by('-entry_time').first().entry_time.isoformat()
        }

    def _get_dashboard_context(self, user):
        """Get dashboard-specific context"""
        if user.role == 'super_admin':
            total_orgs = Organization.objects.count()
            total_users = CustomUser.objects.count()
            return {
                'total_organizations': total_orgs,
                'total_users': total_users,
                'user_type': 'super_admin'
            }
        elif user.role == 'organization_admin':
            org_users = CustomUser.objects.filter(organization=user.organization).count()
            active_users = CustomUser.objects.filter(organization=user.organization, is_active=True).count()
            
            # Get vehicle data for the organization if available
            vehicle_data = {}
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT COUNT(DISTINCT "Plate Number") as vehicle_count,
                               SUM("Amount Paid") as total_revenue,
                               AVG("Duration (Minutes)") as avg_duration
                        FROM combined_dataset 
                        WHERE "Organization" = %s
                    """, [user.organization.name])
                    result = cursor.fetchone()
                    if result:
                        vehicle_data = {
                            'vehicle_count': result[0] or 0,
                            'total_revenue': float(result[1] or 0),
                            'avg_duration': float(result[2] or 0)
                        }
            except Exception as e:
                logger.error(f"Error fetching vehicle data: {e}")
            
            return {
                'organization_users': org_users,
                'active_users': active_users,
                'organization_name': user.organization.name,
                'user_type': 'org_admin',
                **vehicle_data
            }
        else:
            return {'user_type': 'employee'}

    def generate_ai_response(self, message, context):
        """Generate AI response using OpenAI API or fallback"""
        if self.client and OPENAI_AVAILABLE:
            return self._generate_openai_response(message, context)
        else:
            return self._generate_fallback_response(message, context)

    def _generate_openai_response(self, message, context):
        """Generate response using OpenAI API"""
        try:
            system_prompt = self._build_system_prompt(context)
            
            response = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return {
                'response': response.choices[0].message.content,
                'source': 'openai',
                'context_used': True
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return self._generate_fallback_response(message, context)

    def _build_system_prompt(self, context):
        """Build system prompt with context data"""
        base_prompt = """You are an advanced AI assistant for a Vehicle Intelligence System. 
        You provide detailed analytics, insights, and recommendations based on real fleet data.
        
        Current Context:
        """
        
        if context['page_type'] == 'analytics':
            base_prompt += f"""
            - Page: Analytics Dashboard
            - Total Vehicles: {context.get('total_vehicles', 'N/A')}
            - Total Revenue: KSh {context.get('total_revenue', 0):,.2f}
            - Average Duration: {context.get('avg_duration', 0):.1f} minutes
            - User Role: {context['user_role']}
            - Organization: {context['organization']}
            
            Provide insights on fleet performance, optimization opportunities, and data interpretation.
            """
        elif context['page_type'] == 'vehicle_alert':
            if context.get('vehicle_found'):
                base_prompt += f"""
                - Page: Vehicle Alert System
                - Vehicle: {context['license_plate']}
                - Total Visits: {context['total_visits']}
                - Total Amount: KSh {context['total_amount']:,.2f}
                - Average Duration: {context['avg_duration']:.1f} minutes
                - Last Visit: {context['last_visit']}
                
                Provide vehicle-specific analysis, performance insights, and recommendations.
                """
            else:
                base_prompt += """
                - Page: Vehicle Alert System
                - No vehicle currently selected
                
                Help with vehicle search and explain system capabilities.
                """
        elif context['page_type'] == 'org_admin_dashboard':
            base_prompt += f"""
            - Page: Organization Admin Dashboard
            - Organization: {context.get('organization_name', 'N/A')}
            - Total Users: {context.get('organization_users', 0)}
            - Active Users: {context.get('active_users', 0)}
            - Fleet Vehicles: {context.get('vehicle_count', 0)}
            - Fleet Revenue: KSh {context.get('total_revenue', 0):,.2f}
            - Average Parking Duration: {context.get('avg_duration', 0):.1f} minutes
            - User Role: Organization Administrator
            
            Provide organization management insights, user analytics, fleet performance analysis, and administrative recommendations.
            """
        elif context['page_type'] == 'dashboard':
            if context.get('user_type') == 'super_admin':
                base_prompt += f"""
                - Page: Super Admin Dashboard
                - Total Organizations: {context.get('total_organizations', 0)}
                - Total Users: {context.get('total_users', 0)}
                - User Role: Super Administrator
                
                Provide system-wide insights, organizational comparisons, and strategic recommendations.
                """
            else:
                base_prompt += f"""
                - Page: User Dashboard
                - User Role: {context['user_role']}
                - Organization: {context['organization']}
                
                Provide user-specific insights and system navigation help.
                """
        
        base_prompt += """
        
        Guidelines:
        - Provide specific, actionable insights based on the data
        - Use professional but friendly tone
        - Include relevant metrics and comparisons
        - Suggest optimization opportunities
        - Keep responses concise but informative
        - Use emojis sparingly for better readability
        """
        
        return base_prompt

    def _generate_fallback_response(self, message, context):
        """Generate intelligent fallback response without OpenAI"""
        message_lower = message.lower()
        
        # Context-aware responses
        if context['page_type'] == 'analytics':
            return self._analytics_fallback_response(message_lower, context)
        elif context['page_type'] == 'vehicle_alert':
            return self._vehicle_fallback_response(message_lower, context)
        elif context['page_type'] == 'org_admin_dashboard':
            return self._org_admin_fallback_response(message_lower, context)
        else:
            return self._dashboard_fallback_response(message_lower, context)

    def _analytics_fallback_response(self, message, context):
        """Analytics-specific fallback responses"""
        if 'summary' in message or 'overview' in message:
            return {
                'response': f"Analytics Summary: Your fleet has {context.get('total_vehicles', 0)} vehicles generating KSh {context.get('total_revenue', 0):,.2f} in revenue. Average parking duration is {context.get('avg_duration', 0):.1f} minutes. Fleet utilization shows {'high' if context.get('avg_duration', 0) > 60 else 'moderate'} engagement patterns.",
                'source': 'fallback',
                'context_used': True
            }
        elif 'recommendation' in message:
            revenue = context.get('total_revenue', 0)
            duration = context.get('avg_duration', 0)
            recommendations = []
            
            if duration < 30:
                recommendations.append("Consider increasing minimum parking fees to optimize revenue")
            if duration > 120:
                recommendations.append("Implement time limits to increase turnover")
            if revenue < 100000:
                recommendations.append("Focus on marketing to increase vehicle visits")
                
            return {
                'response': f"Optimization Recommendations: {'; '.join(recommendations) if recommendations else 'Current performance is optimal. Monitor trends for future adjustments.'}",
                'source': 'fallback',
                'context_used': True
            }
        
        return {
            'response': "I can provide analytics insights, performance summaries, optimization recommendations, and trend analysis. What specific metric would you like me to analyze?",
            'source': 'fallback',
            'context_used': False
        }

    def _vehicle_fallback_response(self, message, context):
        """Vehicle-specific fallback responses"""
        if not context.get('vehicle_found'):
            return {
                'response': "Please search for a vehicle using the license plate or VIN above. I can then provide detailed performance analysis, maintenance insights, and usage patterns.",
                'source': 'fallback',
                'context_used': True
            }
            
        if 'summary' in message or 'overview' in message:
            return {
                'response': f"Vehicle {context['license_plate']} Analysis: {context['total_visits']} total visits generating KSh {context['total_amount']:,.2f}. Average stay duration is {context['avg_duration']:.1f} minutes. Performance indicates {'high' if context['total_visits'] > 20 else 'moderate'} utilization.",
                'source': 'fallback',
                'context_used': True
            }
        elif 'performance' in message:
            visits = context['total_visits']
            performance_level = 'excellent' if visits > 50 else 'good' if visits > 20 else 'moderate'
            return {
                'response': f"Performance Analysis: This vehicle shows {performance_level} utilization with {visits} visits. Revenue generation is {'strong' if context['total_amount'] > 10000 else 'moderate'}. Consider {'maintaining current usage patterns' if visits > 30 else 'increasing utilization through route optimization'}.",
                'source': 'fallback',
                'context_used': True
            }
            
        return {
            'response': f"I can analyze vehicle {context.get('license_plate', 'data')} including performance metrics, usage patterns, cost analysis, and maintenance recommendations. What specific aspect interests you?",
            'source': 'fallback',
            'context_used': True
        }

    def _org_admin_fallback_response(self, message, context):
        """Organization admin dashboard specific fallback responses"""
        org_name = context.get('organization_name', 'your organization')
        user_count = context.get('organization_users', 0)
        active_users = context.get('active_users', 0)
        vehicle_count = context.get('vehicle_count', 0)
        total_revenue = context.get('total_revenue', 0)
        
        if 'summary' in message or 'overview' in message:
            return {
                'response': f"Organization Overview: {org_name} has {user_count} total users with {active_users} active users. Your fleet includes {vehicle_count} vehicles generating KSh {total_revenue:,.2f} in revenue. User engagement rate is {(active_users/user_count*100) if user_count > 0 else 0:.1f}%.",
                'source': 'fallback',
                'context_used': True
            }
        elif 'users' in message or 'employees' in message:
            inactive_users = user_count - active_users
            return {
                'response': f"User Management: You have {user_count} users in {org_name}. {active_users} are active and {inactive_users} are inactive. {'Focus on re-engaging inactive users' if inactive_users > 0 else 'Excellent user engagement!'} Consider implementing user activity monitoring and profile completion initiatives.",
                'source': 'fallback',
                'context_used': True
            }
        elif 'fleet' in message or 'vehicle' in message:
            if vehicle_count > 0:
                avg_revenue_per_vehicle = total_revenue / vehicle_count if vehicle_count > 0 else 0
                return {
                    'response': f"Fleet Analysis: {org_name} operates {vehicle_count} vehicles generating an average of KSh {avg_revenue_per_vehicle:,.2f} per vehicle. {'Strong performance' if avg_revenue_per_vehicle > 5000 else 'Consider optimization strategies'} for revenue generation. Monitor parking patterns and duration for efficiency improvements.",
                    'source': 'fallback',
                    'context_used': True
                }
            else:
                return {
                    'response': f"No fleet data available for {org_name}. This could mean vehicles haven't been registered in the parking system yet, or data collection is still in progress.",
                    'source': 'fallback',
                    'context_used': True
                }
        elif 'recommendation' in message or 'optimize' in message:
            recommendations = []
            if user_count > 0 and (active_users/user_count) < 0.8:
                recommendations.append("Increase user engagement through training and communication")
            if vehicle_count > 0 and total_revenue < 50000:
                recommendations.append("Optimize fleet utilization and parking strategies")
            if user_count > 20:
                recommendations.append("Implement department-based user management")
            
            return {
                'response': f"Optimization Recommendations for {org_name}: {'; '.join(recommendations) if recommendations else 'Current performance is good. Continue monitoring user activity and fleet efficiency.'}",
                'source': 'fallback',
                'context_used': True
            }
        elif 'report' in message:
            return {
                'response': f"I can generate comprehensive reports for {org_name} including: User activity analysis ({user_count} users), fleet performance summary ({vehicle_count} vehicles), revenue analysis (KSh {total_revenue:,.2f}), and organizational efficiency metrics. Would you like me to create a detailed management report?",
                'source': 'fallback',
                'context_used': True
            }
        
        return {
            'response': f"I can help you manage {org_name} with insights on your {user_count} users, {vehicle_count} fleet vehicles, revenue analysis, user engagement strategies, and organizational optimization. What specific aspect would you like to explore?",
            'source': 'fallback',
            'context_used': True
        }

    def _dashboard_fallback_response(self, message, context):
        """Dashboard-specific fallback responses"""
        if context['user_type'] == 'super_admin':
            return {
                'response': f"System Overview: Managing {context.get('total_organizations', 0)} organizations with {context.get('total_users', 0)} total users. I can provide system analytics, user management insights, and organizational performance comparisons.",
                'source': 'fallback',
                'context_used': True
            }
        elif context['user_type'] == 'org_admin':
            return {
                'response': f"Organization Dashboard: {context['organization_name']} has {context.get('organization_users', 0)} users. I can help with user management, organizational analytics, and performance insights.",
                'source': 'fallback',
                'context_used': True
            }
        
        return {
            'response': "I can help with vehicle analytics, performance insights, and system navigation. What would you like to explore?",
            'source': 'fallback',
            'context_used': False
        }

    def generate_detailed_report(self, context, report_type='comprehensive'):
        """Generate detailed AI-powered reports"""
        if self.client and OPENAI_AVAILABLE:
            return self._generate_ai_report(context, report_type)
        else:
            return self._generate_fallback_report(context, report_type)

    def _generate_ai_report(self, context, report_type):
        """Generate AI-powered detailed report"""
        try:
            report_prompt = f"""
            Generate a comprehensive {report_type} report based on this vehicle intelligence data:
            {json.dumps(context, indent=2)}
            
            Include:
            1. Executive Summary
            2. Key Performance Indicators
            3. Trend Analysis
            4. Optimization Recommendations
            5. Predictive Insights
            6. Action Items
            
            Format as structured text suitable for PDF generation.
            """
            
            response = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": report_prompt}],
                max_tokens=1500,
                temperature=0.5
            )
            
            return {
                'report_content': response.choices[0].message.content,
                'source': 'openai',
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI report generation error: {str(e)}")
            return self._generate_fallback_report(context, report_type)

    def _generate_fallback_report(self, context, report_type):
        """Generate structured fallback report"""
        report_sections = []
        
        # Executive Summary
        if context['page_type'] == 'analytics':
            summary = f"""
            EXECUTIVE SUMMARY
            =================
            Fleet Performance Overview for {context['organization']}
            
            • Total Vehicles: {context.get('total_vehicles', 0)}
            • Revenue Generated: KSh {context.get('total_revenue', 0):,.2f}
            • Average Utilization: {context.get('avg_duration', 0):.1f} minutes
            • Performance Rating: {'Excellent' if context.get('total_revenue', 0) > 100000 else 'Good'}
            """
        else:
            summary = f"""
            VEHICLE INTELLIGENCE REPORT
            ===========================
            Analysis for {context.get('license_plate', 'Selected Vehicle')}
            
            • Total Visits: {context.get('total_visits', 0)}
            • Revenue Impact: KSh {context.get('total_amount', 0):,.2f}
            • Utilization Pattern: {context.get('avg_duration', 0):.1f} min average
            • Performance Status: {'High Performer' if context.get('total_visits', 0) > 30 else 'Standard'}
            """
        
        report_sections.append(summary)
        
        # Recommendations
        recommendations = """
        OPTIMIZATION RECOMMENDATIONS
        ============================
        1. Monitor peak usage patterns for capacity planning
        2. Implement predictive maintenance schedules
        3. Optimize pricing strategies based on demand
        4. Enhance route efficiency through data analysis
        5. Consider fleet expansion in high-demand areas
        """
        
        report_sections.append(recommendations)
        
        return {
            'report_content': '\n'.join(report_sections),
            'source': 'fallback',
            'generated_at': datetime.now().isoformat()
        }

# Initialize global AI assistant instance
ai_assistant = AIAssistant()