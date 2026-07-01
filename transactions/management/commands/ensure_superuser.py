# transactions/management/commands/ensure_superuser.py
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée un superutilisateur via les variables d'environnement DJANGO_SUPERUSER_*"

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not password:
            self.stdout.write('DJANGO_SUPERUSER_PASSWORD non définie, superutilisateur ignoré.')
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(f'Superutilisateur "{username}" existe déjà.')
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superutilisateur "{username}" créé avec succès.'))
