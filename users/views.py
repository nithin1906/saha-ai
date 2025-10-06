from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Q
from .models import InviteCode, UserProfile, AccessLog
from .forms import InviteCodeForm, UserRegistrationForm
import uuid
from datetime import timedelta

def is_admin(user):
    """Check if user is admin"""
    return user.is_superuser or user.is_staff

def send_welcome_email(user):
    """Send welcome email to approved user"""
    try:
        login_url = f"https://saha-ai.up.railway.app/users/login/"
        
        html_message = render_to_string('users/emails/welcome_email.html', {
            'user': user,
            'login_url': login_url
        })
        
        send_mail(
            subject='🎉 Welcome to SAHA-AI - Your Account is Approved!',
            message=f'Hello {user.first_name},\n\nYour SAHA-AI account has been approved! You can now login and start using our AI-powered financial assistant.\n\nLogin URL: {login_url}\n\nBest regards,\nThe SAHA-AI Team',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,  # Don't raise exceptions
        )
        print(f"Welcome email sent to {user.email}")
    except Exception as e:
        print(f"Failed to send welcome email to {user.email}: {e}")

def send_update_email(user, update_type='general'):
    """Send update email to user"""
    try:
        login_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/users/login/"
        if not login_url.startswith('http'):
            login_url = f"http://{login_url}"
        
        html_message = render_to_string('users/emails/update_email.html', {
            'user': user,
            'login_url': login_url,
            'update_type': update_type
        })
        
        send_mail(
            subject='🚀 SAHA-AI Updates - New Features Available!',
            message=f'Hello {user.first_name},\n\nWe have exciting updates and new features for you in SAHA-AI!\n\nLogin URL: {login_url}\n\nBest regards,\nThe SAHA-AI Team',
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        print(f"Update email sent to {user.email}")
    except Exception as e:
        print(f"Failed to send update email to {user.email}: {e}")

def log_access(user, request, action, success=True):
    """Log user access for security monitoring"""
    AccessLog.objects.create(
        user=user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        action=action,
        success=success
    )

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard for managing invites and users"""
    # Update user profile access
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile.last_access = timezone.now()
    profile.access_count += 1
    profile.ip_address = request.META.get('REMOTE_ADDR')
    profile.save()
    
    log_access(request.user, request, 'admin_dashboard_access')
    
    # Get statistics
    total_users = User.objects.count()
    pending_users = UserProfile.objects.filter(is_approved=False).count()
    active_invites = InviteCode.objects.filter(is_active=True, is_used=False).count()
    recent_logs = AccessLog.objects.all()[:10]
    
    context = {
        'total_users': total_users,
        'pending_users': pending_users,
        'active_invites': active_invites,
        'recent_logs': recent_logs,
    }
    return render(request, 'users/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def manage_invites(request):
    """Manage invite codes"""
    if request.method == 'POST':
        form = InviteCodeForm(request.POST)
        if form.is_valid():
            invite = form.save(commit=False)
            invite.created_by = request.user
            invite.expires_at = timezone.now() + timedelta(days=30)  # 30 days expiry
            invite.save()
            messages.success(request, f'Invite code {invite.code} created successfully!')
            return redirect('manage_invites')
    else:
        form = InviteCodeForm()
    
    invites = InviteCode.objects.all().order_by('-created_at')
    return render(request, 'users/manage_invites.html', {'form': form, 'invites': invites})

@login_required
@user_passes_test(is_admin)
def manage_users(request):
    """Manage user approvals"""
    pending_users = UserProfile.objects.filter(is_approved=False).order_by('created_at')
    approved_users = UserProfile.objects.filter(is_approved=True).order_by('-approved_at')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if action == 'approve':
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            user_profile.is_approved = True
            user_profile.approved_by = request.user
            user_profile.approved_at = timezone.now()
            user_profile.save()
            
            # Also activate the user account
            user_profile.user.is_active = True
            user_profile.user.save()
            
            # Send welcome email (async, don't block)
            try:
                send_welcome_email(user_profile.user)
            except Exception as e:
                print(f"Email sending failed (non-blocking): {e}")
            
            messages.success(request, f'User {user_profile.user.username} approved and activated!')
        elif action == 'reject':
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            user_profile.user.delete()
            messages.success(request, f'User {user_profile.user.username} rejected and deleted!')
        elif action == 'remove':
            user_profile = get_object_or_404(UserProfile, user_id=user_id)
            if user_profile.user.is_superuser:
                messages.error(request, f'Cannot remove superuser {user_profile.user.username}.')
            else:
                username = user_profile.user.username
                user_profile.user.delete()
                messages.success(request, f'User {username} has been removed successfully.')
    
    return render(request, 'users/manage_users.html', {
        'pending_users': pending_users,
        'approved_users': approved_users
    })

def register_with_invite(request):
    """User registration with invite code"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        invite_code = request.POST.get('invite_code', '').upper().strip()
        
        if form.is_valid():
            # Check invite code
            try:
                invite = InviteCode.objects.get(code=invite_code)
                if not invite.is_valid():
                    messages.error(request, 'Invalid or expired invite code!')
                    return render(request, 'users/register.html', {'form': form})
                
                # Create user
                user = form.save()
                user.is_active = False  # Require admin approval
                user.save()
                
                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    invite_code=invite,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                # Use the invite
                invite.use_invite(user)
                
                log_access(user, request, 'registration', True)
                
                messages.success(request, 'Registration successful! Your account is pending admin approval.')
                return redirect('login')
                
            except InviteCode.DoesNotExist:
                messages.error(request, 'Invalid invite code!')
                return render(request, 'users/register.html', {'form': form})
    else:
        form = UserRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})

