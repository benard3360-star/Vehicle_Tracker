# urls.py - Update with profile URLs

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login, name='home'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Profile Management
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/upload-picture/', views.upload_profile_picture, name='upload_profile_picture'),
    path('profile/delete-picture/', views.delete_profile_picture, name='delete_profile_picture'),
    path('profile/upload-document/', views.upload_document, name='upload_document'),
    path('profile/delete-document/<int:document_id>/', views.delete_document, name='delete_document'),
    path('profile/update-notifications/', views.update_notification_preferences, name='update_notification_preferences'),
    path('profile/update-security/', views.update_security_settings, name='update_security_settings'),
    path('profile/mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('profile/mark-all-notifications-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('profile/unread-notifications-count/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
    path('profile/activity-logs/', views.activity_logs, name='activity_logs'),
    path('profile/export/', views.export_profile_data, name='export_profile_data'),
    
    # Super Admin
    path('super-admin-dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/organizations/', views.super_admin_organizations_view, name='super_admin_organizations'),
    path('super-admin/users/', views.super_admin_users_view, name='super_admin_users'),
    path('super-admin/activities/', views.super_admin_activities_view, name='super_admin_activities'),
    
    # Super Admin API Endpoints
    path('super-admin/create-org/', views.super_admin_create_organization, name='super_admin_create_org'),
    path('super-admin/create-org-admin/', views.super_admin_create_org_admin, name='super_admin_create_org_admin'),
    path('super-admin/create-super-admin/', views.super_admin_create_super_admin, name='super_admin_create_super_admin'),
    path('super-admin/reset-user-password/', views.super_admin_reset_user_password, name='super_admin_reset_user_password'),
    path('super-admin/delete-user/', views.super_admin_delete_user, name='super_admin_delete_user'),
    path('super-admin/delete-organization/', views.super_admin_delete_organization, name='super_admin_delete_organization'),
    path('super-admin/organizations/api/', views.super_admin_organizations_api, name='super_admin_organizations_api'),
    
    # Organization Admin
    path('org-admin/dashboard/', views.org_admin_dashboard, name='org_admin_dashboard'),
    path('org-admin/dashboard/layer2/', views.org_admin_dashboard_layer2, name='org_admin_dashboard_layer2'),
    path('org-admin/export-report/', views.export_org_admin_report, name='export_org_admin_report'),
    path('org-admin/add-user/', views.add_user, name='add_user'),
    path('org-admin/edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('org-admin/reset-password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    
    # Vehicle Intelligence Views
    path('vehicle-tracking/', views.vehicle_tracking, name='vehicle_tracking'),
    path('movement-history/', views.movement_history, name='movement_history'),
    path('ai-assistant/', views.ai_assistant, name='ai_assistant'),
    path('reports/', views.reports, name='reports'),
    path('reports/generate/<str:report_type>/', views.generate_vehicle_report, name='generate_vehicle_report'),
    
    # Vehicle Analytics API
    path('api/vehicle-analytics/', views.vehicle_analytics_api, name='vehicle_analytics_api'),
    
    # Admin Module Views (for admin roles)
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/generate-sample-data/', views.generate_sample_data, name='generate_sample_data'),
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/add/', views.add_inventory_item, name='add_inventory_item'),
    path('inventory/export/', views.export_inventory_report, name='export_inventory_report'),
    path('inventory/settings/', views.inventory_settings, name='inventory_settings'),
    path('sales/', views.sales, name='sales'),
    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('hr-dashboard/export/', views.export_hr_report, name='export_hr_report'),
    path('hr-dashboard/settings/', views.hr_settings, name='hr_settings'),
    path('purchasing/', views.purchasing, name='purchasing'),
    path('manufacturing/', views.manufacturing, name='manufacturing'),
    path('online-store/', views.online_store, name='online_store'),
    path('store-management/', views.store_management, name='store_management'),
    
    # System Views
    path('help-center/', views.help_center, name='help_center'),
    path('settings/', views.settings, name='settings'),
    path('update-profile/', views.update_profile, name='update_profile'),
]