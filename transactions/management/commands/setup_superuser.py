"""
Configure UNIQUEMENT le superuser Django (interface /admin/) :
username, email et mot de passe imposés. Les comptes Admin du site
(profil Admin) ne sont PAS modifiés.

Usage : python manage.py setup_superuser
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from transactions.models import Admin

USERNAME = 'Black'
EMAIL = 'adamasankare2000@gmail.com'
PASSWORD = 'Black7073@#'


class Command(BaseCommand):
    help = 'Définit le superuser Django (Black) sans toucher aux comptes Admin du site'

    def handle(self, *args, **options):
        admin_user_ids = set(Admin.objects.values_list('user_id', flat=True))
        superusers = list(User.objects.filter(is_superuser=True))

        self.stdout.write(self.style.WARNING(f'{len(superusers)} superuser(s) trouvé(s)'))

        cible = None
        for u in superusers:
            if u.id not in admin_user_ids:
                cible = u
                break
        if cible is None and len(superusers) == 1:
            cible = superusers[0]
        if cible is None and superusers:
            cible = superusers[0]

        if cible is not None:
            cible.username = USERNAME
            cible.email = EMAIL
            cible.is_superuser = True
            cible.is_staff = True
            cible.set_password(PASSWORD)
            cible.save()
            self.stdout.write(self.style.SUCCESS(
                f"SUPERUSER MAJ: LOGIN={cible.username} EMAIL={cible.email} MDP={PASSWORD}"))
        else:
            cible, _ = User.objects.get_or_create(username=USERNAME)
            cible.email = EMAIL
            cible.is_superuser = True
            cible.is_staff = True
            cible.set_password(PASSWORD)
            cible.save()
            self.stdout.write(self.style.SUCCESS(
                f"SUPERUSER CREE: LOGIN={cible.username} EMAIL={cible.email} MDP={PASSWORD}"))

        admins = Admin.objects.count()
        self.stdout.write(self.style.SUCCESS(f'UNTOUCHED: {admins} compte(s) Admin du site intacts'))
        self.stdout.write(self.style.SUCCESS('SUPERUSER_OK'))