from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
import json
from .models import ParkingRecord

@csrf_exempt
@require_POST
def add_parking_entry(request):
    """API endpoint to add new parking entry in real-time"""
    try:
        data = json.loads(request.body)
        
        record = ParkingRecord.objects.create(
            plate_number=data['plate_number'],
            entry_time=timezone.now(),
            vehicle_type=data.get('vehicle_type', 'Unknown'),
            vehicle_brand=data.get('vehicle_brand', 'Unknown'),
            organization=data['organization'],
            parking_status='active'
        )
        
        return JsonResponse({'success': True, 'id': record.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@require_POST
def update_parking_exit(request):
    """API endpoint to update parking exit in real-time"""
    try:
        data = json.loads(request.body)
        
        record = ParkingRecord.objects.get(
            plate_number=data['plate_number'],
            parking_status='active'
        )
        
        record.exit_time = timezone.now()
        record.amount_paid = data.get('amount_paid', 0)
        record.payment_method = data.get('payment_method', 'Cash')
        record.parking_duration_minutes = (record.exit_time - record.entry_time).total_seconds() / 60
        record.parking_status = 'completed'
        record.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})