from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Run authenticated chat smoke tests using Django test client (force login)'

    def handle(self, *args, **options):
        User = get_user_model()
        client = Client()

        # Try to get an existing user, otherwise create one
        username = 'smokeuser'
        try:
            user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.create_user(username=username, email='smoke@example.com', password='smoke-pass')
                user.save()
                self.stdout.write(f'Created test user: {username}')
            else:
                self.stdout.write(f'Found existing user: {username}')
        except Exception as e:
            self.stderr.write(f'Error creating/finding user: {e}')
            return

        # Force login without password
        client.force_login(user)
        self.stdout.write('Authenticated test client')

        # Test chat endpoint
        try:
            resp = client.post('/api/nlp/chat/', {'message': 'hello, how are you?'}, content_type='application/json')
            self.stdout.write(f'POST /api/nlp/chat/ -> {resp.status_code}')
            self.stdout.write(resp.content.decode('utf-8')[:2000])
        except Exception as e:
            self.stderr.write(f'chat endpoint ERROR: {e}')

        # Test detect_question_type
        try:
            resp2 = client.post('/api/nlp/detect/', {'message': 'analyze tata steel for me'}, content_type='application/json')
            self.stdout.write(f'POST /api/nlp/detect/ -> {resp2.status_code}')
            self.stdout.write(resp2.content.decode('utf-8')[:2000])
        except Exception as e:
            self.stderr.write(f'detect endpoint ERROR: {e}')

        # Test financial advisor
        try:
            resp3 = client.post('/api/nlp/advisor/', {'query': 'Give me insight into TSLA', 'ticker': 'TSLA'}, content_type='application/json')
            self.stdout.write(f'POST /api/nlp/advisor/ -> {resp3.status_code}')
            self.stdout.write(resp3.content.decode('utf-8')[:2000])
        except Exception as e:
            self.stderr.write(f'advisor endpoint ERROR: {e}')
