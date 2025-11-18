from django.core.management.base import BaseCommand
from django.test import Client


class Command(BaseCommand):
    help = 'Run quick internal smoke tests against key endpoints using Django test client.'

    def handle(self, *args, **options):
        client = Client()

        endpoints = [
            ('GET', '/api/dev/version/'),
            ('GET', '/api/market/snapshot/'),
            ('POST', '/api/parse/', {'text': 'hello'}),
        ]

        for method, path, *rest in endpoints:
            try:
                if method == 'GET':
                    resp = client.get(path)
                else:
                    data = rest[0] if rest else {}
                    resp = client.post(path, data, content_type='application/json')

                self.stdout.write(f"{method} {path} -> {resp.status_code}")
                content = resp.content.decode('utf-8', errors='replace')
                snippet = content[:1000]
                self.stdout.write(snippet)
                self.stdout.write('-' * 60)
            except Exception as e:
                self.stderr.write(f"{method} {path} -> ERROR: {e}")