def custom_login(request):
    """Custom login with access logging"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Check if user is approved
            try:
                profile = UserProfile.objects.get(user=user)
                if not profile.is_approved:
                    log_access(user, request, 'login_attempt_unapproved', False)
                    messages.error(request, 'Your account is pending admin approval.')
                    return render(request, 'users/login.html', {'form': None, 'next': request.GET.get('next', '')})
            except UserProfile.DoesNotExist:
                log_access(user, request, 'login_attempt_no_profile', False)
                messages.error(request, 'Account not found. Please register first.')
                return render(request, 'users/login.html', {'form': None, 'next': request.GET.get('next', '')})
            
            login(request, user)
            
            # Update profile
            profile.last_access = timezone.now()
            profile.access_count += 1
            profile.ip_address = request.META.get('REMOTE_ADDR')
            profile.save()
            
            log_access(user, request, 'login_success', True)
            
            # Redirect admin users to admin dashboard, regular users to home
            if is_admin(user):
                return redirect('admin_dashboard')
            else:
                # Check if user came from mobile service and redirect accordingly
                next_url = request.GET.get('next') or request.POST.get('next')
                referer = request.META.get('HTTP_REFERER', '')
                
                # Check if this is a mobile service request
                is_mobile_service = (
                    'mobile' in next_url or 
                    '/mobile/' in referer or
                    'saha-ai-mobile.up.railway.app' in referer or
                    request.META.get('HTTP_HOST', '').endswith('mobile.up.railway.app') or
                    '/mobile/' in next_url
                )
                
                if is_mobile_service:
                    return redirect('/mobile/')
                else:
                    return redirect('home')
        else:
            log_access(None, request, 'login_failed', False)
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'users/login.html', {'form': None, 'next': request.GET.get('next', '')})

@login_required
def access_logs(request):
    """View access logs (admin only)"""
    if not is_admin(request.user):
        messages.error(request, 'Access denied.')
        return redirect('home')
    
    logs = AccessLog.objects.all().order_by('-accessed_at')[:100]
    return render(request, 'users/access_logs.html', {'logs': logs})

@login_required
@user_passes_test(is_admin)
def send_updates_to_all_users(request):
    """Send update emails to all approved users (admin only)"""
    if request.method == 'POST':
        approved_users = User.objects.filter(userprofile__is_approved=True)
        sent_count = 0
        
        for user in approved_users:
            try:
                send_update_email(user)
                sent_count += 1
            except Exception as e:
                print(f"Failed to send update email to {user.email}: {e}")
        
        messages.success(request, f'Update emails sent to {sent_count} users!')
        return redirect('admin_dashboard')
    
    return render(request, 'users/send_updates.html')

def logout_view(request):
    """Custom logout view with logging"""
    if request.user.is_authenticated:
        log_access(request.user, request, 'logout', True)
    
    from django.contrib.auth import logout
    logout(request)
    return redirect('login')