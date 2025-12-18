from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
import secrets
import string

# Custom User Manager
class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)

def generate_temp_password(length=12):
    """Generate a temporary password"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'CustomUser', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_organizations'
    )
    admin_user = models.OneToOneField(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_organization'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Generate slug if not provided
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-').replace('_', '-')
            # Make slug unique
            base_slug = self.slug
            counter = 1
            while Organization.objects.filter(slug=self.slug).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)
    
    def get_user_count(self):
        return self.users.count()
    
    def get_active_users_count(self):
        return self.users.filter(is_active=True).count()

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrator'),
        ('organization_admin', 'Organization Administrator'),
        ('manager', 'Manager'),
        ('hr', 'HR Personnel'),
        ('sales_agent', 'Sales Agent'),
        ('employee', 'Employee'),
    ]
    
    organization = models.ForeignKey(
        Organization, 
        on_delete=models.CASCADE, 
        related_name='users',
        null=True,
        blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    last_active = models.DateTimeField(null=True, blank=True)
    
    # Track if user needs to reset password
    temp_password = models.CharField(max_length=128, blank=True)
    force_password_change = models.BooleanField(default=False)
    
    # Track who created this user
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users'
    )
    
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        # Store temp_password before hashing
        if self.temp_password and not self.password.startswith('pbkdf2_sha256$'):
            temp_pwd = self.temp_password
            self.set_password(temp_pwd)
            self.temp_password = temp_pwd
        
        # Set is_staff and is_superuser based on role
        if self.role == 'super_admin':
            self.is_staff = True
            self.is_superuser = True
        elif self.role == 'organization_admin':
            self.is_staff = True
            self.is_superuser = False
        else:
            self.is_staff = False
            self.is_superuser = False
            
        super().save(*args, **kwargs)
    
    @property
    def is_super_admin(self):
        return self.role == 'super_admin'
    
    @property
    def is_organization_admin(self):
        return self.role == 'organization_admin'
    
    def get_role_display(self):
        """Get human-readable role name"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def get_full_name_or_username(self):
        """Get full name or fallback to username"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username
    
    def can_access_module(self, module_name):
        """Check if user has access to a specific module based on role"""
        # Super admins can access everything
        if self.is_super_admin:
            return True
        
        # Module permissions based on role
        module_permissions = {
            'dashboard': ['super_admin', 'organization_admin', 'manager', 'hr', 'sales_agent', 'employee'],
            'super_admin_dashboard': ['super_admin'],
            'analytics': ['super_admin', 'organization_admin', 'manager', 'hr'],
            'inventory': ['super_admin', 'organization_admin', 'manager', 'sales_agent'],
            'sales': ['super_admin', 'organization_admin', 'manager', 'sales_agent'],
            'purchasing': ['super_admin', 'organization_admin', 'manager'],
            'manufacturing': ['super_admin', 'organization_admin', 'manager'],
            'online_store': ['super_admin', 'organization_admin', 'manager', 'sales_agent'],
            'store_management': ['super_admin', 'organization_admin', 'manager'],
            'hr_dashboard': ['super_admin', 'organization_admin', 'hr', 'manager'],
            'reports': ['super_admin', 'organization_admin', 'manager', 'hr'],
            'settings': ['super_admin', 'organization_admin', 'manager', 'hr', 'sales_agent', 'employee'],
            'user_management': ['super_admin', 'organization_admin'],
            'organizations': ['super_admin'],
            'org_admin_dashboard': ['organization_admin'],
            'super_admin_organizations': ['super_admin'],
            'super_admin_users': ['super_admin'],
            'super_admin_activities': ['super_admin'],
            'super_admin_create_org_admin': ['super_admin'],
            'profile_settings': ['super_admin', 'organization_admin', 'manager', 'hr', 'sales_agent', 'employee'],
            'help_center': ['super_admin', 'organization_admin', 'manager', 'hr', 'sales_agent', 'employee'],
        }
        
        return self.role in module_permissions.get(module_name, [])
    
    def get_managed_users(self):
        """Get users that this user can manage"""
        if self.is_super_admin:
            # Super admin can see other super admins and organization admins
            return CustomUser.objects.filter(
                role__in=['super_admin', 'organization_admin']
            ).exclude(id=self.id)
        elif self.is_organization_admin and self.organization:
            # Organization admin can see all users in their org EXCEPT super admins
            return CustomUser.objects.filter(
                organization=self.organization
            ).exclude(role='super_admin')
        elif self.is_manager and self.organization:
            # Managers can see employees in their department
            if self.department:
                return CustomUser.objects.filter(
                    organization=self.organization,
                    department=self.department,
                    role='employee'
                )
            return CustomUser.objects.none()
        return CustomUser.objects.none()
    
    def update_last_active(self):
        """Update user's last active timestamp"""
        self.last_active = timezone.now()
        self.save(update_fields=['last_active'])

