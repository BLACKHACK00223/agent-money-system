"""
Réinitialisation du site : supprime TOUTES les données opérationnelles
mais GARDE les comptes Admin (et leurs mots de passe).

Usage (sur le serveur) :
    python manage.py reset_donnees [--confirme]

Sans --confirme, la commande affiche un aperçu et demande confirmation.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from transactions.models import (
    Agent, Assistant, Admin, Caisse,
    Transaction, DemandeApprovisionnement, ApprovisionnementDirect,
    HistoriqueAgent, Facture, PaiementFacture, Debiteur, Dette,
    RemboursementDette, CompteEpargne, OperationCompte, OperationCaisse,
    OperationUv, CompteEpargneAdmin, OperationEpargne, PrintQueue,
    CommissionRate,
)


class Command(BaseCommand):
    help = 'Supprime toutes les données (transactions, agents, historiques...) en gardant les admins'

    def add_arguments(self, parser):
        parser.add_argument('--confirme', action='store_true', help='Confirmer sans demander')

    def handle(self, *args, **options):
        confirm = options.get('confirme')

        # ---- 1. Aperçu ----
        self.stdout.write(self.style.WARNING('== APERÇU DE LA RÉINITIALISATION =='))
        models_reset = [
            ("Transactions", Transaction),
            ("Demandes d'approvisionnement", DemandeApprovisionnement),
            ("Approvisionnements directs", ApprovisionnementDirect),
            ("Historique agents", HistoriqueAgent),
            ("Factures", Facture),
            ("Paiements de factures", PaiementFacture),
            ("Débiteurs", Debiteur),
            ("Dettes", Dette),
            ("Remboursements de dettes", RemboursementDette),
            ("Comptes d'épargne", CompteEpargne),
            ("Opérations de comptes", OperationCompte),
            ("Opérations de caisse", OperationCaisse),
            ("Opérations UV", OperationUv),
            ("Comptes d'épargne admin", CompteEpargneAdmin),
            ("Opérations d'épargne", OperationEpargne),
            ("File d'impression", PrintQueue),
        ]
        total = 0
        for label, model in models_reset:
            n = model.objects.count()
            total += n
            self.stdout.write(f"  {label:<42} : {n}")
        self.stdout.write(f"  {'Agents':<42} : {Agent.objects.count()}")
        self.stdout.write(f"  {'Assistants':<42} : {Assistant.objects.count()}")
        self.stdout.write(f"  {'TOTAL lignes supprimées':<42} : {total}")

        admins = Admin.objects.count()
        self.stdout.write(self.style.SUCCESS(f"\n  Admins conservés : {admins} (comptes et mots de passe intacts)"))

        if not confirm:
            rep = input('\nContinuer ? La suppression est IRRÉVERSIBLE. Tapez OUI : ')
            if rep.strip().upper() != 'OUI':
                self.stdout.write(self.style.WARNING('Annulé.'))
                return

        # ---- 2. Suppression des données opérationnelles ----
        # Ordre : enfants d'abord (dépendances)
        for label, model in models_reset:
            model.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {label} supprimé'))

        # ---- 3. Agents / Assistants + leurs utilisateurs ----
        def delete_profiles(model_cls, label):
            for obj in model_cls.objects.all():
                uid = obj.user_id
                obj.delete()
                if uid:
                    User.objects.filter(id=uid, is_staff=False, is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS(f'  ✓ {label} supprimés'))

        delete_profiles(Agent, 'Agents')
        delete_profiles(Assistant, 'Assistants')

        # ---- 4. Caisses des admins remises à zéro ----
        for admin in Admin.objects.all():
            caisse, _ = Caisse.objects.get_or_create(user=admin.user)
            caisse.solde_cash = 0
            caisse.solde_uv = 0
            caisse.solde_wave = 0
            caisse.solde_cash_hier = 0
            caisse.solde_uv_hier = 0
            caisse.solde_wave_hier = 0
            caisse.last_balance_update = None
            caisse.save()
        self.stdout.write(self.style.SUCCESS('  ✓ Caisses admins remises à zéro'))

        # ---- 5. Taux de commission ----
        CommissionRate.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('  ✓ Taux de commission réinitialisés (à reconfigurer)'))

        self.stdout.write(self.style.SUCCESS('\n✅ Réinitialisation terminée. Les comptes admins sont intacts.'))