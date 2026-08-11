"""
Crée / corrige le superuser Django (accès /admin/) :
    LOGIN = BLACK
    EMAIL = adamasankare2000@gmail.com
    MDP   = Black7073@#
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Crée ou met à jour le superuser BLACK pour l'interface /admin/"

    def handle(self, *args, **options):
        user = User.objects.filter(username='BLACK').first()
        if user is None:
            user = User.objects.filter(is_superuser=True).first()
        if user is None:
            user = User(username='BLACK')
            self.stdout.write(self.style.WARNING('Création du superuser BLACK...'))

        user.username = 'BLACK'
        user.email = 'adamasankare2000@gmail.com'
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.set_password('Black7073@#')
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"SUPERUSER_OK | LOGIN={user.username} | EMAIL={user.email}"))
