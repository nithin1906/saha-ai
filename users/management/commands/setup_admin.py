from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import InviteCode, UserProfile
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Create initial admin user and invite codes for SAHA-AI'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Admin username')
        parser.add_argument('--email', type=str, default='admin@saha-ai.com', help='Admin email')
        parser.add_argument('--password', type=str, default='admin123', help='Admin password')
        parser.add_argument('--invite-codes', type=int, default=5, help='Number of invite codes to create')

    def handle(self, *args, **options):
        # Create superuser
        username = options['username']
        email = options['email']
        password = options['password']
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_superuser(username, email, password)
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {username}'))
        
        # Create user profile for admin
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'is_approved': True,
                'approved_by': user,
                'approved_at': timezone.now(),
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created admin profile for {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin profile for {username} already exists'))
        
        # Create invite codes
        num_codes = options['invite_codes']
        created_codes = []
        
        for i in range(num_codes):
            invite = InviteCode.objects.create(
                created_by=user,
                expires_at=timezone.now() + timedelta(days=30),
                max_uses=1,
                is_active=True
            )
            created_codes.append(invite.code)
        
        self.stdout.write(self.style.SUCCESS(f'Created {num_codes} invite codes:'))
        for code in created_codes:
            self.stdout.write(f'  - {code}')
        
        self.stdout.write(self.style.SUCCESS('\nSetup complete!'))
        self.stdout.write(self.style.WARNING('Remember to change the admin password in production!'))
