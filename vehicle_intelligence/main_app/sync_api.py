from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .signals import sync_vehicle_users

@login_required
@require_POST
def sync_users_api(request):
    """API endpoint to manually sync vehicle users"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        success = sync_vehicle_users()
        if success:
            return JsonResponse({'success': True, 'message': 'Users synced successfully'})
        else:
            return JsonResponse({'success': False, 'error': 'Sync failed'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})