class UserPermission(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='permissions')
    module = models.CharField(max_length=50)
    can_view = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'user_permissions'
        unique_together = ['user', 'module']
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
    
    def __str__(self):
        return f"{self.user.username} - {self.module}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('reset_password', 'Reset Password'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activity_logs')
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['organization', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def get_action_display(self):
        """Get human-readable action name"""
        return dict(self.ACTION_CHOICES).get(self.action, self.action)
    
    
    
# models.py - Add these to your existing models

class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    
    # Personal Information
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        null=True,
        blank=True
    )
    
    # Contact Information
    alternate_email = models.EmailField(null=True, blank=True)
    mobile_phone = models.CharField(max_length=20, null=True, blank=True)
    work_phone = models.CharField(max_length=20, null=True, blank=True)
    emergency_contact = models.CharField(max_length=100, null=True, blank=True)
    emergency_phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Address Information
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    
    # Professional Information
    employee_id = models.CharField(max_length=50, null=True, blank=True, unique=True)
    hire_date = models.DateField(null=True, blank=True)
    job_title = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')
    employment_type = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('intern', 'Intern')
        ],
        null=True,
        blank=True
    )
    
    # Social Media & Links
    linkedin_url = models.URLField(null=True, blank=True)
    twitter_handle = models.CharField(max_length=50, null=True, blank=True)
    github_username = models.CharField(max_length=50, null=True, blank=True)
    personal_website = models.URLField(null=True, blank=True)
    
    # Profile Settings
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    theme_preference = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Light'),
            ('dark', 'Dark'),
            ('auto', 'Auto')
        ],
        default='auto'
    )
    
    # Notification Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Security & Privacy
    two_factor_enabled = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)
    account_locked = models.BooleanField(default=False)
    lock_reason = models.TextField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_profiles')
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"Profile for {self.user.username}"
    
    def get_full_address(self):
        """Get formatted full address"""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)
    
    def get_employment_details(self):
        """Get formatted employment details"""
        details = []
        if self.job_title:
            details.append(f"Job Title: {self.job_title}")
        if self.department:
            details.append(f"Department: {self.department}")
        if self.employment_type:
            details.append(f"Type: {self.get_employment_type_display()}")
        return details
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def save(self, *args, **kwargs):
        # Generate employee ID if not set
        if not self.employee_id and self.user and self.user.organization:
            org_prefix = self.user.organization.slug[:3].upper()
            user_id = str(self.user.id).zfill(6)
            self.employee_id = f"{org_prefix}-{user_id}"
        
        super().save(*args, **kwargs)


class ProfileAuditLog(models.Model):
    """Track profile changes"""
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('viewed', 'Viewed'),
            ('deleted', 'Deleted')
        ]
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Profile Audit Log"
        verbose_name_plural = "Profile Audit Logs"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} {self.field_changed} for {self.profile.user.username}"


class Document(models.Model):
    """User documents"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=50,
        choices=[
            ('resume', 'Resume'),
            ('certificate', 'Certificate'),
            ('license', 'License'),
            ('id_proof', 'ID Proof'),
            ('degree', 'Degree'),
            ('contract', 'Contract'),
            ('other', 'Other')
        ]
    )
    file = models.FileField(upload_to='user_documents/')
    description = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='verified_documents')
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.name} ({self.user.username})"
    
    @property
    def file_size(self):
        if self.file and self.file.size:
            return self.file.size
        return 0
    
    @property
    def is_expired(self):
        if self.expires_at:
            return self.expires_at < timezone.now().date()
        return False


class Notification(models.Model):
    """User notifications"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Information'),
            ('success', 'Success'),
            ('warning', 'Warning'),
            ('error', 'Error'),
            ('security', 'Security'),
            ('system', 'System')
        ],
        default='info'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.URLField(null=True, blank=True)
    action_text = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    @property
    def is_recent(self):
        """Check if notification is recent (within 24 hours)"""
        return (timezone.now() - self.created_at).days < 1