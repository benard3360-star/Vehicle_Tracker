from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate, update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.core.paginator import Paginator
from django.db.models import Q, Count
import json
from .models import Organization, ActivityLog, CustomUser, InventoryItem
import secrets
import string
from .models import UserProfile, Document, Notification, ActivityLog, ProfileAuditLog
from datetime import datetime, timedelta
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def generate_temp_password(length=12):
    """Generate a secure temporary password"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))

# ==================== AUTHENTICATION VIEWS ====================

def login(request):
    """Handle user login"""
    if request.user.is_authenticated:
        # Check if password needs to be changed
        if hasattr(request.user, 'force_password_change') and request.user.force_password_change:
            return redirect('change_password')
        
        # Redirect based on role - check both role field and is_superuser
        user_role = getattr(request.user, 'role', 'employee')
        if user_role == 'super_admin' or getattr(request.user, 'is_superuser', False):
            return redirect('super_admin_dashboard')
        elif user_role == 'organization_admin':
            return redirect('org_admin_dashboard')
        else:
            return redirect('dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                auth_login(request, user)
                
                # Update last active
                if hasattr(user, 'update_last_active'):
                    user.update_last_active()
                
                # Log login activity
                ActivityLog.objects.create(
                    user=user,
                    organization=user.organization if hasattr(user, 'organization') else None,
                    action='login',
                    module='authentication',
                    description=f'User {user.username} logged in successfully',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Check if password needs to be changed
                if hasattr(user, 'force_password_change') and user.force_password_change:
                    messages.info(request, 'Please change your temporary password.')
                    return redirect('change_password')
                
                # Redirect based on role
                user_role = getattr(user, 'role', 'employee')
                if user_role == 'super_admin' or getattr(user, 'is_superuser', False):
                    return redirect('super_admin_dashboard')
                elif user_role == 'organization_admin':
                    return redirect('org_admin_dashboard')
                else:
                    return redirect('dashboard')
            else:
                messages.error(request, 'Your account is inactive.')
        else:
            messages.error(request, 'Invalid credentials. Please try again.')

    return render(request, 'login.html')

@login_required
def change_password(request):
    """Handle password change"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif new_password == current_password:
            messages.error(request, 'New password must be different from current password.')
        else:
            request.user.set_password(new_password)
            request.user.force_password_change = False
            request.user.temp_password = ''
            request.user.save()
            
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully!')
            
            ActivityLog.objects.create(
                user=request.user,
                organization=request.user.organization,
                action='update',
                module='authentication',
                description='Changed password',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return redirect('dashboard')
    
    return render(request, 'change_password.html')

@login_required
def logout_view(request):
    """Handle user logout"""
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='logout',
        module='authentication',
        description=f'User {request.user.username} logged out',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    auth_logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

# ==================== DASHBOARD VIEWS ====================

@login_required
def dashboard(request):
    """Main dashboard view based on user role"""
    # Get user's role - check both role field and is_superuser
    user_role = getattr(request.user, 'role', 'employee')
    
    # If user is super_admin OR has is_superuser=True, redirect to super admin dashboard
    if user_role == 'super_admin' or getattr(request.user, 'is_superuser', False):
        return redirect('super_admin_dashboard')
    
    # If user is organization_admin, redirect to org admin dashboard
    if user_role == 'organization_admin':
        return redirect('org_admin_dashboard')
    
    # For other users (managers, employees, etc.), show normal dashboard
    organization = getattr(request.user, 'organization', None)
    
    # Get module access status
    accessible_modules = {
        'analytics': request.user.can_access_module('analytics'),
        'inventory': request.user.can_access_module('inventory'),
        'sales': request.user.can_access_module('sales'),
        'hr_dashboard': request.user.can_access_module('hr_dashboard'),
        'reports': request.user.can_access_module('reports'),
        'settings': request.user.can_access_module('settings'),
    }
    
    # Get user's recent activities
    recent_activities = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:10]
    
    context = {
        'tenant': {
            'name': organization.name if organization else 'System',
        },
        'accessible_modules': accessible_modules,
        'recent_activities': recent_activities,
        'now': timezone.now(),
        'user_role': user_role,
        'organization': organization,
    }

    if organization and request.user.id:
        ActivityLog.objects.create(
            user=request.user,
            organization=organization,
            action='view',
            module='dashboard',
            description='Accessed dashboard',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

    return render(request, 'dashboard.html', context)

# ==================== SUPER ADMIN VIEWS ====================

@login_required
def super_admin_dashboard(request):
    """Super admin dashboard - only accessible by super_admin role"""
    user_role = getattr(request.user, 'role', 'employee')
    
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get system statistics for super admin
    total_organizations = Organization.objects.count()
    active_organizations = Organization.objects.filter(is_active=True).count()
    total_system_users = CustomUser.objects.filter(role__in=['super_admin', 'organization_admin']).count()
    total_super_admins = CustomUser.objects.filter(role='super_admin').count()
    total_org_admins = CustomUser.objects.filter(role='organization_admin').count()
    
    # Get recent system activities (only super admins and organization admins)
    recent_system_activities = ActivityLog.objects.filter(
        user__role__in=['super_admin', 'organization_admin']
    ).order_by('-timestamp')[:15]
    
    # Get recent organizations created
    recent_organizations = Organization.objects.all().order_by('-created_at')[:10]
    
    # Get organizations without admins
    organizations_without_admins = Organization.objects.filter(admin_user__isnull=True).count()
    
    context = {
        'user_role': user_role,
        'total_organizations': total_organizations,
        'active_organizations': active_organizations,
        'total_system_users': total_system_users,
        'total_super_admins': total_super_admins,
        'total_org_admins': total_org_admins,
        'organizations_without_admins': organizations_without_admins,
        'recent_system_activities': recent_system_activities,
        'recent_organizations': recent_organizations,
        'now': timezone.now(),
    }
    
    # Log the access
    ActivityLog.objects.create(
        user=request.user,
        organization=None,
        action='view',
        module='super_admin_dashboard',
        description='Accessed super admin dashboard',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'super_admin_dashboard.html', context)

@login_required
def super_admin_organizations_view(request):
    """Super admin organizations management page"""
    user_role = getattr(request.user, 'role', 'employee')
    
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    organizations = Organization.objects.all().order_by('-created_at')
    
    context = {
        'user_role': user_role,
        'organizations': organizations,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=None,
        action='view',
        module='super_admin_organizations',
        description='Accessed organizations management',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'super_admin_organizations.html', context)

@login_required
def super_admin_users_view(request):
    """Super admin users management page"""
    user_role = getattr(request.user, 'role', 'employee')
    
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get all super admins and organization admins
    system_users = CustomUser.objects.filter(
        role__in=['super_admin', 'organization_admin']
    ).order_by('-date_joined')
    
    context = {
        'user_role': user_role,
        'system_users': system_users,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=None,
        action='view',
        module='super_admin_users',
        description='Accessed system users management',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'super_admin_users.html', context)

@login_required
def super_admin_activities_view(request):
    """Super admin activities monitoring page"""
    user_role = getattr(request.user, 'role', 'employee')
    
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get activities for super admins and organization admins only
    activities = ActivityLog.objects.filter(
        user__role__in=['super_admin', 'organization_admin']
    ).order_by('-timestamp')[:50]
    
    context = {
        'user_role': user_role,
        'activities': activities,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=None,
        action='view',
        module='super_admin_activities',
        description='Accessed system activities',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'super_admin_activities.html', context)

# ==================== SUPER ADMIN API ENDPOINTS ====================

@login_required
@require_GET
def super_admin_organizations_api(request):
    """API endpoint for organizations data"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    organizations = Organization.objects.all().order_by('-created_at')
    
    # Filtering
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    if search:
        organizations = organizations.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(slug__icontains=search)
        )
    
    if status == 'active':
        organizations = organizations.filter(is_active=True)
    elif status == 'inactive':
        organizations = organizations.filter(is_active=False)
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(organizations, per_page)
    
    try:
        org_page = paginator.page(page)
    except:
        org_page = paginator.page(1)
    
    orgs_data = []
    for org in org_page.object_list:
        orgs_data.append({
            'id': org.id,
            'name': org.name,
            'slug': org.slug,
            'email': org.email,
            'phone': org.phone or '-',
            'address': org.address or '-',
            'is_active': org.is_active,
            'status': 'Active' if org.is_active else 'Inactive',
            'created_at': org.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': org.updated_at.strftime('%Y-%m-%d %H:%M:%S') if org.updated_at else '',
            'user_count': org.users.count(),
            'has_admin': org.admin_user is not None,
            'admin_name': org.admin_user.get_full_name_or_username() if org.admin_user else 'Not assigned',
        })
    
    return JsonResponse({
        'success': True,
        'organizations': orgs_data,
        'total_pages': paginator.num_pages,
        'current_page': org_page.number,
        'total_count': paginator.count,
    })

@login_required
@require_POST
def super_admin_create_organization(request):
    """Create new organization from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        address = data.get('address', '').strip()
        is_active = data.get('is_active', 'true') == 'true'
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Organization name is required'}, status=400)
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
        
        # Check if organization with same name exists
        if Organization.objects.filter(name=name).exists():
            return JsonResponse({'success': False, 'error': 'Organization with this name already exists'}, status=400)
        
        # Check if organization with same email exists
        if Organization.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Organization with this email already exists'}, status=400)
        
        # Generate slug from name
        slug = name.lower().replace(' ', '-').replace('_', '-')
        # Make slug unique
        base_slug = slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        org = Organization.objects.create(
            name=name,
            slug=slug,
            email=email,
            phone=phone,
            address=address,
            is_active=is_active,
            created_by=request.user
        )
        
        ActivityLog.objects.create(
            user=request.user,
            action='create',
            module='organizations',
            description=f'Created organization: {name}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Organization "{name}" created successfully!',
            'organization': {
                'id': org.id,
                'name': org.name,
                'slug': org.slug,
                'email': org.email,
                'phone': org.phone,
                'is_active': org.is_active,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def super_admin_create_org_admin(request):
    """Create organization admin from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        org_id = data.get('org_id')
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        
        if not org_id:
            return JsonResponse({'success': False, 'error': 'Organization ID is required'}, status=400)
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username is required'}, status=400)
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
        
        # Get organization
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Organization not found'}, status=404)
        
        # Check if organization already has an admin
        if organization.admin_user:
            return JsonResponse({
                'success': False, 
                'error': f'Organization already has an admin: {organization.admin_user.username}'
            }, status=400)
        
        # Check if username exists
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'}, status=400)
        
        # Check if email exists
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
        
        # Generate temporary password
        temp_password = generate_temp_password()
        
        # Create organization admin
        org_admin = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=temp_password,
            first_name=first_name,
            last_name=last_name,
            role='organization_admin',
            phone=phone,
            organization=organization,
            force_password_change=True,
            temp_password=temp_password,
            is_active=True,
            created_by=request.user
        )
        
        # Update organization with admin user
        organization.admin_user = org_admin
        organization.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='create',
            module='user_management',
            description=f'Created organization admin {username} for {organization.name}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Organization admin created successfully!',
            'user': {
                'id': org_admin.id,
                'username': org_admin.username,
                'email': org_admin.email,
                'temp_password': temp_password,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def super_admin_create_super_admin(request):
    """Create super admin from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        phone = data.get('phone', '').strip()
        
        if not username:
            return JsonResponse({'success': False, 'error': 'Username is required'}, status=400)
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
        
        # Check if username exists
        if CustomUser.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'}, status=400)
        
        # Check if email exists
        if CustomUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
        
        # Generate temporary password
        temp_password = generate_temp_password()
        
        # Create super admin using create_superuser method
        super_admin = CustomUser.objects.create_superuser(
            username=username,
            email=email,
            password=temp_password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            force_password_change=True,
            temp_password=temp_password,
            is_active=True,
            created_by=request.user
        )
        
        ActivityLog.objects.create(
            user=request.user,
            action='create',
            module='user_management',
            description=f'Created super admin {username}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Super admin created successfully!',
            'user': {
                'id': super_admin.id,
                'username': super_admin.username,
                'email': super_admin.email,
                'temp_password': temp_password,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def super_admin_reset_user_password(request):
    """Reset user password from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User ID is required'}, status=400)
        
        # Get user
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Check if user is a system user (super_admin or organization_admin)
        if user.role not in ['super_admin', 'organization_admin']:
            return JsonResponse({
                'success': False, 
                'error': 'Can only reset passwords for system users'
            }, status=400)
        
        # Generate new temporary password
        temp_password = generate_temp_password()
        
        # Update user
        user.set_password(temp_password)
        user.force_password_change = True
        user.temp_password = temp_password
        user.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='reset_password',
            module='user_management',
            description=f'Reset password for user {user.username}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Password reset successfully!',
            'temp_password': temp_password,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def super_admin_delete_user(request):
    """Delete user from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        user_id = data.get('user_id')
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User ID is required'}, status=400)
        
        # Get user
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
        
        # Cannot delete yourself
        if user.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'Cannot delete yourself'}, status=400)
        
        username = user.username
        
        # If user is organization admin, remove them from organization
        if user.role == 'organization_admin' and user.organization:
            organization = user.organization
            organization.admin_user = None
            organization.save()
        
        user.delete()
        
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            module='user_management',
            description=f'Deleted user {username}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'User {username} deleted successfully!',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
@require_POST
def super_admin_delete_organization(request):
    """Delete organization from super admin dashboard"""
    user_role = getattr(request.user, 'role', 'employee')
    # Check if user is super_admin OR has is_superuser=True
    if user_role != 'super_admin' and not getattr(request.user, 'is_superuser', False):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        org_id = data.get('org_id')
        
        if not org_id:
            return JsonResponse({'success': False, 'error': 'Organization ID is required'}, status=400)
        
        # Get organization
        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Organization not found'}, status=404)
        
        org_name = organization.name
        
        # Check if organization has users
        user_count = organization.users.count()
        if user_count > 0:
            return JsonResponse({
                'success': False, 
                'error': f'Cannot delete organization with {user_count} users. Delete users first.'
            }, status=400)
        
        # Delete the organization
        organization.delete()
        
        ActivityLog.objects.create(
            user=request.user,
            action='delete',
            module='organizations',
            description=f'Deleted organization {org_name}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Organization {org_name} deleted successfully!',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# ==================== ORGANIZATION ADMIN VIEWS ====================

@login_required
def org_admin_dashboard(request):
    """Organization admin dashboard - only accessible by organization_admin"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'organization_admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if not request.user.organization:
        messages.error(request, "You are not assigned to any organization.")
        return redirect('dashboard')
    
    organization = request.user.organization
    
    # Get all users in the organization except super admins
    users = CustomUser.objects.filter(
        organization=organization
    ).exclude(role='super_admin').order_by('-date_joined')
    
    # Enhanced user statistics
    user_count = users.count()
    active_users = users.filter(is_active=True).count()
    inactive_users = user_count - active_users
    
    # Recent hires (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_hires = users.filter(date_joined__gte=thirty_days_ago).count()
    
    # Users created by this admin
    users_created_by_admin = users.filter(created_by=request.user).count()
    
    # Role distribution with counts
    role_distribution = {}
    for role_code, role_name in CustomUser.ROLE_CHOICES:
        if role_code != 'super_admin':
            count = users.filter(role=role_code).count()
            if count > 0:
                role_distribution[role_name] = count
    
    # Department distribution
    dept_distribution = {}
    departments = users.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()
    for dept in departments:
        count = users.filter(department=dept).count()
        dept_distribution[dept] = count
    
    # User profiles completion
    users_with_profiles = UserProfile.objects.filter(user__organization=organization).count()
    profile_completion_rate = (users_with_profiles / user_count * 100) if user_count > 0 else 0
    
    # Document statistics
    total_documents = Document.objects.filter(user__organization=organization).count()
    verified_documents = Document.objects.filter(user__organization=organization, is_verified=True).count()
    pending_documents = total_documents - verified_documents
    
    # Users needing attention
    users_needing_attention = []
    for user in users[:15]:
        issues = []
        profile = getattr(user, 'profile', None)
        
        if not profile:
            issues.append('No profile created')
        else:
            if not profile.date_of_birth:
                issues.append('Missing date of birth')
            if not profile.mobile_phone and not user.phone:
                issues.append('Missing phone number')
            if not profile.address_line1:
                issues.append('Missing address')
        
        # Check for expired documents
        expired_docs = Document.objects.filter(
            user=user, 
            expires_at__lt=timezone.now().date()
        ).count()
        if expired_docs > 0:
            issues.append(f'{expired_docs} expired document(s)')
        
        if issues:
            users_needing_attention.append({
                'user': user,
                'issues': issues
            })
    
    # Recent activities for this organization
    recent_activities = ActivityLog.objects.filter(
        organization=organization
    ).exclude(user__role='super_admin').order_by('-timestamp')[:25]
    
    # User activity tracking
    user_activities = {}
    for user in users[:10]:  # Top 10 users
        activity_count = ActivityLog.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count()
        user_activities[user] = activity_count
    
    # Most active users (last 7 days)
    most_active_users = sorted(user_activities.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Login statistics (last 30 days)
    login_activities = ActivityLog.objects.filter(
        organization=organization,
        action='login',
        timestamp__gte=thirty_days_ago
    ).count()
    
    # Add analytics data for organization
    from .analytics import VehicleAnalytics
    from .models import Vehicle, VehicleMovement
    
    analytics_engine = VehicleAnalytics(organization=organization)
    fleet_summary = analytics_engine.get_fleet_summary()
    daily_trips_chart = analytics_engine.get_daily_trips_chart()
    parking_duration_chart = analytics_engine.get_parking_duration_chart()
    route_analysis = analytics_engine.get_route_analysis()[:5]  # Top 5 routes
    
    context = {
        'organization': organization,
        'users': users[:20],  # Latest 20 users for display
        'all_users': users,  # All users for other calculations
        'user_count': user_count,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'recent_hires': recent_hires,
        'users_created_by_admin': users_created_by_admin,
        'role_distribution': role_distribution,
        'dept_distribution': dept_distribution,
        'profile_completion_rate': round(profile_completion_rate, 1),
        'total_documents': total_documents,
        'verified_documents': verified_documents,
        'pending_documents': pending_documents,
        'users_needing_attention': users_needing_attention[:10],
        'recent_activities': recent_activities,
        'most_active_users': most_active_users,
        'login_activities': login_activities,
        'fleet_summary': fleet_summary,
        'daily_trips_chart': daily_trips_chart,
        'parking_duration_chart': parking_duration_chart,
        'hourly_entries_chart': analytics_engine.get_hourly_entries_chart(organization),
        'vehicles_per_site_chart': analytics_engine.get_vehicles_per_site_chart(organization),
        'revenue_per_site_chart': analytics_engine.get_revenue_per_site_chart(organization),
        'visit_patterns_chart': analytics_engine.get_visit_patterns_chart(organization),
        'avg_stay_by_type_chart': analytics_engine.get_avg_stay_by_type_chart(organization),
        'movement_flow_chart': analytics_engine.get_movement_flow_chart(organization),
        'route_analysis': route_analysis,
        'has_vehicle_data': Vehicle.objects.filter(organization=organization).exists(),
        'now': timezone.now(),
        'user_role': user_role,
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=organization,
        action='view',
        module='org_admin_dashboard',
        description='Accessed organization admin dashboard',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'org_admin_dashboard.html', context)

@login_required
def add_user(request):
    """Add new user to organization - only accessible by organization_admin"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'organization_admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'employee')
        phone = request.POST.get('phone', '').strip()
        department = request.POST.get('department', '').strip()
        job_title = request.POST.get('job_title', '').strip()
        
        # Validate role - organization admin cannot create other organization admins or super admins
        if role in ['super_admin', 'organization_admin']:
            messages.error(request, 'You cannot create this type of user.')
            return render(request, 'add_user.html')
        
        if not username or not email or not first_name or not last_name:
            messages.error(request, 'Please fill all required fields.')
        elif CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            temp_password = generate_temp_password()
            
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=temp_password,
                first_name=first_name,
                last_name=last_name,
                role=role,
                phone=phone,
                department=department,
                job_title=job_title,
                organization=request.user.organization,
                force_password_change=True,
                temp_password=temp_password,
                is_active=True,
                created_by=request.user
            )
            
            messages.success(request, 
                f'User {username} created successfully! '
                f'Temporary password: {temp_password}'
            )
            
            ActivityLog.objects.create(
                user=request.user,
                organization=request.user.organization,
                action='create',
                module='user_management',
                description=f'Added user {username} with role {role}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return redirect('org_admin_dashboard')
    
    return render(request, 'add_user.html')

@login_required
def edit_user(request, user_id):
    """Edit user - only accessible by organization_admin"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'organization_admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    try:
        user = CustomUser.objects.get(id=user_id, organization=request.user.organization)
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('org_admin_dashboard')
    
    # Prevent editing super admins or other organization admins
    if user.role in ['super_admin', 'organization_admin']:
        messages.error(request, "Cannot edit this user.")
        return redirect('org_admin_dashboard')
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.role = request.POST.get('role', user.role)
        user.phone = request.POST.get('phone', user.phone)
        user.department = request.POST.get('department', user.department)
        user.job_title = request.POST.get('job_title', user.job_title)
        user.is_active = request.POST.get('is_active') == 'on'
        user.save()
        
        messages.success(request, f'User {user.username} updated successfully.')
        
        ActivityLog.objects.create(
            user=request.user,
            organization=request.user.organization,
            action='update',
            module='user_management',
            description=f'Updated user {user.username}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return redirect('org_admin_dashboard')
    
    context = {
        'edit_user': user,
        'user_role': user_role,
    }
    return render(request, 'edit_user.html', context)

@login_required
def reset_user_password(request, user_id):
    """Reset user password - only accessible by organization_admin"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'organization_admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    try:
        user = CustomUser.objects.get(
            id=user_id, 
            organization=request.user.organization
        )
        
        # Prevent resetting passwords for super admins or other organization admins
        if user.role in ['super_admin', 'organization_admin']:
            messages.error(request, "Cannot reset password for this user.")
            return redirect('org_admin_dashboard')
        
        # Generate new temporary password
        temp_password = generate_temp_password()
        
        user.set_password(temp_password)
        user.force_password_change = True
        user.temp_password = temp_password
        user.save()
        
        messages.success(request, 
            f'Password reset for {user.username} successful! '
            f'New temporary password: {temp_password}'
        )
        
        ActivityLog.objects.create(
            user=request.user,
            organization=request.user.organization,
            action='reset_password',
            module='user_management',
            description=f'Reset password for user {user.username}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
    except CustomUser.DoesNotExist:
        messages.error(request, "User not found.")
    
    return redirect('org_admin_dashboard')

# ==================== MODULE VIEWS ====================

@login_required
def analytics(request):
    """Analytics module view with real PostgreSQL data"""
    if not request.user.can_access_module('analytics'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    from .analytics import VehicleAnalytics
    from .models import Vehicle, VehicleMovement, Organization
    
    # Get selected organization from request
    selected_org_id = request.GET.get('organization')
    selected_organization = None
    
    # Super admins can view all organizations, others only their own
    if request.user.role == 'super_admin' or request.user.is_superuser:
        available_organizations = Organization.objects.all()
        if selected_org_id:
            try:
                selected_organization = Organization.objects.get(id=selected_org_id)
            except Organization.DoesNotExist:
                selected_organization = None
    else:
        available_organizations = [request.user.organization] if request.user.organization else []
        selected_organization = request.user.organization
    
    # Initialize analytics for selected organization
    analytics_engine = VehicleAnalytics(organization=selected_organization)
    
    # Get analytics data
    fleet_summary = analytics_engine.get_fleet_summary()
    daily_trips_chart = analytics_engine.get_daily_trips_chart()
    parking_duration_chart = analytics_engine.get_parking_duration_chart()
    driver_performance = analytics_engine.get_driver_performance()
    route_analysis = analytics_engine.get_route_analysis()
    cost_analysis = analytics_engine.get_cost_analysis()
    
    context = {
        'fleet_summary': fleet_summary,
        'daily_trips_chart': daily_trips_chart,
        'parking_duration_chart': parking_duration_chart,
        'hourly_entries_chart': analytics_engine.get_hourly_entries_chart(selected_organization),
        'vehicles_per_site_chart': analytics_engine.get_vehicles_per_site_chart(selected_organization),
        'revenue_per_site_chart': analytics_engine.get_revenue_per_site_chart(selected_organization),
        'visit_patterns_chart': analytics_engine.get_visit_patterns_chart(selected_organization),
        'avg_stay_by_type_chart': analytics_engine.get_avg_stay_by_type_chart(selected_organization),
        'movement_flow_chart': analytics_engine.get_movement_flow_chart(selected_organization),
        'driver_performance': driver_performance,
        'route_analysis': route_analysis,
        'cost_analysis': cost_analysis,
        'available_organizations': available_organizations,
        'selected_organization': selected_organization,
        'has_data': Vehicle.objects.filter(organization=selected_organization).exists() if selected_organization else Vehicle.objects.exists(),
        'is_super_admin': request.user.role == 'super_admin' or request.user.is_superuser,
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='analytics',
        description=f'Accessed analytics module for {selected_organization.name if selected_organization else "all organizations"}',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'analytics.html', context)

@login_required
def inventory(request):
    """Inventory module view"""
    if not request.user.can_access_module('inventory'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Get inventory data
    vehicles = InventoryItem.objects.filter(item_type='vehicle')
    parts = InventoryItem.objects.filter(item_type='part')
    
    context = {
        'vehicles': vehicles,
        'parts': parts,
        'total_vehicles': vehicles.count(),
        'total_parts': parts.count(),
        'low_stock_parts': parts.filter(part_status='low_stock').count(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='inventory',
        description='Accessed inventory module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'inventory.html', context)

@login_required
def add_inventory_item(request):
    """Add new inventory item"""
    if not request.user.can_access_module('inventory'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else request.POST
            
            item_type = data.get('item_type')
            name = data.get('name', '').strip()
            price = data.get('price')
            
            if not name or not price or not item_type:
                return JsonResponse({'success': False, 'error': 'Name, price, and item type are required'}, status=400)
            
            item = InventoryItem.objects.create(
                name=name,
                item_type=item_type,
                description=data.get('description', ''),
                price=float(price),
                created_by=request.user
            )
            
            # Set type-specific fields
            if item_type == 'vehicle':
                item.model = data.get('model', '')
                item.year = int(data.get('year')) if data.get('year') else None
                item.color = data.get('color', '')
                item.vin = data.get('vin', '')
                item.vehicle_status = data.get('vehicle_status', 'available')
            elif item_type == 'part':
                item.part_number = data.get('part_number', '')
                item.category = data.get('category', '')
                item.quantity = int(data.get('quantity', 0))
                item.min_stock_level = int(data.get('min_stock_level', 10))
            
            item.save()
            
            ActivityLog.objects.create(
                user=request.user,
                organization=request.user.organization,
                action='create',
                module='inventory',
                description=f'Added inventory item: {name}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return JsonResponse({
                'success': True,
                'message': f'{item_type.title()} added successfully!',
                'item': {
                    'id': item.id,
                    'name': item.name,
                    'item_type': item.item_type,
                    'price': str(item.price)
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@login_required
def export_inventory_report(request):
    """Export inventory report in CSV or PDF format"""
    if not request.user.can_access_module('inventory'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    export_format = request.GET.get('format', 'csv')
    
    vehicles = InventoryItem.objects.filter(item_type='vehicle')
    parts = InventoryItem.objects.filter(item_type='part')
    
    if export_format == 'csv':
        return export_inventory_csv(vehicles, parts)
    elif export_format == 'pdf':
        return export_inventory_pdf(vehicles, parts)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_inventory_csv(vehicles, parts):
    """Export inventory data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write vehicles section
    writer.writerow(['VEHICLE INVENTORY'])
    writer.writerow(['Name', 'Model', 'Year', 'Color', 'VIN', 'Status', 'Price'])
    
    for vehicle in vehicles:
        writer.writerow([
            vehicle.name,
            vehicle.model or 'N/A',
            vehicle.year or 'N/A',
            vehicle.color or 'N/A',
            vehicle.vin or 'N/A',
            vehicle.get_vehicle_status_display() if vehicle.vehicle_status else 'N/A',
            f'KSh {vehicle.price:,.2f}'
        ])
    
    writer.writerow([])  # Empty row
    
    # Write parts section
    writer.writerow(['PARTS INVENTORY'])
    writer.writerow(['Name', 'Part Number', 'Category', 'Quantity', 'Min Stock', 'Status', 'Price'])
    
    for part in parts:
        writer.writerow([
            part.name,
            part.part_number or 'N/A',
            part.category or 'N/A',
            part.quantity,
            part.min_stock_level,
            part.get_part_status_display() if part.part_status else 'N/A',
            f'KSh {part.price:,.2f}'
        ])
    
    return response

def export_inventory_pdf(vehicles, parts):
    """Export inventory data as PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)
    story.append(Paragraph('Inventory Report', title_style))
    story.append(Paragraph(f'Generated: {timezone.now().strftime("%B %d, %Y at %H:%M")}', styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Vehicles section
    story.append(Paragraph('Vehicle Inventory', styles['Heading2']))
    
    vehicle_data = [['Name', 'Model', 'Year', 'Status', 'Price']]
    for vehicle in vehicles[:20]:  # Limit for PDF
        vehicle_data.append([
            vehicle.name,
            vehicle.model or 'N/A',
            str(vehicle.year) if vehicle.year else 'N/A',
            vehicle.get_vehicle_status_display() if vehicle.vehicle_status else 'N/A',
            f'KSh {vehicle.price:,.0f}'
        ])
    
    vehicle_table = Table(vehicle_data)
    vehicle_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(vehicle_table)
    story.append(Spacer(1, 30))
    
    # Parts section
    story.append(Paragraph('Parts Inventory', styles['Heading2']))
    
    parts_data = [['Name', 'Category', 'Quantity', 'Status', 'Price']]
    for part in parts[:20]:  # Limit for PDF
        parts_data.append([
            part.name,
            part.category or 'N/A',
            str(part.quantity),
            part.get_part_status_display() if part.part_status else 'N/A',
            f'KSh {part.price:,.0f}'
        ])
    
    parts_table = Table(parts_data)
    parts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(parts_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def inventory_settings(request):
    """Inventory settings view"""
    if not request.user.can_access_module('inventory'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('inventory')
    
    context = {
        'user_role': request.user.role,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='inventory_settings',
        description='Accessed inventory settings',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'inventory_settings.html', context)

@login_required
def sales(request):
    """Sales module view"""
    if not request.user.can_access_module('sales'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='sales',
        description='Accessed sales module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'sales.html')

@login_required
def hr_dashboard(request):
    """HR Dashboard module view"""
    if not request.user.can_access_module('hr_dashboard'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    # Super admins see all data, others see only their organization
    if request.user.role == 'super_admin' or request.user.is_superuser:
        all_users = CustomUser.objects.all()
        all_organizations = Organization.objects.all()
        organization = None
    else:
        organization = request.user.organization
        all_users = CustomUser.objects.filter(organization=organization)
        all_organizations = Organization.objects.filter(id=organization.id) if organization else Organization.objects.none()
    
    # HR Statistics
    total_employees = all_users.count()
    active_employees = all_users.filter(is_active=True).count()
    inactive_employees = total_employees - active_employees
    
    # Role distribution
    role_stats = {}
    for role_code, role_name in CustomUser.ROLE_CHOICES:
        count = all_users.filter(role=role_code).count()
        if count > 0:
            role_stats[role_name] = count
    
    # Department distribution
    dept_stats = {}
    departments = all_users.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()
    for dept in departments:
        count = all_users.filter(department=dept).count()
        dept_stats[dept] = count
    
    # Organization statistics
    org_stats = {}
    for org in all_organizations:
        user_count = all_users.filter(organization=org).count()
        org_stats[org.name] = user_count
    
    # Recent hires (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_hires = all_users.filter(date_joined__gte=thirty_days_ago).order_by('-date_joined')[:10]
    
    # Users with profiles
    if organization:
        users_with_profiles = UserProfile.objects.filter(user__organization=organization).count()
    else:
        users_with_profiles = UserProfile.objects.count()
    profile_completion_rate = (users_with_profiles / total_employees * 100) if total_employees > 0 else 0
    
    # Document statistics
    if organization:
        total_documents = Document.objects.filter(user__organization=organization).count()
        verified_documents = Document.objects.filter(user__organization=organization, is_verified=True).count()
    else:
        total_documents = Document.objects.count()
        verified_documents = Document.objects.filter(is_verified=True).count()
    
    # Recent activities (HR related)
    if organization:
        recent_activities = ActivityLog.objects.filter(
            organization=organization,
            module__in=['profile', 'user_management', 'hr_dashboard']
        ).order_by('-timestamp')[:15]
    else:
        recent_activities = ActivityLog.objects.filter(
            module__in=['profile', 'user_management', 'hr_dashboard']
        ).order_by('-timestamp')[:15]
    
    # Users needing attention
    users_needing_attention = []
    for user in all_users[:20]:
        issues = []
        profile = getattr(user, 'profile', None)
        
        if not profile:
            issues.append('No profile created')
        else:
            if not profile.date_of_birth:
                issues.append('Missing date of birth')
            if not profile.mobile_phone and not user.phone:
                issues.append('Missing phone number')
            if not profile.address_line1:
                issues.append('Missing address')
        
        expired_docs = Document.objects.filter(
            user=user, 
            expires_at__lt=timezone.now().date()
        ).count()
        if expired_docs > 0:
            issues.append(f'{expired_docs} expired document(s)')
        
        if issues:
            users_needing_attention.append({
                'user': user,
                'issues': issues
            })
    
    context = {
        'organization': organization,
        'all_organizations': all_organizations,
        'total_employees': total_employees,
        'active_employees': active_employees,
        'inactive_employees': inactive_employees,
        'role_stats': role_stats,
        'dept_stats': dept_stats,
        'org_stats': org_stats,
        'recent_hires': recent_hires,
        'profile_completion_rate': round(profile_completion_rate, 1),
        'total_documents': total_documents,
        'verified_documents': verified_documents,
        'recent_activities': recent_activities,
        'users_needing_attention': users_needing_attention[:10],
        'all_users': all_users.order_by('-date_joined')[:50],
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='hr_dashboard',
        description='Accessed HR dashboard',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'hr_dashboard.html', context)

@login_required
def hr_settings(request):
    """HR Settings view"""
    if not request.user.can_access_module('hr_dashboard'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    organization = request.user.organization
    
    # Get HR-related settings
    context = {
        'organization': organization,
        'user_role': request.user.role,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='hr_settings',
        description='Accessed HR settings',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'hr_settings.html', context)
    


@login_required
def export_org_admin_report(request):
    """Export organization admin report in CSV or PDF format"""
    if request.user.role != 'organization_admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    export_format = request.GET.get('format', 'csv')
    organization = request.user.organization
    
    if not organization:
        return JsonResponse({'error': 'No organization assigned'}, status=400)
    
    # Get organization data
    users = CustomUser.objects.filter(organization=organization).select_related('organization')
    
    if export_format == 'csv':
        return export_org_admin_csv(users, organization)
    elif export_format == 'pdf':
        return export_org_admin_pdf(users, organization)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_org_admin_csv(users, organization):
    """Export organization admin data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{organization.slug}_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write organization info
    writer.writerow(['ORGANIZATION REPORT'])
    writer.writerow(['Organization Name', organization.name])
    writer.writerow(['Email', organization.email])
    writer.writerow(['Phone', organization.phone or 'N/A'])
    writer.writerow(['Status', 'Active' if organization.is_active else 'Inactive'])
    writer.writerow(['Created Date', organization.created_at.strftime('%Y-%m-%d')])
    writer.writerow([])
    
    # Write employees section
    writer.writerow(['EMPLOYEES REPORT'])
    writer.writerow([
        'Username', 'Full Name', 'Email', 'Role', 'Department', 
        'Status', 'Join Date', 'Last Active', 'Phone'
    ])
    
    for user in users:
        writer.writerow([
            user.username,
            user.get_full_name() or 'N/A',
            user.email,
            user.get_role_display(),
            user.department or 'N/A',
            'Active' if user.is_active else 'Inactive',
            user.date_joined.strftime('%Y-%m-%d'),
            user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else 'Never',
            user.phone or 'N/A'
        ])
    
    return response

def export_org_admin_pdf(users, organization):
    """Export organization admin data as PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph(f'{organization.name} - Organization Report', title_style))
    story.append(Paragraph(f'Generated on: {timezone.now().strftime("%B %d, %Y at %H:%M")}', styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Organization info
    story.append(Paragraph('Organization Information', styles['Heading2']))
    org_info = [
        ['Organization Name', organization.name],
        ['Email', organization.email],
        ['Phone', organization.phone or 'N/A'],
        ['Status', 'Active' if organization.is_active else 'Inactive'],
        ['Created Date', organization.created_at.strftime('%Y-%m-%d')],
        ['Total Users', str(users.count())]
    ]
    
    org_table = Table(org_info)
    org_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(org_table)
    story.append(Spacer(1, 30))
    
    # Employees section
    story.append(Paragraph('Employees Overview', styles['Heading2']))
    
    emp_data = [['Username', 'Name', 'Role', 'Status', 'Join Date']]
    for user in users[:50]:
        emp_data.append([
            user.username,
            user.get_full_name() or 'N/A',
            user.get_role_display(),
            'Active' if user.is_active else 'Inactive',
            user.date_joined.strftime('%Y-%m-%d')
        ])
    
    emp_table = Table(emp_data)
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(emp_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{organization.slug}_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def org_admin_dashboard_layer2(request):
    """Second layer dashboard with fix issues boxes"""
    user_role = getattr(request.user, 'role', 'employee')
    
    if user_role != 'organization_admin':
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if not request.user.organization:
        messages.error(request, "You are not assigned to any organization.")
        return redirect('dashboard')
    
    organization = request.user.organization
    users = CustomUser.objects.filter(organization=organization).exclude(role='super_admin')
    
    # Issues analysis
    issues_data = {
        'incomplete_profiles': [],
        'expired_documents': [],
        'inactive_users': [],
        'missing_departments': [],
        'password_issues': []
    }
    
    for user in users:
        profile = getattr(user, 'profile', None)
        
        # Check incomplete profiles
        if not profile or not profile.date_of_birth or not profile.address_line1:
            issues_data['incomplete_profiles'].append(user)
        
        # Check expired documents
        expired_docs = Document.objects.filter(
            user=user, 
            expires_at__lt=timezone.now().date()
        ).count()
        if expired_docs > 0:
            issues_data['expired_documents'].append({'user': user, 'count': expired_docs})
        
        # Check inactive users
        if not user.is_active:
            issues_data['inactive_users'].append(user)
        
        # Check missing departments
        if not user.department:
            issues_data['missing_departments'].append(user)
        
        # Check password issues (temp passwords)
        if hasattr(user, 'force_password_change') and user.force_password_change:
            issues_data['password_issues'].append(user)
    
    context = {
        'organization': organization,
        'issues_data': issues_data,
        'total_users': users.count(),
        'user_role': user_role,
        'now': timezone.now(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=organization,
        action='view',
        module='org_admin_dashboard_layer2',
        description='Accessed organization admin dashboard layer 2',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'org_admin_dashboard_layer2.html', context)

@login_required
def export_hr_report(request):
    """Export HR report in CSV or PDF format"""
    if not request.user.can_access_module('hr_dashboard'):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    export_format = request.GET.get('format', 'csv')
    
    # Get data based on user role
    if request.user.role == 'super_admin' or request.user.is_superuser:
        all_users = CustomUser.objects.all().select_related('organization')
        all_organizations = Organization.objects.all()
    else:
        organization = request.user.organization
        all_users = CustomUser.objects.filter(organization=organization).select_related('organization')
        all_organizations = Organization.objects.filter(id=organization.id) if organization else Organization.objects.none()
    
    if export_format == 'csv':
        return export_hr_csv(all_users, all_organizations)
    elif export_format == 'pdf':
        return export_hr_pdf(all_users, all_organizations)
    else:
        return JsonResponse({'error': 'Invalid format'}, status=400)

def export_hr_csv(users, organizations):
    """Export HR data as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="hr_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # Write organizations section
    writer.writerow(['ORGANIZATIONS REPORT'])
    writer.writerow(['Organization Name', 'Email', 'Phone', 'Status', 'Created Date', 'Total Users'])
    
    for org in organizations:
        user_count = users.filter(organization=org).count()
        writer.writerow([
            org.name,
            org.email,
            org.phone or 'N/A',
            'Active' if org.is_active else 'Inactive',
            org.created_at.strftime('%Y-%m-%d'),
            user_count
        ])
    
    writer.writerow([])  # Empty row
    
    # Write employees section
    writer.writerow(['EMPLOYEES REPORT'])
    writer.writerow([
        'Username', 'Full Name', 'Email', 'Role', 'Department', 
        'Organization', 'Status', 'Join Date', 'Last Active', 'Phone'
    ])
    
    for user in users:
        writer.writerow([
            user.username,
            user.get_full_name() or 'N/A',
            user.email,
            user.get_role_display(),
            user.department or 'N/A',
            user.organization.name if user.organization else 'N/A',
            'Active' if user.is_active else 'Inactive',
            user.date_joined.strftime('%Y-%m-%d'),
            user.last_active.strftime('%Y-%m-%d %H:%M') if user.last_active else 'Never',
            user.phone or 'N/A'
        ])
    
    return response

def export_hr_pdf(users, organizations):
    """Export HR data as PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph('HR Dashboard Report', title_style))
    story.append(Paragraph(f'Generated on: {timezone.now().strftime("%B %d, %Y at %H:%M")}', styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Organizations section
    story.append(Paragraph('Organizations Overview', styles['Heading2']))
    
    org_data = [['Organization', 'Email', 'Status', 'Users', 'Created']]
    for org in organizations:
        user_count = users.filter(organization=org).count()
        org_data.append([
            org.name,
            org.email,
            'Active' if org.is_active else 'Inactive',
            str(user_count),
            org.created_at.strftime('%Y-%m-%d')
        ])
    
    org_table = Table(org_data)
    org_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(org_table)
    story.append(Spacer(1, 30))
    
    # Employees section
    story.append(Paragraph('Employees Overview', styles['Heading2']))
    
    emp_data = [['Username', 'Name', 'Role', 'Organization', 'Status', 'Join Date']]
    for user in users[:50]:  # Limit to prevent PDF size issues
        emp_data.append([
            user.username,
            user.get_full_name() or 'N/A',
            user.get_role_display(),
            user.organization.name if user.organization else 'N/A',
            'Active' if user.is_active else 'Inactive',
            user.date_joined.strftime('%Y-%m-%d')
        ])
    
    emp_table = Table(emp_data)
    emp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(emp_table)
    
    # Statistics
    story.append(Spacer(1, 30))
    story.append(Paragraph('Summary Statistics', styles['Heading2']))
    
    stats_data = [
        ['Total Organizations', str(organizations.count())],
        ['Total Employees', str(users.count())],
        ['Active Employees', str(users.filter(is_active=True).count())],
        ['Inactive Employees', str(users.filter(is_active=False).count())]
    ]
    
    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(stats_table)
    
    doc.build(story)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="hr_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def ai_assistant(request):
    """AI Assistant for vehicle movement tracking"""
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='ai_assistant',
        description='Accessed AI Assistant',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'ai_assistant.html')

@login_required
def vehicle_tracking(request):
    """Vehicle tracking view"""
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='vehicle_tracking',
        description='Accessed vehicle tracking',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'vehicle_tracking.html')

@login_required
def movement_history(request):
    """Movement history view"""
    context = {
        'today': timezone.now().date(),
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='movement_history',
        description='Accessed movement history',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'movement_history.html', context)

@login_required
def reports(request):
    """Reports module view"""
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='reports',
        description='Accessed reports module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'reports.html')

@login_required
def generate_vehicle_report(request, report_type):
    """Generate vehicle movement report as PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Report data
    report_configs = {
        'movement_summary': {
            'title': 'Vehicle Movement Summary Report',
            'data': [['Metric', 'Value'], ['Total Distance', '298.4 km'], ['Total Trips', '28'], ['Avg Duration', '18 min']]
        },
        'route_analysis': {
            'title': 'Route Analysis Report', 
            'data': [['Route', 'Frequency'], ['Home → Office', '14 times'], ['Office → Home', '14 times']]
        },
        'parking_costs': {
            'title': 'Parking Cost Report',
            'data': [['Period', 'Visits', 'Total Cost'], ['This Week', '15', 'KSh 1,350'], ['Last Week', '12', 'KSh 1,080']]
        },
        'weekly_summary': {
            'title': 'Weekly Summary Report',
            'data': [['Day', 'Trips', 'Distance'], ['Monday', '4', '42.6 km'], ['Tuesday', '5', '38.9 km']]
        },
        'performance_metrics': {
            'title': 'Performance Metrics Report',
            'data': [['Metric', 'Value', 'Target'], ['Avg Speed', '45.2 km/h', '50 km/h'], ['Fuel Efficiency', '12.5 km/L', '13 km/L']]
        },
        'location_history': {
            'title': 'Location History Report',
            'data': [['Location', 'Visits', 'Duration'], ['Home', '28', '168h 30m'], ['Office', '28', '224h 15m']]
        }
    }
    
    config = report_configs.get(report_type, report_configs['movement_summary'])
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)
    story.append(Paragraph(config['title'], title_style))
    story.append(Paragraph(f'Generated: {timezone.now().strftime("%B %d, %Y at %H:%M")}', styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Table
    table = Table(config['data'])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='export',
        module='reports',
        description=f'Generated {report_type} report',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
    
    return response

@login_required
def purchasing(request):
    """Purchasing module view"""
    if not request.user.can_access_module('purchasing'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='purchasing',
        description='Accessed purchasing module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'purchasing.html')

@login_required
def manufacturing(request):
    """Manufacturing module view"""
    if not request.user.can_access_module('manufacturing'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='manufacturing',
        description='Accessed manufacturing module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'manufacturing.html')

@login_required
def online_store(request):
    """Online Store module view"""
    if not request.user.can_access_module('online_store'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='online_store',
        description='Accessed online store module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'online_store.html')

@login_required
def store_management(request):
    """Store Management module view"""
    if not request.user.can_access_module('store_management'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='store_management',
        description='Accessed store management module',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'store_management.html')

# ==================== SYSTEM VIEWS ====================

@login_required
def help_center(request):
    """Help Center view"""
    if not request.user.can_access_module('help_center'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='help_center',
        description='Accessed help center',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'help_center.html')

@login_required
def settings(request):
    """Settings view"""
    if not request.user.can_access_module('settings'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    context = {
        'user': request.user,
        'organization': request.user.organization,
        'user_role': request.user.role,
    }
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='view',
        module='settings',
        description='Accessed settings',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'settings.html', context)

@login_required
def update_profile(request):
    """Update user profile information"""
    if not request.user.can_access_module('profile_settings'):
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        job_title = request.POST.get('job_title', '').strip()
        department = request.POST.get('department', '').strip()
        
        # Validate required fields
        if not first_name or not last_name:
            messages.error(request, 'First name and last name are required.')
            return redirect('settings')
        
        if not email:
            messages.error(request, 'Email is required.')
            return redirect('settings')
        
        # Check if email is being changed and if it's unique
        if email != request.user.email:
            if CustomUser.objects.filter(email=email).exclude(id=request.user.id).exists():
                messages.error(request, 'This email is already in use by another account.')
                return redirect('settings')
        
        # Update user
        try:
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.phone = phone
            request.user.job_title = job_title
            request.user.department = department
            request.user.save()
            
            messages.success(request, 'Profile updated successfully!')
            
            # Log the activity
            ActivityLog.objects.create(
                user=request.user,
                organization=request.user.organization,
                action='update',
                module='profile',
                description='Updated profile information',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return redirect('settings')


# views.py - Add these views

@login_required
def profile_view(request):
    """Main profile view for users"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    # If profile doesn't exist, create it
    if not profile:
        from django.db import transaction
        with transaction.atomic():
            profile = UserProfile.objects.create(user=user)
            ActivityLog.objects.create(
                user=user,
                organization=user.organization,
                action='create',
                module='profile',
                description='Profile created',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
    
    # Get user documents
    documents = Document.objects.filter(user=user).order_by('-uploaded_at')
    
    # Get recent notifications
    notifications_qs = Notification.objects.filter(user=user).order_by('-created_at')
    notifications = notifications_qs[:10]
    unread_notifications = notifications_qs.filter(is_read=False).count()

    
    # Get profile audit logs
    audit_logs = ProfileAuditLog.objects.filter(profile=profile).order_by('-timestamp')[:20]
    
    # Get activity logs
    recent_activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')[:15]
    
    context = {
        'profile': profile,
        'documents': documents,
        'notifications': notifications,
        'unread_notifications': unread_notifications,
        'audit_logs': audit_logs,
        'recent_activities': recent_activities,
        'now': timezone.now(),
    }
    
    # Log profile view
    ActivityLog.objects.create(
        user=user,
        organization=user.organization,
        action='view',
        module='profile',
        description='Viewed profile',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Create audit log for profile view
    ProfileAuditLog.objects.create(
        profile=profile,
        changed_by=user,
        action='viewed',
        field_changed='profile',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'profile/profile.html', context)


@login_required
def edit_profile(request):
    """Edit profile information"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if not profile:
        profile = UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        try:
            old_data = {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone,
                'job_title': user.job_title,
                'department': user.department,
            }
            
            # Update basic user info
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            user.phone = request.POST.get('phone', user.phone)
            user.job_title = request.POST.get('job_title', user.job_title)
            user.department = request.POST.get('department', user.department)
            
            # Update profile info
            profile_fields = [
                'date_of_birth', 'gender', 'alternate_email', 'mobile_phone',
                'work_phone', 'emergency_contact', 'emergency_phone',
                'address_line1', 'address_line2', 'city', 'state',
                'postal_code', 'country', 'linkedin_url', 'twitter_handle',
                'github_username', 'personal_website', 'timezone',
                'language', 'theme_preference'
            ]
            
            profile_old_data = {}
            for field in profile_fields:
                old_value = getattr(profile, field)
                new_value = request.POST.get(field, old_value)
                
                if field in ['date_of_birth'] and new_value:
                    try:
                        new_value = datetime.strptime(new_value, '%Y-%m-%d').date()
                    except:
                        new_value = old_value
                
                if str(old_value) != str(new_value):
                    profile_old_data[field] = old_value
                    setattr(profile, field, new_value)
            
            # Save changes
            user.save()
            profile.save()
            
            # Create audit logs for changed fields
            for field, old_value in profile_old_data.items():
                ProfileAuditLog.objects.create(
                    profile=profile,
                    changed_by=user,
                    action='updated',
                    field_changed=field,
                    old_value=str(old_value),
                    new_value=str(getattr(profile, field)),
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            
            messages.success(request, 'Profile updated successfully!')
            
            ActivityLog.objects.create(
                user=user,
                organization=user.organization,
                action='update',
                module='profile',
                description='Updated profile information',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return redirect('profile_view')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    context = {
        'profile': profile,
        'countries': [
            'United States', 'Canada', 'United Kingdom', 'Australia', 'Germany',
            'France', 'Japan', 'China', 'India', 'Brazil', 'Mexico', 'South Africa'
        ],
        'timezones': [
            'UTC', 'America/New_York', 'America/Chicago', 'America/Denver',
            'America/Los_Angeles', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo',
            'Asia/Dubai', 'Australia/Sydney'
        ],
        'languages': [
            ('en', 'English'),
            ('es', 'Spanish'),
            ('fr', 'French'),
            ('de', 'German'),
            ('ja', 'Japanese'),
            ('zh', 'Chinese'),
            ('hi', 'Hindi'),
            ('ar', 'Arabic')
        ]
    }
    
    return render(request, 'profile/edit_profile.html', context)


@login_required
def upload_profile_picture(request):
    """Upload or update profile picture"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        user = request.user
        profile = getattr(user, 'profile', None)
        
        if not profile:
            profile = UserProfile.objects.create(user=user)
        
        try:
            # Delete old profile picture if exists
            if profile.profile_picture:
                profile.profile_picture.delete()
            
            # Save new profile picture
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            
            # Log the activity
            ActivityLog.objects.create(
                user=user,
                organization=user.organization,
                action='update',
                module='profile',
                description='Updated profile picture',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, 'Profile picture updated successfully!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            messages.error(request, f'Error updating profile picture: {str(e)}')
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_profile_picture(request):
    """Delete profile picture"""
    if request.method == 'POST':
        user = request.user
        profile = getattr(user, 'profile', None)
        
        if profile and profile.profile_picture:
            try:
                profile.profile_picture.delete()
                profile.save()
                
                # Log the activity
                ActivityLog.objects.create(
                    user=user,
                    organization=user.organization,
                    action='delete',
                    module='profile',
                    description='Deleted profile picture',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                messages.success(request, 'Profile picture removed successfully!')
                return JsonResponse({'success': True})
                
            except Exception as e:
                messages.error(request, f'Error removing profile picture: {str(e)}')
                return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def upload_document(request):
    """Upload user document"""
    if request.method == 'POST':
        user = request.user
        
        name = request.POST.get('name', '').strip()
        document_type = request.POST.get('document_type', 'other')
        description = request.POST.get('description', '').strip()
        expires_at = request.POST.get('expires_at', None)
        
        if not name or not request.FILES.get('file'):
            messages.error(request, 'Document name and file are required.')
            return redirect('profile_view')
        
        try:
            expires_date = None
            if expires_at:
                expires_date = datetime.strptime(expires_at, '%Y-%m-%d').date()
            
            document = Document.objects.create(
                user=user,
                name=name,
                document_type=document_type,
                file=request.FILES['file'],
                description=description,
                uploaded_by=user,
                expires_at=expires_date
            )
            
            ActivityLog.objects.create(
                user=user,
                organization=user.organization,
                action='create',
                module='documents',
                description=f'Uploaded document: {name}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, 'Document uploaded successfully!')
            
        except Exception as e:
            messages.error(request, f'Error uploading document: {str(e)}')
    
    return redirect('profile_view')


@login_required
def delete_document(request, document_id):
    """Delete user document"""
    try:
        document = Document.objects.get(id=document_id, user=request.user)
        document_name = document.name
        document.delete()
        
        ActivityLog.objects.create(
            user=request.user,
            organization=request.user.organization,
            action='delete',
            module='documents',
            description=f'Deleted document: {document_name}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(request, 'Document deleted successfully!')
        
    except Document.DoesNotExist:
        messages.error(request, 'Document not found.')
    
    return redirect('profile_view')


@login_required
@require_POST
def update_notification_preferences(request):
    """Update notification preferences"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if not profile:
        profile = UserProfile.objects.create(user=user)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        profile.email_notifications = data.get('email_notifications', 'true') == 'true'
        profile.sms_notifications = data.get('sms_notifications', 'false') == 'true'
        profile.push_notifications = data.get('push_notifications', 'true') == 'true'
        profile.save()
        
        ProfileAuditLog.objects.create(
            profile=profile,
            changed_by=user,
            action='updated',
            field_changed='notification_preferences',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        ActivityLog.objects.create(
            user=user,
            organization=user.organization,
            action='update',
            module='profile',
            description='Updated notification preferences',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification preferences updated successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def update_security_settings(request):
    """Update security settings"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if not profile:
        profile = UserProfile.objects.create(user=user)
    
    try:
        data = json.loads(request.body) if request.body else request.POST
        
        # Update two-factor authentication
        if 'two_factor_enabled' in data:
            profile.two_factor_enabled = data['two_factor_enabled'] == 'true'
        
        profile.save()
        
        ProfileAuditLog.objects.create(
            profile=profile,
            changed_by=user,
            action='updated',
            field_changed='security_settings',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        ActivityLog.objects.create(
            user=user,
            organization=user.organization,
            action='update',
            module='profile',
            description='Updated security settings',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Security settings updated successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        
        ActivityLog.objects.create(
            user=request.user,
            organization=request.user.organization,
            action='update',
            module='notifications',
            description='Marked notification as read',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({'success': True})
        
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    notifications = Notification.objects.filter(user=request.user, is_read=False)
    count = notifications.count()
    
    notifications.update(is_read=True, read_at=timezone.now())
    
    ActivityLog.objects.create(
        user=request.user,
        organization=request.user.organization,
        action='update',
        module='notifications',
        description=f'Marked {count} notifications as read',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return JsonResponse({'success': True, 'count': count})


@login_required
def get_unread_notifications_count(request):
    """Get count of unread notifications"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def generate_sample_data(request):
    """Generate sample vehicle data for testing analytics"""
    if not request.user.can_access_module('analytics'):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        from .analytics import generate_sample_data
        
        organization = request.user.organization
        if not organization:
            return JsonResponse({'success': False, 'error': 'No organization assigned'}, status=400)
        
        result = generate_sample_data(organization)
        
        ActivityLog.objects.create(
            user=request.user,
            organization=organization,
            action='create',
            module='analytics',
            description='Generated sample vehicle data',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': result
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def activity_logs(request):
    """Get user activity logs"""
    logs = ActivityLog.objects.filter(user=request.user).order_by('-timestamp')
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 20)
    paginator = Paginator(logs, per_page)
    
    try:
        logs_page = paginator.page(page)
    except:
        logs_page = paginator.page(1)
    
    logs_data = []
    for log in logs_page.object_list:
        logs_data.append({
            'id': log.id,
            'action': log.get_action_display(),
            'module': log.module,
            'description': log.description,
            'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'time_ago': log.timestamp.strftime('%b %d, %Y %I:%M %p'),
            'ip_address': log.ip_address,
            'organization': log.organization.name if log.organization else None,
        })
    
    return JsonResponse({
        'success': True,
        'activities': logs_data,
        'total_pages': paginator.num_pages,
        'current_page': logs_page.number,
        'total_count': paginator.count,
    })


@login_required
def vehicle_analytics_api(request):
    """API endpoint for vehicle analytics by license plate"""
    plate_number = request.GET.get('plate', '').strip().upper()
    
    if not plate_number:
        return JsonResponse({'success': False, 'error': 'License plate number is required'}, status=400)
    
    try:
        from .models import Vehicle, VehicleMovement
        from django.db.models import Sum, Count, Avg, Max
        
        # Find vehicle by license plate (case-insensitive search)
        try:
            vehicle = Vehicle.objects.get(license_plate__iexact=plate_number)
        except Vehicle.DoesNotExist:
            # Also try searching by vehicle_id as fallback
            try:
                vehicle = Vehicle.objects.get(vehicle_id__iexact=plate_number)
            except Vehicle.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Vehicle not found'}, status=404)
        
        # Allow access for regular users (employees) to search any vehicle
        # Only restrict for organization admins to their own organization
        if (request.user.role == 'organization_admin' and 
            request.user.organization and 
            vehicle.organization != request.user.organization):
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Get all movements for this vehicle
        movements = VehicleMovement.objects.filter(vehicle=vehicle)
        
        if not movements.exists():
            return JsonResponse({'success': False, 'error': 'No movement data found'}, status=404)
        
        # Calculate analytics
        total_visits = movements.count()
        total_amount = movements.aggregate(total=Sum('fuel_consumed_liters'))['total'] or 0  # Using fuel as amount proxy
        total_time_minutes = movements.aggregate(total=Sum('duration_minutes'))['total'] or 0
        total_time_hours = total_time_minutes / 60
        
        # Get unique destinations
        destinations_data = movements.values('end_location').annotate(
            visits=Count('id'),
            total_time_minutes=Sum('duration_minutes'),
            total_amount=Sum('fuel_consumed_liters'),
            last_visit=Max('start_time')
        ).order_by('-visits')
        
        unique_destinations = destinations_data.count()
        
        # Format destinations data
        destinations = []
        for dest in destinations_data:
            total_minutes = dest['total_time_minutes'] or 0
            avg_minutes = total_minutes / dest['visits'] if dest['visits'] > 0 else 0
            
            destinations.append({
                'destination': dest['end_location'],
                'visits': dest['visits'],
                'total_time_hours': total_minutes / 60,
                'total_time_minutes': total_minutes % 60,
                'avg_time_hours': avg_minutes / 60,
                'avg_time_minutes': avg_minutes % 60,
                'total_amount': (dest['total_amount'] or 0) * 150,  # Convert to KSh estimate
                'last_visit': dest['last_visit'].isoformat() if dest['last_visit'] else None
            })
        
        analytics_data = {
            'total_visits': total_visits,
            'total_amount': total_amount * 150,  # Convert to KSh estimate
            'total_time_hours': total_time_hours,
            'unique_destinations': unique_destinations,
            'destinations': destinations
        }
        
        # Log the analytics access
        ActivityLog.objects.create(
            user=request.user,
            organization=request.user.organization,
            action='view',
            module='vehicle_analytics',
            description=f'Viewed analytics for vehicle {plate_number}',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'analytics': analytics_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error retrieving analytics: {str(e)}'
        }, status=500)

@login_required
def export_profile_data(request):
    """Export profile data in JSON format"""
    user = request.user
    profile = getattr(user, 'profile', None)
    
    if not profile:
        return JsonResponse({'error': 'Profile not found'}, status=404)
    
    # Collect all profile data
    profile_data = {
        'user': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        },
        'profile': {
            'personal_info': {
                'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                'gender': profile.gender,
                'age': profile.age,
            },
            'contact_info': {
                'phone': user.phone,
                'alternate_email': profile.alternate_email,
                'mobile_phone': profile.mobile_phone,
                'work_phone': profile.work_phone,
                'emergency_contact': profile.emergency_contact,
                'emergency_phone': profile.emergency_phone,
                'full_address': profile.get_full_address(),
            },
            'professional_info': {
                'employee_id': profile.employee_id,
                'job_title': user.job_title,
                'department': user.department,
                'hire_date': profile.hire_date.isoformat() if profile.hire_date else None,
                'employment_type': profile.employment_type,
                'manager': profile.manager.user.username if profile.manager else None,
            },
            'social_links': {
                'linkedin': profile.linkedin_url,
                'twitter': profile.twitter_handle,
                'github': profile.github_username,
                'website': profile.personal_website,
            },
            'preferences': {
                'timezone': profile.timezone,
                'language': profile.language,
                'theme': profile.theme_preference,
                'notifications': {
                    'email': profile.email_notifications,
                    'sms': profile.sms_notifications,
                    'push': profile.push_notifications,
                }
            },
            'security': {
                'two_factor_enabled': profile.two_factor_enabled,
                'last_password_change': profile.last_password_change.isoformat() if profile.last_password_change else None,
            }
        },
        'metadata': {
            'exported_at': timezone.now().isoformat(),
            'exported_by': user.username,
            'format': 'json',
        }
    }
    
    # Log the export
    ActivityLog.objects.create(
        user=user,
        organization=user.organization,
        action='export',
        module='profile',
        description='Exported profile data',
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Create response
    response = JsonResponse(profile_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="profile_data_{user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
    return response