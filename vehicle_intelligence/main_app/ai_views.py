# ai_views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import json
from .ai_assistant import ai_assistant
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def ai_chat_endpoint(request):
    """Handle AI chat requests"""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        page_type = data.get('page_type', 'dashboard')
        filters = data.get('filters', {})
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Message is required'
            }, status=400)
        
        # Get context data for AI
        context = ai_assistant.get_context_data(request.user, page_type, filters)
        
        # Generate AI response
        ai_response = ai_assistant.generate_ai_response(message, context)
        
        return JsonResponse({
            'success': True,
            'response': ai_response['response'],
            'source': ai_response['source'],
            'context_used': ai_response['context_used'],
            'timestamp': context['timestamp']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def ai_report_endpoint(request):
    """Handle AI report generation requests"""
    try:
        data = json.loads(request.body)
        page_type = data.get('page_type', 'dashboard')
        report_type = data.get('report_type', 'comprehensive')
        filters = data.get('filters', {})
        
        # Get context data for report
        context = ai_assistant.get_context_data(request.user, page_type, filters)
        
        # Generate detailed report
        report_data = ai_assistant.generate_detailed_report(context, report_type)
        
        return JsonResponse({
            'success': True,
            'report': report_data['report_content'],
            'source': report_data['source'],
            'generated_at': report_data['generated_at'],
            'report_type': report_type
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"AI report error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)

@login_required
@require_http_methods(["GET"])
def ai_suggestions_endpoint(request):
    """Get AI-powered suggestions based on current context"""
    try:
        page_type = request.GET.get('page_type', 'dashboard')
        filters = {}
        
        # Extract filters from query parameters
        for key in ['organization', 'vehicle_brand', 'vehicle_type', 'license_plate']:
            if request.GET.get(key):
                filters[key] = request.GET.get(key)
        
        # Get context data
        context = ai_assistant.get_context_data(request.user, page_type, filters)
        
        # Generate contextual suggestions
        suggestions = []
        
        if page_type == 'analytics':
            suggestions = [
                "Give me a performance summary",
                "What optimization recommendations do you have?",
                "Show me trend analysis",
                "Generate a detailed report",
                "What insights can you provide?"
            ]
        elif page_type == 'vehicle_alert':
            if context.get('vehicle_found'):
                suggestions = [
                    f"Analyze {context.get('license_plate', 'this vehicle')} performance",
                    "What maintenance recommendations do you have?",
                    "Show cost analysis",
                    "Generate vehicle report",
                    "Compare with fleet average"
                ]
            else:
                suggestions = [
                    "How do I search for a vehicle?",
                    "What data can you analyze?",
                    "Show me search examples",
                    "Explain vehicle metrics"
                ]
        else:
            suggestions = [
                "Give me a system overview",
                "What can you help me with?",
                "Show me key insights",
                "Generate dashboard report"
            ]
        
        return JsonResponse({
            'success': True,
            'suggestions': suggestions,
            'context': {
                'page_type': page_type,
                'has_data': context.get('vehicle_found', True)
            }
        })
        
    except Exception as e:
        logger.error(f"AI suggestions error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)