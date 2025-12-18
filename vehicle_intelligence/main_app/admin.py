from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Organization, ActivityLog, UserPermission

# ========== COMPLETELY HIDE ALL MODELS FROM DJANGO ADMIN ==========

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False
    
    def has_view_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    def has_module_permission(self, request):
        return False
    
    def has_view_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return False
    
    def has_view_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

# Hide UserPermission from admin completely
admin.site.unregister(UserPermission) if UserPermission in admin.site._registry else None

# Customize admin site to completely hide it
admin.site.site_header = '🚫 USE HTML DASHBOARD INSTEAD'
admin.site.site_title = '🚫 Management via HTML Dashboard Only'
admin.site.index_title = '🚫 All management must be done through the HTML dashboard'


# admin.py
from django.contrib import admin
from .models import UserProfile, ProfileAuditLog, Document, Notification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'job_title', 'department', 'two_factor_enabled']
    list_filter = ['two_factor_enabled', 'employment_type', 'gender']
    search_fields = ['user__username', 'user__email', 'employee_id', 'job_title']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('user', 'date_of_birth', 'gender')
        }),
        ('Contact Information', {
            'fields': ('alternate_email', 'mobile_phone', 'work_phone', 
                      'emergency_contact', 'emergency_phone')
        }),
        ('Address Information', {
            'fields': ('address_line1', 'address_line2', 'city', 
                      'state', 'postal_code', 'country')
        }),
        ('Professional Information', {
            'fields': ('employee_id', 'hire_date', 'job_title', 'department',
                      'manager', 'employment_type')
        }),
        ('Social Media', {
            'fields': ('linkedin_url', 'twitter_handle', 'github_username', 'personal_website')
        }),
        ('Preferences', {
            'fields': ('profile_picture', 'timezone', 'language', 'theme_preference')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'sms_notifications', 'push_notifications')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'last_password_change',
                      'account_locked', 'lock_reason', 'locked_until')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_updated_by')
        })
    )

@admin.register(ProfileAuditLog)
class ProfileAuditLogAdmin(admin.ModelAdmin):
    list_display = ['profile', 'action', 'field_changed', 'changed_by', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['profile__user__username', 'field_changed', 'changed_by__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'document_type', 'uploaded_at', 'is_verified', 'is_expired']
    list_filter = ['document_type', 'is_verified', 'uploaded_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['uploaded_at', 'uploaded_by']
    date_hierarchy = 'uploaded_at'
    
    def is_expired(self, obj):
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'