# transactions/models.py
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver


class Admin(models.Model):
    """
    ADMIN - Compte administrateur principal
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    point_service = models.CharField(max_length=200)
    adresse = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.point_service}"
    
    class Meta:
        verbose_name = "Administrateur"
        verbose_name_plural = "Administrateurs"

class Agent(models.Model):
    """
    AGENT - Compte agent qui fait les transactions
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='agent_profile')
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    est_actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.telephone}"
    
    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"

# transactions/models.py
class Caisse(models.Model):
    """
    Caisse - Chaque utilisateur (ADMIN ou AGENT) a sa propre caisse
    Comptes: Cash (espèces), UV (Orange/Malitel/Telecel), Wave
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='caisse')
    
    # Comptes UNIFIÉS
    solde_cash = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde en espèces physiques"
    )
    solde_uv = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde UV Touspiont (Orange/Malitel/Telecel)"
    )
    solde_wave = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde Wave"
    )
    
    # ========== SOLDES D'HIER (stockés) ==========
    solde_cash_hier = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde Cash d'hier (fixe)"
    )
    solde_uv_hier = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde UV d'hier (fixe)"
    )
    solde_wave_hier = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text="Solde Wave d'hier (fixe)"
    )
    
    # Date de la dernière mise à jour des soldes d'hier
    last_balance_update = models.DateField(null=True, blank=True)
    
    # Limites par compte
    limite_cash = models.DecimalField(max_digits=12, decimal_places=2, default=10000000)
    limite_uv = models.DecimalField(max_digits=12, decimal_places=2, default=50000000)
    limite_wave = models.DecimalField(max_digits=12, decimal_places=2, default=50000000)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Caisse de {self.user.username} - Cash: {self.solde_cash} FCFA"
    
    def solde_total(self):
        return self.solde_cash + self.solde_uv + self.solde_wave
    
    def sauvegarder_soldes_hier(self):
        """
        Sauvegarde les soldes actuels comme soldes d'hier
        À appeler une fois par jour (via cron ou à minuit)
        """
        from django.utils import timezone
        self.solde_cash_hier = self.solde_cash
        self.solde_uv_hier = self.solde_uv
        self.solde_wave_hier = self.solde_wave
        self.last_balance_update = timezone.now().date()
        self.save()
    
    class Meta:
        verbose_name = "Caisse"
        verbose_name_plural = "Caisses"
        
# transactions/models.py - Ajouter à la fin du fichier

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Caisse)
def init_soldes_hier(sender, instance, created, **kwargs):
    """
    Initialise les soldes d'hier avec les soldes actuels lors de la création
    """
    if created:
        instance.solde_cash_hier = instance.solde_cash
        instance.solde_uv_hier = instance.solde_uv
        instance.solde_wave_hier = instance.solde_wave
        instance.save()

class Transaction(models.Model):
    """
    Transaction - Pour ADMIN et AGENTS
    """
    OPERATEUR_CHOICES = (
        ('orange', 'Orange Money'),
        ('wave', 'Wave'),
        ('malitel', 'Malitel'),
        ('telecel', 'Telecel'),
    )
    TYPE_CHOICES = (
        ('depot', 'Dépôt'),
        ('retrait', 'Retrait'),
        ('credit', 'Crédit/Recharge'),
    )
    
    # Qui a fait la transaction
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    # Détails
    operateur = models.CharField(max_length=10, choices=OPERATEUR_CHOICES)
    type_transaction = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # Client
    numero_client = models.CharField(max_length=20)
    nom_client = models.CharField(max_length=100, blank=True, null=True)
    
    # Montants
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    frais_operateur = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Références
    reference = models.CharField(max_length=50, unique=True, editable=False)
    reference_operateur = models.CharField(max_length=50, blank=True)
    
    # Statut
    statut = models.CharField(max_length=20, default='complete')
    
    # Horodatage
    date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    def calculer_commission(self):
        montant = Decimal(str(self.montant))
        
        taux = {
            'orange': {
                'depot': Decimal('0.0014'),
                'retrait': Decimal('0.0028'),
                'credit': Decimal('0.005'),
            },
            'wave': {
                'depot': Decimal('0.01'),
                'retrait': Decimal('0.01'),
                'credit': Decimal('0'),
            },
            'malitel': {
                'depot': Decimal('0.0014'),
                'retrait': Decimal('0.0028'),
                'credit': Decimal('0.005'),
            },
            'telecel': {
                'depot': Decimal('0'),
                'retrait': Decimal('0'),
                'credit': Decimal('0.005'),
            }
        }
        
        taux_commission = taux.get(self.operateur, {}).get(self.type_transaction, Decimal('0'))
        return (montant * taux_commission).quantize(Decimal('0.01'))
    
    def calculer_frais_operateur(self):
        montant = Decimal(str(self.montant))
        
        if self.operateur == 'orange':
            if self.type_transaction == 'depot':
                if montant <= 5000: return Decimal('25')
                elif montant <= 10000: return Decimal('50')
                elif montant <= 25000: return Decimal('100')
                elif montant <= 50000: return Decimal('150')
                elif montant <= 100000: return Decimal('200')
                else: return Decimal('250')
            elif self.type_transaction == 'retrait':
                if montant <= 5000: return Decimal('50')
                elif montant <= 10000: return Decimal('75')
                elif montant <= 25000: return Decimal('125')
                elif montant <= 50000: return Decimal('175')
                elif montant <= 100000: return Decimal('225')
                else: return Decimal('275')
            else:
                if montant <= 1000: return Decimal('25')
                elif montant <= 5000: return Decimal('50')
                elif montant <= 10000: return Decimal('75')
                else: return Decimal('100')
        
        elif self.operateur == 'wave':
            if self.type_transaction in ['depot', 'retrait']:
                return (montant * Decimal('0.01')).quantize(Decimal('0.01'))
        
        elif self.operateur == 'malitel':
            if self.type_transaction == 'depot':
                return Decimal('0')
            elif self.type_transaction == 'retrait':
                if montant <= 5000: return Decimal('50')
                elif montant <= 10000: return Decimal('75')
                elif montant <= 25000: return Decimal('100')
                else: return Decimal('150')
            else:
                if montant <= 1000: return Decimal('25')
                elif montant <= 5000: return Decimal('50')
                elif montant <= 10000: return Decimal('75')
                else: return Decimal('100')
        
        elif self.operateur == 'telecel':
            if self.type_transaction == 'credit':
                if montant <= 1000: return Decimal('20')
                elif montant <= 5000: return Decimal('40')
                elif montant <= 10000: return Decimal('60')
                else: return Decimal('80')
        
        return Decimal('0')
    
    def save(self, *args, **kwargs):
        if not self.reference:
            prefix = {
                'orange': 'OM',
                'wave': 'WV',
                'malitel': 'ML',
                'telecel': 'TC'
            }.get(self.operateur, 'TR')
            
            type_prefix = {
                'depot': 'D',
                'retrait': 'R',
                'credit': 'C'
            }.get(self.type_transaction, 'T')
            
            self.reference = f"{prefix}{type_prefix}{uuid.uuid4().hex[:8].upper()}"
        
        self.commission = self.calculer_commission()
        self.frais_operateur = self.calculer_frais_operateur()
        
        # Récupérer la caisse de l'utilisateur
        caisse = self.user.caisse
        
        # ========== LOGIQUE CORRIGÉE ==========
        
        # ORANGE, MALITEL, TELECEL (via UV Touspiont)
        if self.operateur in ['orange', 'malitel', 'telecel']:
            if self.type_transaction == 'depot':
                # DÉPÔT: client donne cash → agent donne ses UV
                caisse.solde_cash += self.montant   # Agent reçoit cash
                caisse.solde_uv -= self.montant     # Agent donne UV (DIMINUE)
                
            elif self.type_transaction == 'retrait':
                # RETRAIT: client prend cash → agent reçoit UV
                caisse.solde_cash -= self.montant   # Agent donne cash
                caisse.solde_uv += self.montant     # Agent reçoit UV (AUGMENTE)
                
            elif self.type_transaction == 'credit':
                # CRÉDIT: client recharge → agent donne ses UV
                caisse.solde_cash += self.montant   # Agent reçoit cash
                caisse.solde_uv -= self.montant     # Agent donne UV (DIMINUE)
        
        # WAVE
        elif self.operateur == 'wave':
            if self.type_transaction == 'depot':
                # DÉPÔT WAVE: client donne cash → agent donne ses Wave
                caisse.solde_cash += self.montant   # Agent reçoit cash
                caisse.solde_wave -= self.montant   # Agent donne Wave (DIMINUE)
                
            elif self.type_transaction == 'retrait':
                # RETRAIT WAVE: client prend cash → agent reçoit Wave
                caisse.solde_cash -= self.montant   # Agent donne cash
                caisse.solde_wave += self.montant   # Agent reçoit Wave (AUGMENTE)
        
        caisse.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.get_type_transaction_display()} {self.get_operateur_display()} - {self.montant} FCFA"
    
    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-date']


# transactions/models.py - DemandeApprovisionnement corrigé

# transactions/models.py - DemandeApprovisionnement (version finale)

# transactions/models.py
from django.utils import timezone

# transactions/models.py
from django.utils import timezone

class DemandeApprovisionnement(models.Model):
    """
    Demande d'approvisionnement de l'AGENT vers l'ADMIN
    """
    TYPE_ECHANGE = (
        ('uv_to_cash', '📱 UV → Cash'),
        ('wave_to_cash', '💳 Wave → Cash'),
        ('cash_to_uv', '💰 Cash → UV'),
        ('cash_to_wave', '💰 Cash → Wave'),
    )
    
    STATUT_CHOICES = (
        ('en_attente', '⏳ En attente'),
        ('valide', '✅ Validé'),
        ('refuse', '❌ Refusé'),
    )
    
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='demandes')
    type_echange = models.CharField(max_length=20, choices=TYPE_ECHANGE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    motif = models.TextField(blank=True)
    
    traite_par = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_traitees')
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    def valider(self, admin_user):
        """
        Valider la demande et effectuer l'échange
        admin_user est l'instance Admin qui valide
        """
        # Vérifier que la demande est en attente
        if self.statut != 'en_attente':
            return False
        
        caisse_agent = self.agent.user.caisse
        caisse_admin = admin_user.user.caisse
        
        # ========== LOGIQUE SYMÉTRIQUE ==========
        
        # Cas 1: Agent donne UV → reçoit Cash
        if self.type_echange == 'uv_to_cash':
            if caisse_agent.solde_uv >= self.montant and caisse_admin.solde_cash >= self.montant:
                caisse_agent.solde_uv -= self.montant
                caisse_agent.solde_cash += self.montant
                caisse_admin.solde_cash -= self.montant
                caisse_admin.solde_uv += self.montant
                self.statut = 'valide'
                self.traite_par = admin_user
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_admin.save()
                self.save()  # 🔴 IMPORTANT: Sauvegarder la demande
                return True
            return False
        
        # Cas 2: Agent donne Wave → reçoit Cash
        elif self.type_echange == 'wave_to_cash':
            if caisse_agent.solde_wave >= self.montant and caisse_admin.solde_cash >= self.montant:
                caisse_agent.solde_wave -= self.montant
                caisse_agent.solde_cash += self.montant
                caisse_admin.solde_cash -= self.montant
                caisse_admin.solde_wave += self.montant
                self.statut = 'valide'
                self.traite_par = admin_user
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_admin.save()
                self.save()  # 🔴 IMPORTANT: Sauvegarder la demande
                return True
            return False
        
        # Cas 3: Agent donne Cash → reçoit UV
        elif self.type_echange == 'cash_to_uv':
            if caisse_agent.solde_cash >= self.montant and caisse_admin.solde_uv >= self.montant:
                caisse_agent.solde_cash -= self.montant
                caisse_agent.solde_uv += self.montant
                caisse_admin.solde_uv -= self.montant
                caisse_admin.solde_cash += self.montant
                self.statut = 'valide'
                self.traite_par = admin_user
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_admin.save()
                self.save()  # 🔴 IMPORTANT: Sauvegarder la demande
                return True
            return False
        
        # Cas 4: Agent donne Cash → reçoit Wave
        elif self.type_echange == 'cash_to_wave':
            if caisse_agent.solde_cash >= self.montant and caisse_admin.solde_wave >= self.montant:
                caisse_agent.solde_cash -= self.montant
                caisse_agent.solde_wave += self.montant
                caisse_admin.solde_wave -= self.montant
                caisse_admin.solde_cash += self.montant
                self.statut = 'valide'
                self.traite_par = admin_user
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_admin.save()
                self.save()  # 🔴 IMPORTANT: Sauvegarder la demande
                return True
            return False
        
        return False
    
    def __str__(self):
        return f"{self.agent.nom} - {self.get_type_echange_display()} - {self.montant:,.0f} FCFA - {self.get_statut_display()}"
    
    class Meta:
        verbose_name = "Demande d'approvisionnement"
        verbose_name_plural = "Demandes d'approvisionnement"
        ordering = ['-date_demande']


class ApprovisionnementDirect(models.Model):
    """
    Approvisionnement direct ADMIN → AGENT
    """
    TYPE_CHOICES = (
        ('cash', '💰 Cash'),
        ('uv', '📱 UV Touspiont'),
        ('wave', '💳 Wave'),
    )
    
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='approvisionnements')
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='approvisionnements')
    type_approvisionnement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        caisse_admin = self.admin.user.caisse
        caisse_agent = self.agent.user.caisse
        
        if self.type_approvisionnement == 'cash':
            caisse_admin.solde_cash -= self.montant
            caisse_agent.solde_cash += self.montant
        elif self.type_approvisionnement == 'uv':
            caisse_admin.solde_uv -= self.montant
            caisse_agent.solde_uv += self.montant
        elif self.type_approvisionnement == 'wave':
            caisse_admin.solde_wave -= self.montant
            caisse_agent.solde_wave += self.montant
        
        caisse_admin.save()
        caisse_agent.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.admin.nom} → {self.agent.nom} - {self.get_type_approvisionnement_display()} - {self.montant:,.0f} FCFA"
    
    class Meta:
        verbose_name = "Approvisionnement direct"
        verbose_name_plural = "Approvisionnements directs"
        ordering = ['-date']


# ==================== SIGNALS ====================

@receiver(post_save, sender=User)
def create_user_caisse(sender, instance, created, **kwargs):
    """Crée automatiquement une caisse pour chaque nouvel utilisateur"""
    if created:
        Caisse.objects.get_or_create(user=instance)


@receiver(post_save, sender=Admin)
def create_admin_profile(sender, instance, created, **kwargs):
    """S'assure que l'admin a une caisse"""
    if created:
        Caisse.objects.get_or_create(user=instance.user)


@receiver(post_save, sender=Agent)
def create_agent_profile(sender, instance, created, **kwargs):
    """S'assure que l'agent a une caisse"""
    if created:
        Caisse.objects.get_or_create(user=instance.user)