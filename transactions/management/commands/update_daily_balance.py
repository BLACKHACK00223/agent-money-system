# transactions/management/commands/update_daily_balance.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from transactions.models import Caisse

class Command(BaseCommand):
    help = 'Met à jour les soldes d\'hier pour toutes les caisses'

    def handle(self, *args, **options):
        today = timezone.now().date()
        count = 0
        
        for caisse in Caisse.objects.all():
            # Ne mettre à jour que si ce n'est pas déjà fait aujourd'hui
            if caisse.last_balance_update != today:
                caisse.sauvegarder_soldes_hier()
                count += 1
                self.stdout.write(f"✓ Soldes d'hier mis à jour pour {caisse.user.username}")
        
        self.stdout.write(self.style.SUCCESS(f'✅ {count} caisses mises à jour'))