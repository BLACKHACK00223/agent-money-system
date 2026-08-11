"""
Réinitialise le mot de passe de TOUS les comptes Admin à une valeur donnée.

Usage : python manage.py reset_admin_pwd --pwd VOTRE_MOT_DE_PASSE
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from transactions.models import Admin


class Command(BaseCommand):
    help = 'Récupère la liste des admins et réinitialise leur mot de passe'

    def add_arguments(self, parser):
        parser.add_argument('--pwd', default='KoneAdmin2026',
                            help='Nouveau mot de passe (défaut : KoneAdmin2026)')

    def handle(self, *args, **options):
        pwd = options.get('pwd')
        admins = Admin.objects.all()
        self.stdout.write(self.style.WARNING(f'{admins.count()} compte(s) admin trouvé(s)'))
        for admin in admins:
            user = admin.user
            user.set_password(pwd)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"LOGIN={user.username} | EMAIL={user.email} | MDP={pwd}"))
        self.stdout.write(self.style.SUCCESS('MDP_OK'))
