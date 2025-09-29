from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

def generate_invite_code():
    """Generate a unique invite code"""
    return str(uuid.uuid4())[:8].upper()

class InviteCode(models.Model):
    """Invite codes for user registration"""
    code = models.CharField(max_length=20, unique=True, default=generate_invite_code)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_invites')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='used_invite')
    used_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(default=1)
    current_uses = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Invite {self.code} ({'Used' if self.is_used else 'Active'})"
    
    def is_valid(self):
        return (self.is_active and 
                not self.is_used and 
                self.current_uses < self.max_uses and 
                timezone.now() < self.expires_at)
    
    def use_invite(self, user):
        if self.is_valid():
            self.current_uses += 1
            if self.current_uses >= self.max_uses:
                self.is_used = True
            self.used_by = user
            self.used_at = timezone.now()
            self.save()
            return True
        return False

class UserProfile(models.Model):
    """Extended user profile with access control"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    invite_code = models.ForeignKey(InviteCode, on_delete=models.SET_NULL, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_users')
    approved_at = models.DateTimeField(null=True, blank=True)
    last_access = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} ({'Approved' if self.is_approved else 'Pending'})"

class AccessLog(models.Model):
    """Log all user access for security monitoring"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    accessed_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100)  # login, logout, access_app, etc.
    success = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-accessed_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.accessed_at}"