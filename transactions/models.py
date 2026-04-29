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
    created_by = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='agents_crees')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.telephone}"
    
    class Meta:
        verbose_name = "Agent"
        verbose_name_plural = "Agents"


class Assistant(models.Model):
    """
    ASSISTANT - Compte assistant avec droits similaires à l'Admin
    Peut faire: dépôt, retrait, crédit
    Un Admin peut avoir plusieurs Assistants
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='assistant_profile')
    nom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    est_actif = models.BooleanField(default=True)
    
    # Lié à un Admin (un admin peut avoir plusieurs assistants)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='assistants')
    
    created_by = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='assistants_crees')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} - {self.telephone} (Assistant de {self.admin.nom})"
    
    @property
    def get_caisse(self):
        """L'assistant partage la caisse de son Admin"""
        return self.admin.user.caisse
    
    class Meta:
        verbose_name = "Assistant"
        verbose_name_plural = "Assistants"


class Caisse(models.Model):
    """
    Caisse - Chaque utilisateur (ADMIN, AGENT) a sa propre caisse
    L'ASSISTANT partage la caisse de son ADMIN
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


class Transaction(models.Model):
    """
    Transaction - Pour ADMIN, AGENTS et ASSISTANTS
    L'ASSISTANT utilise la caisse de son ADMIN
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
    
    # Qui a fait la transaction (User: Admin, Agent ou Assistant)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    
    # Type d'utilisateur qui a fait la transaction
    ROLE_CHOICES = (
        ('admin', 'Administrateur'),
        ('agent', 'Agent'),
        ('assistant', 'Assistant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    
    # Si c'est un assistant, quel admin
    assistant_admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions_assistant')
    
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
                'credit': 'C',
            }.get(self.type_transaction, 'T')
            
            self.reference = f"{prefix}{type_prefix}{uuid.uuid4().hex[:8].upper()}"
        
        self.commission = self.calculer_commission()
        self.frais_operateur = self.calculer_frais_operateur()
        
        # ========== RÉCUPÉRER LA BONNE CAISSE ==========
        # Si c'est un assistant, utiliser la caisse de son ADMIN
        if self.role == 'assistant' and self.assistant_admin:
            # L'assistant utilise la caisse de son admin
            caisse = self.assistant_admin.user.caisse
        else:
            # Sinon, utiliser la caisse de l'utilisateur
            caisse = self.user.caisse
        
        # ========== MISE À JOUR DES SOLDES ==========
        # ORANGE, MALITEL, TELECEL (via UV Touspiont)
        if self.operateur in ['orange', 'malitel', 'telecel']:
            if self.type_transaction == 'depot':
                # DÉPÔT: client donne cash → agent donne ses UV
                caisse.solde_cash += self.montant
                caisse.solde_uv -= self.montant
                
            elif self.type_transaction == 'retrait':
                # RETRAIT: client prend cash → agent reçoit UV
                caisse.solde_cash -= self.montant
                caisse.solde_uv += self.montant
                
            elif self.type_transaction == 'credit':
                # CRÉDIT: client recharge → agent donne ses UV
                caisse.solde_cash += self.montant
                caisse.solde_uv -= self.montant
        
        # WAVE
        elif self.operateur == 'wave':
            if self.type_transaction == 'depot':
                # DÉPÔT WAVE: client donne cash → agent donne ses Wave
                caisse.solde_cash += self.montant
                caisse.solde_wave -= self.montant
                
            elif self.type_transaction == 'retrait':
                # RETRAIT WAVE: client prend cash → agent reçoit Wave
                caisse.solde_cash -= self.montant
                caisse.solde_wave += self.montant
        
        # Sauvegarder la caisse
        caisse.save()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        role_display = dict(self.ROLE_CHOICES).get(self.role, '')
        return f"[{role_display}] {self.get_type_transaction_display()} {self.get_operateur_display()} - {self.montant} FCFA"
    
    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-date']

class DemandeApprovisionnement(models.Model):
    """
    Demande d'approvisionnement de l'AGENT vers l'ADMIN ou un ASSISTANT
    L'agent peut choisir à qui il demande (Admin ou un Assistant spécifique)
    Un Admin peut avoir plusieurs Assistants
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
    
    DESTINATAIRE_CHOICES = (
        ('admin', 'Administrateur'),
        ('assistant', 'Assistant'),
    )
    
    # Agent qui demande
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='demandes_approvisionnement')
    
    # À qui il demande
    destinataire_type = models.CharField(max_length=20, choices=DESTINATAIRE_CHOICES, default='admin')
    assistant_destinataire = models.ForeignKey(Assistant, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_recues')
    
    type_echange = models.CharField(max_length=20, choices=TYPE_ECHANGE)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    motif = models.TextField(blank=True)
    
    # Qui a traité
    traite_par_admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_traitees_admin')
    traite_par_assistant = models.ForeignKey(Assistant, on_delete=models.SET_NULL, null=True, blank=True, related_name='demandes_traitees_assistant')
    
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    def valider_par_admin(self, admin_user):
        """
        Valider la demande par un ADMIN
        """
        return self._valider(admin_user.user.caisse, admin_user, 'admin')
    
    def valider_par_assistant(self, assistant_user):
        """
        Valider la demande par un ASSISTANT
        L'assistant utilise la caisse de SON ADMIN (pas sa propre caisse)
        """
        try:
            # Récupérer le profil assistant
            assistant = assistant_user.assistant_profile
            # Récupérer la caisse de l'admin associé à l'assistant
            caisse_admin = assistant.admin.user.caisse
            return self._valider(caisse_admin, assistant_user, 'assistant')
        except Exception as e:
            print(f"Erreur lors de la validation par assistant: {e}")
            return False
    
    def _valider(self, caisse_destinataire, destinataire, destinataire_type):
        """
        Logique de validation commune
        caisse_destinataire = caisse de celui qui valide (Admin ou Assistant)
        """
        if self.statut != 'en_attente':
            return False
        
        caisse_agent = self.agent.user.caisse
        
        # Cas 1: Agent donne UV → reçoit Cash
        if self.type_echange == 'uv_to_cash':
            if caisse_agent.solde_uv >= self.montant and caisse_destinataire.solde_cash >= self.montant:
                caisse_agent.solde_uv -= self.montant
                caisse_agent.solde_cash += self.montant
                caisse_destinataire.solde_cash -= self.montant
                caisse_destinataire.solde_uv += self.montant
                self.statut = 'valide'
                if destinataire_type == 'admin':
                    self.traite_par_admin = destinataire
                else:
                    self.traite_par_assistant = destinataire
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_destinataire.save()
                self.save()
                return True
            return False
        
        # Cas 2: Agent donne Wave → reçoit Cash
        elif self.type_echange == 'wave_to_cash':
            if caisse_agent.solde_wave >= self.montant and caisse_destinataire.solde_cash >= self.montant:
                caisse_agent.solde_wave -= self.montant
                caisse_agent.solde_cash += self.montant
                caisse_destinataire.solde_cash -= self.montant
                caisse_destinataire.solde_wave += self.montant
                self.statut = 'valide'
                if destinataire_type == 'admin':
                    self.traite_par_admin = destinataire
                else:
                    self.traite_par_assistant = destinataire
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_destinataire.save()
                self.save()
                return True
            return False
        
        # Cas 3: Agent donne Cash → reçoit UV
        elif self.type_echange == 'cash_to_uv':
            if caisse_agent.solde_cash >= self.montant and caisse_destinataire.solde_uv >= self.montant:
                caisse_agent.solde_cash -= self.montant
                caisse_agent.solde_uv += self.montant
                caisse_destinataire.solde_uv -= self.montant
                caisse_destinataire.solde_cash += self.montant
                self.statut = 'valide'
                if destinataire_type == 'admin':
                    self.traite_par_admin = destinataire
                else:
                    self.traite_par_assistant = destinataire
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_destinataire.save()
                self.save()
                return True
            return False
        
        # Cas 4: Agent donne Cash → reçoit Wave
        elif self.type_echange == 'cash_to_wave':
            if caisse_agent.solde_cash >= self.montant and caisse_destinataire.solde_wave >= self.montant:
                caisse_agent.solde_cash -= self.montant
                caisse_agent.solde_wave += self.montant
                caisse_destinataire.solde_wave -= self.montant
                caisse_destinataire.solde_cash += self.montant
                self.statut = 'valide'
                if destinataire_type == 'admin':
                    self.traite_par_admin = destinataire
                else:
                    self.traite_par_assistant = destinataire
                self.date_traitement = timezone.now()
                caisse_agent.save()
                caisse_destinataire.save()
                self.save()
                return True
            return False
        
        return False
    
    @property
    def destinataire_nom(self):
        if self.destinataire_type == 'admin':
            return "Administrateur"
        else:
            if self.assistant_destinataire:
                return f"Assistant {self.assistant_destinataire.nom}"
            return "Assistant"
    
    def __str__(self):
        return f"{self.agent.nom} → {self.destinataire_nom} - {self.get_type_echange_display()} - {self.montant:,.0f} FCFA"
    
    class Meta:
        verbose_name = "Demande d'approvisionnement"
        verbose_name_plural = "Demandes d'approvisionnement"
        ordering = ['-date_demande']

 
class ApprovisionnementDirect(models.Model):
    """
    Approvisionnement direct ADMIN ou ASSISTANT → AGENT
    """
    TYPE_CHOICES = (
        ('cash', '💰 Cash'),
        ('uv', '📱 UV Touspiont'),
        ('wave', '💳 Wave'),
    )
    
    SOURCE_CHOICES = (
        ('admin', 'Administrateur'),
        ('assistant', 'Assistant'),
    )
    
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='admin')
    admin_source = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvisionnements_emis')
    assistant_source = models.ForeignKey(Assistant, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvisionnements_emis')
    
    agent_destinataire = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='approvisionnements_recus')
    type_approvisionnement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Caisse de la source
        if self.source_type == 'admin':
            caisse_source = self.admin_source.user.caisse
        else:
            caisse_source = self.assistant_source.user.caisse
        
        caisse_agent = self.agent_destinataire.user.caisse
        
        if self.type_approvisionnement == 'cash':
            caisse_source.solde_cash -= self.montant
            caisse_agent.solde_cash += self.montant
        elif self.type_approvisionnement == 'uv':
            caisse_source.solde_uv -= self.montant
            caisse_agent.solde_uv += self.montant
        elif self.type_approvisionnement == 'wave':
            caisse_source.solde_wave -= self.montant
            caisse_agent.solde_wave += self.montant
        
        caisse_source.save()
        caisse_agent.save()
        super().save(*args, **kwargs)
    
    @property
    def source_nom(self):
        if self.source_type == 'admin':
            return self.admin_source.nom if self.admin_source else "Admin"
        else:
            return self.assistant_source.nom if self.assistant_source else "Assistant"
    
    def __str__(self):
        return f"{self.source_nom} ({self.get_source_type_display()}) → {self.agent_destinataire.nom} - {self.get_type_approvisionnement_display()} - {self.montant:,.0f} FCFA"
    
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


@receiver(post_save, sender=Assistant)
def create_assistant_profile(sender, instance, created, **kwargs):
    """S'assure que l'assistant a une caisse"""
    if created:
        Caisse.objects.get_or_create(user=instance.user)


@receiver(post_save, sender=Caisse)
def init_soldes_hier(sender, instance, created, **kwargs):
    """Initialise les soldes d'hier avec les soldes actuels lors de la création"""
    if created:
        instance.solde_cash_hier = instance.solde_cash
        instance.solde_uv_hier = instance.solde_uv
        instance.solde_wave_hier = instance.solde_wave
        instance.save()


# ==================== MODÈLES POUR RAPPORTS ET GESTION ====================

class Facture(models.Model):
    TYPE_CHOICES = [
        ('cliente', 'Facture Client - Client nous doit'),
        ('fournisseur', 'Facture Fournisseur - Nous devons'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('partiellement_payee', 'Partiellement payée'),
        ('payee', 'Payée'),
        ('annulee', 'Annulée'),
    ]
    
    type_facture = models.CharField(max_length=20, choices=TYPE_CHOICES, default='cliente')
    
    numero = models.CharField(max_length=50, unique=True)
    
    # Informations de la personne
    personne_nom = models.CharField(max_length=200)
    personne_email = models.EmailField(blank=True, null=True)
    personne_telephone = models.CharField(max_length=50, blank=True)
    
    montant_total = models.DecimalField(max_digits=12, decimal_places=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    date_emission = models.DateField(auto_now_add=True)
    date_echeance = models.DateField()
    date_paiement_complet = models.DateField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_attente')
    
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE)
    cree_le = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_emission']
    
    @property
    def reste_a_payer(self):
        return self.montant_total - self.montant_paye
    
    @property
    def sens_creance(self):
        """Indique qui doit à qui"""
        if self.type_facture == 'cliente':
            return f"{self.personne_nom} nous doit {self.reste_a_payer:,.0f} FCFA"
        else:
            return f"Nous devons {self.reste_a_payer:,.0f} FCFA à {self.personne_nom}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            from datetime import datetime
            prefix = "FACT-C" if self.type_facture == 'cliente' else "FACT-F"
            self.numero = f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if self.montant_paye >= self.montant_total and self.montant_total > 0:
            self.statut = 'payee'
            if not self.date_paiement_complet:
                from django.utils import timezone
                self.date_paiement_complet = timezone.now().date()
        elif self.montant_paye > 0:
            self.statut = 'partiellement_payee'
        super().save(*args, **kwargs)
    
    def __str__(self):
        sens = "→" if self.type_facture == 'cliente' else "←"
        return f"{self.numero} {sens} {self.personne_nom} ({self.montant_total:,.0f} FCFA)"


class PaiementFacture(models.Model):
    MODE_CHOICES = [
        ('cash', 'Espèces'),
        ('uv', 'UV Touchpiont'),
        ('wave', 'UV Wave'),
        ('virement', 'Virement bancaire'),
    ]
    
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE, related_name='paiements')
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    mode_paiement = models.CharField(max_length=20, choices=MODE_CHOICES)
    date_paiement = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-date_paiement']
    
    def __str__(self):
        return f"Paiement {self.facture.numero} - {self.montant} FCFA"


class Dette(models.Model):
    STATUT_CHOICES = [
        ('active', 'Active'),
        ('payee', 'Payée'),
    ]
    
    debiteur = models.ForeignKey('Agent', on_delete=models.CASCADE, related_name='dettes')
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    montant_rembourse = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    
    date_creation = models.DateField(auto_now_add=True)
    date_echeance = models.DateField()
    date_remboursement_complet = models.DateField(null=True, blank=True)
    
    motif = models.TextField(blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='active')
    
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-date_creation']
    
    @property
    def reste_a_payer(self):
        return self.montant - self.montant_rembourse
    
    def save(self, *args, **kwargs):
        if self.montant_rembourse >= self.montant and self.montant > 0:
            self.statut = 'payee'
            if not self.date_remboursement_complet:
                from django.utils import timezone
                self.date_remboursement_complet = timezone.now().date()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Dette de {self.debiteur.nom} - {self.montant} FCFA"


class RemboursementDette(models.Model):
    MODE_CHOICES = [
        ('cash', 'Espèces'),
        ('uv', 'UV Touchpiont'),
        ('wave', 'UV Wave'),
    ]
    
    dette = models.ForeignKey(Dette, on_delete=models.CASCADE, related_name='remboursements')
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    mode_paiement = models.CharField(max_length=20, choices=MODE_CHOICES)
    date_remboursement = models.DateTimeField(auto_now_add=True)
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-date_remboursement']
    
    def __str__(self):
        return f"Remboursement {self.dette.id} - {self.montant} FCFA"


class CompteEpargne(models.Model):
    titulaire = models.CharField(max_length=200)
    numero_compte = models.CharField(max_length=50, unique=True)
    solde = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    taux_interet = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    date_ouverture = models.DateField(auto_now_add=True)
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        ordering = ['-date_ouverture']
    
    def __str__(self):
        return f"{self.numero_compte} - {self.titulaire}"


class OperationCompte(models.Model):
    TYPE_CHOICES = [
        ('depot', 'Dépôt'),
        ('retrait', 'Retrait'),
        ('interet', 'Intérêt crédité'),
    ]
    
    compte = models.ForeignKey(CompteEpargne, on_delete=models.CASCADE, related_name='operations')
    type_operation = models.CharField(max_length=20, choices=TYPE_CHOICES)
    montant = models.DecimalField(max_digits=12, decimal_places=0)
    description = models.CharField(max_length=200, blank=True)
    date_operation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.montant} FCFA"
    
