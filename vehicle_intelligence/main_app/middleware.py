from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin

class RoleBasedAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip middleware for static/media files and debug
        skip_paths = [
            '/static/',
            '/media/',
            '/__debug__/',
            '/favicon.ico',
        ]
        
        for path in skip_paths:
            if request.path.startswith(path):
                return None
        
        # Block access to Django admin completely
        if request.path.startswith('/admin/'):
            messages.error(request, '🚫 Django Admin is disabled. Use the HTML Dashboard instead.')
            return redirect('login')
        
        # Public paths that don't require authentication
        public_paths = [
            '/',
            '/login/',
            '/logout/',
            '/change-password/',
        ]
        
        # Allow access to public paths without authentication
        if any(request.path == path or request.path.startswith(path.rstrip('/') + '/') for path in public_paths):
            # If user is already authenticated and tries to access login page, redirect to appropriate dashboard
            if request.path in ['/', '/login/'] and request.user.is_authenticated:
                # Check if password needs to be changed
                if hasattr(request.user, 'force_password_change') and request.user.force_password_change:
                    return redirect('change_password')
                
                # Redirect based on role
                # Check both role field and is_superuser for super admin detection
                if hasattr(request.user, 'role'):
                    user_role = getattr(request.user, 'role', 'employee')
                else:
                    # For users created with Django's createsuperuser
                    user_role = 'super_admin' if getattr(request.user, 'is_superuser', False) else 'employee'
                
                if user_role == 'super_admin' or getattr(request.user, 'is_superuser', False):
                    return redirect('super_admin_dashboard')
                elif user_role == 'organization_admin':
                    return redirect('org_admin_dashboard')
                else:
                    return redirect('dashboard')
            return None
        
        # Check if user is authenticated for all other paths
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        
        # Check if user needs to change password (skip for change-password and logout pages)
        if (hasattr(request.user, 'force_password_change') and 
            request.user.force_password_change and 
            request.path != '/change-password/' and
            request.path != '/logout/'):
            messages.info(request, 'Please change your temporary password.')
            return redirect('change_password')
        
        # Get user role - handle both CustomUser role field and Django's is_superuser
        if hasattr(request.user, 'role'):
            user_role = getattr(request.user, 'role', 'employee')
        else:
            # For users created with Django's createsuperuser
            user_role = 'super_admin' if getattr(request.user, 'is_superuser', False) else 'employee'
        
        # Super Admin Paths - Only accessible by super_admin or is_superuser
        super_admin_paths = [
            '/super-admin-dashboard/',
            '/super-admin/organizations/',
            '/super-admin/users/',
            '/super-admin/activities/',
            '/super-admin/create-org/',
            '/super-admin/create-org-admin/',
            '/super-admin/create-super-admin/',
            '/super-admin/reset-user-password/',
            '/super-admin/delete-user/',
            '/super-admin/delete-organization/',
            '/super-admin/organizations/api/',
        ]
        
        for path in super_admin_paths:
            if request.path.startswith(path):
                # Check if user is super_admin OR has is_superuser=True
                is_super_admin = user_role == 'super_admin' or getattr(request.user, 'is_superuser', False)
                if not is_super_admin:
                    messages.error(request, "You don't have permission to access this page.")
                    return redirect('dashboard')
                return None  # Allow access if user is super admin
        
        # Organization Admin Paths - Only accessible by organization_admin
        org_admin_paths = [
            '/org-admin/dashboard/',
            '/org-admin/add-user/',
            '/org-admin/edit-user/',
            '/org-admin/reset-password/',
        ]
        
        for path in org_admin_paths:
            if request.path.startswith(path):
                if user_role != 'organization_admin':
                    messages.error(request, "You don't have permission to access this page.")
                    return redirect('dashboard')
                return None  # Allow access if user is organization admin
        
        # Check module access permissions for other paths
        if hasattr(request.user, 'can_access_module'):
            try:
                resolved_url = resolve(request.path)
                url_name = resolved_url.url_name
                
                # Map URL names to module names
                url_to_module_map = {
                    # Authentication
                    'login': 'dashboard',
                    'logout': 'dashboard',
                    'change_password': 'dashboard',
                    
                    # Dashboards
                    'home': 'dashboard',
                    'dashboard': 'dashboard',
                    'super_admin_dashboard': 'super_admin_dashboard',
                    'org_admin_dashboard': 'org_admin_dashboard',
                    
                    # Super Admin
                    'super_admin_organizations': 'super_admin_organizations',
                    'super_admin_users': 'super_admin_users',
                    'super_admin_activities': 'super_admin_activities',
                    'super_admin_create_org': 'super_admin_organizations',
                    'super_admin_create_org_admin': 'super_admin_users',
                    'super_admin_create_super_admin': 'super_admin_users',
                    'super_admin_reset_user_password': 'super_admin_users',
                    'super_admin_delete_user': 'super_admin_users',
                    'super_admin_delete_organization': 'super_admin_organizations',
                    'super_admin_organizations_api': 'super_admin_organizations',
                    
                    # Organization Admin
                    'add_user': 'user_management',
                    'edit_user': 'user_management',
                    'reset_user_password': 'user_management',
                    
                    # Modules
                    'analytics': 'analytics',
                    'inventory': 'inventory',
                    'sales': 'sales',
                    'purchasing': 'purchasing',
                    'manufacturing': 'manufacturing',
                    'online_store': 'online_store',
                    'store_management': 'store_management',
                    'hr_dashboard': 'hr_dashboard',
                    'reports': 'reports',
                    'settings': 'settings',
                    'help_center': 'help_center',
                    
                    # Profile
                    'update_profile': 'profile_settings',
                }
                
                module_name = url_to_module_map.get(url_name)
                if module_name:
                    # Check if user can access this module
                    # Super admins have access to all modules
                    if not request.user.can_access_module(module_name) and not (user_role == 'super_admin' or getattr(request.user, 'is_superuser', False)):
                        messages.error(request, "You don't have permission to access this page.")
                        return redirect('dashboard')
                    
            except Exception as e:
                # If URL doesn't resolve or other error, log and continue
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"URL resolution error: {e}")
        
        # Special handling for super users with is_superuser=True but no role field
        # Ensure they can access super admin dashboard even if role field is not set
        if request.path == '/super-admin-dashboard/' and getattr(request.user, 'is_superuser', False):
            return None
        
        return None

    def process_response(self, request, response):
        """Add security headers and handle some response modifications"""
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Clear messages after they're displayed to prevent duplicates
        if hasattr(request, '_messages'):
            storage = messages.get_messages(request)
            storage.used = True
        
        return response