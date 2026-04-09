# transactions/management/commands/init_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from transactions.models import AgentPrincipal, SousAgent, Caisse

class Command(BaseCommand):
    help = 'Initialise les données de base'

    def handle(self, *args, **options):
        # Créer un utilisateur pour l'agent principal
        user, created = User.objects.get_or_create(
            username='agent_principal',
            defaults={
                'email': 'agent@example.com',
                'password': 'pbkdf2_sha256$260000$...'  # Utilisez set_password
            }
        )
        user.set_password('agent123')
        user.save()
        
        # Créer l'agent principal
        agent_principal, created = AgentPrincipal.objects.get_or_create(
            user=user,
            defaults={
                'nom': 'Mamadou Diallo',
                'telephone': '+223 70 00 00 00',
                'point_service': 'Agence Centrale',
                'adresse': 'Bamako, Mali'
            }
        )
        
        # Créer des sous-agents
        sous_agents_data = [
            {'nom': 'Amadou Traoré', 'telephone': '+223 71 11 11 11', 'code_acces': '123456'},
            {'nom': 'Fatoumata Keita', 'telephone': '+223 72 22 22 22', 'code_acces': '234567'},
            {'nom': 'Ibrahim Sangaré', 'telephone': '+223 73 33 33 33', 'code_acces': '345678'},
        ]
        
        for data in sous_agents_data:
            sous_agent, created = SousAgent.objects.get_or_create(
                code_acces=data['code_acces'],
                defaults={
                    'agent_principal': agent_principal,
                    'nom': data['nom'],
                    'telephone': data['telephone'],
                    'est_actif': True
                }
            )
            
            # Créer une caisse pour chaque sous-agent
            Caisse.objects.get_or_create(
                sous_agent=sous_agent,
                defaults={
                    'solde_cash': 100000,
                    'solde_orange': 50000,
                    'solde_wave': 25000,
                    'solde_malitel': 30000,
                    'solde_telecel': 20000,
                }
            )
            
            self.stdout.write(self.style.SUCCESS(f'Sous-agent créé: {sous_agent.nom}'))
        
        self.stdout.write(self.style.SUCCESS('✅ Données initiales créées avec succès!'))