# ========== MODELS POUR LA GESTION DE CAISSE ADMIN ==========

class OperationCaisse(models.Model):
    """Suivi des operations d'encaissement/decaissement"""
    TYPE_OPERATION = (
        ('encaissement', 'Encaissement'),
        ('decaissement', 'Decaissement'),
    )
    caisse = models.ForeignKey('Caisse', on_delete=models.CASCADE, related_name='operations_caisse')
    type_operation = models.CharField(max_length=20, choices=TYPE_OPERATION)
    montant = models.BigIntegerField()
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_operation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.montant:,.0f} FCFA - {self.user.username}"
    
    class Meta:
        ordering = ['-date_operation']


class OperationUv(models.Model):
    """Suivi des operations sur les comptes UV (Touchpoint et Wave)"""
    TYPE_OPERATION = (
        ('ajout', 'Ajout'),
        ('retrait', 'Retrait'),
    )
    TYPE_UV = (
        ('touchpoint', 'UV Touchpoint'),
        ('wave', 'UV Wave'),
    )
    caisse = models.ForeignKey('Caisse', on_delete=models.CASCADE, related_name='operations_uv')
    type_operation = models.CharField(max_length=20, choices=TYPE_OPERATION)
    type_uv = models.CharField(max_length=20, choices=TYPE_UV)
    montant = models.BigIntegerField()
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date_operation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_type_uv_display()} - {self.get_type_operation_display()} - {self.montant:,.0f} FCFA"
    
    class Meta:
        ordering = ['-date_operation']


class CompteEpargneAdmin(models.Model):
    """Compte epargne pour l'administrateur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='compte_epargne')
    titulaire = models.CharField(max_length=200)
    solde = models.BigIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Epargne - {self.titulaire}: {self.solde:,.0f} FCFA"
    
    class Meta:
        verbose_name = "Compte epargne admin"
        verbose_name_plural = "Comptes epargne admin"


class OperationEpargne(models.Model):
    """Suivi des operations sur le compte epargne"""
    TYPE_OPERATION = (
        ('depot', 'Depot'),
        ('retrait', 'Retrait'),
    )
    compte = models.ForeignKey(CompteEpargneAdmin, on_delete=models.CASCADE, related_name='operations')
    type_operation = models.CharField(max_length=20, choices=TYPE_OPERATION)
    montant = models.BigIntegerField()
    description = models.TextField(blank=True)
    date_operation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_type_operation_display()} - {self.montant:,.0f} FCFA - {self.date_operation}"
    
    class Meta:
        ordering = ['-date_operation']