from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import UserProfile, InviteCode, AccessLog

# Custom User Admin with enhanced functionality
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    fk_name = 'user'  # Specify which ForeignKey to use since there are multiple
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('is_approved', 'approved_by', 'approved_at', 'last_access', 'access_count', 'ip_address')
    readonly_fields = ('last_access', 'access_count', 'ip_address', 'approved_at')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_approved', 'date_joined', 'last_login', 'admin_actions')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'userprofile__is_approved')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve-user/<int:user_id>/', self.admin_site.admin_view(self.approve_user), name='approve_user'),
            path('reject-user/<int:user_id>/', self.admin_site.admin_view(self.reject_user), name='reject_user'),
            path('remove-user/<int:user_id>/', self.admin_site.admin_view(self.remove_user), name='remove_user'),
        ]
        return custom_urls + urls
    
    def approve_user(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.is_approved = True
        profile.approved_by = request.user
        profile.approved_at = timezone.now()
        profile.save()
        messages.success(request, f'User {user.username} has been approved.')
        return redirect('admin:auth_user_changelist')
    
    def reject_user(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        try:
            profile = user.userprofile
            profile.is_approved = False
            profile.approved_by = None
            profile.approved_at = None
            profile.save()
            messages.warning(request, f'User {user.username} has been rejected.')
        except UserProfile.DoesNotExist:
            messages.error(request, f'User {user.username} has no profile.')
        return redirect('admin:auth_user_changelist')
    
    def remove_user(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        if user.is_superuser:
            messages.error(request, f'Cannot remove superuser {user.username}.')
            return redirect('admin:auth_user_changelist')
        
        try:
            # Delete user profile first
            try:
                profile = user.userprofile
                profile.delete()
            except UserProfile.DoesNotExist:
                pass
            
            # Delete user
            username = user.username
            user.delete()
            messages.success(request, f'User {username} has been removed successfully.')
        except Exception as e:
            messages.error(request, f'Error removing user {user.username}: {str(e)}')
        
        return redirect('admin:auth_user_changelist')
    
    def is_approved(self, obj):
        try:
            profile = obj.userprofile
            if profile.is_approved:
                return format_html('<span style="color: green;">✓ Approved</span>')
            else:
                return format_html('<span style="color: orange;">⏳ Pending</span>')
        except UserProfile.DoesNotExist:
            return format_html('<span style="color: red;">❌ No Profile</span>')
    is_approved.short_description = 'Approval Status'
    
    def admin_actions(self, obj):
        if obj.is_superuser:
            return format_html('<span style="color: gray;">Superuser</span>')
        
        approve_url = reverse('admin:approve_user', args=[obj.pk])
        reject_url = reverse('admin:reject_user', args=[obj.pk])
        delete_url = reverse('admin:auth_user_delete', args=[obj.pk])
        remove_url = reverse('admin:remove_user', args=[obj.pk])
        
        buttons = []
        
        try:
            profile = obj.userprofile
            if not profile.is_approved:
                buttons.append(f'<a href="{approve_url}" class="button" style="background: green; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px; margin-right: 5px;">Approve</a>')
                buttons.append(f'<a href="{reject_url}" class="button" style="background: red; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px; margin-right: 5px;">Reject</a>')
        except UserProfile.DoesNotExist:
            pass
        
        buttons.append(f'<a href="{remove_url}" class="button" style="background: #dc3545; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px; margin-right: 5px; font-weight: bold;">Remove User</a>')
        buttons.append(f'<a href="{delete_url}" class="button" style="background: #6c757d; color: white; padding: 2px 8px; text-decoration: none; border-radius: 3px;">Delete</a>')
        
        return format_html(' '.join(buttons))
    admin_actions.short_description = 'Actions'
    admin_actions.allow_tags = True

# Invite Code Admin
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_by', 'created_at', 'expires_at', 'is_used', 'current_uses', 'max_uses', 'is_active')
    list_filter = ('is_used', 'is_active', 'created_at', 'expires_at')
    search_fields = ('code', 'created_by__username')
    readonly_fields = ('created_at', 'used_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'created_by', 'created_at')
        }),
        ('Usage Settings', {
            'fields': ('max_uses', 'current_uses', 'is_active')
        }),
        ('Expiration', {
            'fields': ('expires_at',)
        }),
        ('Usage Tracking', {
            'fields': ('is_used', 'used_by', 'used_at'),
            'classes': ('collapse',)
        }),
    )

# Access Log Admin
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'action', 'success', 'accessed_at')
    list_filter = ('success', 'action', 'accessed_at')
    search_fields = ('user__username', 'ip_address', 'action')
    readonly_fields = ('accessed_at',)
    ordering = ('-accessed_at',)
    
    def has_add_permission(self, request):
        return False  # Access logs are created automatically
    
    def has_change_permission(self, request, obj=None):
        return False  # Access logs should not be modified

# User Profile Admin
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_approved', 'approved_by', 'approved_at', 'last_access', 'access_count')
    list_filter = ('is_approved', 'approved_at', 'created_at')
    search_fields = ('user__username', 'user__email', 'ip_address')
    readonly_fields = ('created_at', 'last_access', 'access_count')
    ordering = ('-created_at',)

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Register other models
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(InviteCode, InviteCodeAdmin)
admin.site.register(AccessLog, AccessLogAdmin)
