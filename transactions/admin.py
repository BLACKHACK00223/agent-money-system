# transactions/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Admin, Agent, Assistant, Caisse, Transaction, DemandeApprovisionnement, ApprovisionnementDirect


@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'point_service', 'solde_cash', 'solde_uv', 'solde_wave', 'created_at')
    search_fields = ('nom', 'telephone', 'point_service')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'nom', 'telephone', 'point_service', 'adresse')
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def solde_cash(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_cash:,.0f} FCFA"
        return "0 FCFA"
    solde_cash.short_description = "💰 Cash"
    
    def solde_uv(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_uv:,.0f} FCFA"
        return "0 FCFA"
    solde_uv.short_description = "📱 UV Touspiont"
    
    def solde_wave(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_wave:,.0f} FCFA"
        return "0 FCFA"
    solde_wave.short_description = "💳 Wave"


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'est_actif', 'solde_cash', 'solde_uv', 'solde_wave', 'created_at')
    search_fields = ('nom', 'telephone', 'email')
    list_filter = ('est_actif', 'created_at')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'nom', 'telephone', 'email')
        }),
        ('Statut', {
            'fields': ('est_actif',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activer_agents', 'desactiver_agents']
    
    def solde_cash(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_cash:,.0f} FCFA"
        return "0 FCFA"
    solde_cash.short_description = "💰 Cash"
    
    def solde_uv(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_uv:,.0f} FCFA"
        return "0 FCFA"
    solde_uv.short_description = "📱 UV Touspiont"
    
    def solde_wave(self, obj):
        if hasattr(obj.user, 'caisse'):
            return f"{obj.user.caisse.solde_wave:,.0f} FCFA"
        return "0 FCFA"
    solde_wave.short_description = "💳 Wave"
    
    def activer_agents(self, request, queryset):
        queryset.update(est_actif=True)
        self.message_user(request, f"{queryset.count()} agent(s) activé(s)")
    activer_agents.short_description = "✅ Activer les agents sélectionnés"
    
    def desactiver_agents(self, request, queryset):
        queryset.update(est_actif=False)
        self.message_user(request, f"{queryset.count()} agent(s) désactivé(s)")
    desactiver_agents.short_description = "❌ Désactiver les agents sélectionnés"


@admin.register(Assistant)
class AssistantAdmin(admin.ModelAdmin):
    list_display = ('nom', 'telephone', 'admin', 'est_actif', 'solde_cash', 'solde_uv', 'solde_wave', 'created_at')
    search_fields = ('nom', 'telephone', 'email', 'admin__nom')
    list_filter = ('est_actif', 'created_at', 'admin')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'nom', 'telephone', 'email')
        }),
        ('Administrateur', {
            'fields': ('admin',)
        }),
        ('Statut', {
            'fields': ('est_actif',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activer_assistants', 'desactiver_assistants']
    
    def solde_cash(self, obj):
        caisse = obj.admin.user.caisse if obj.admin else None
        if caisse:
            return f"{caisse.solde_cash:,.0f} FCFA"
        return "0 FCFA"
    solde_cash.short_description = "💰 Cash (Admin)"
    
    def solde_uv(self, obj):
        caisse = obj.admin.user.caisse if obj.admin else None
        if caisse:
            return f"{caisse.solde_uv:,.0f} FCFA"
        return "0 FCFA"
    solde_uv.short_description = "📱 UV Touspiont (Admin)"
    
    def solde_wave(self, obj):
        caisse = obj.admin.user.caisse if obj.admin else None
        if caisse:
            return f"{caisse.solde_wave:,.0f} FCFA"
        return "0 FCFA"
    solde_wave.short_description = "💳 Wave (Admin)"
    
    def activer_assistants(self, request, queryset):
        queryset.update(est_actif=True)
        self.message_user(request, f"{queryset.count()} assistant(s) activé(s)")
    activer_assistants.short_description = "✅ Activer les assistants sélectionnés"
    
    def desactiver_assistants(self, request, queryset):
        queryset.update(est_actif=False)
        self.message_user(request, f"{queryset.count()} assistant(s) désactivé(s)")
    desactiver_assistants.short_description = "❌ Désactiver les assistants sélectionnés"


@admin.register(Caisse)
class CaisseAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'type_utilisateur', 'solde_cash', 'solde_uv', 'solde_wave', 'solde_total', 'updated_at')
    search_fields = ('user__username', 'user__agent_profile__nom', 'user__admin_profile__nom', 'user__assistant_profile__nom')
    list_filter = ('updated_at',)
    readonly_fields = ('updated_at',)
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Soldes', {
            'fields': ('solde_cash', 'solde_uv', 'solde_wave')
        }),
        ('Limites', {
            'fields': ('limite_cash', 'limite_uv', 'limite_wave'),
            'classes': ('collapse',)
        }),
        ('Mise à jour', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def utilisateur(self, obj):
        if hasattr(obj.user, 'admin_profile'):
            return obj.user.admin_profile.nom
        elif hasattr(obj.user, 'agent_profile'):
            return obj.user.agent_profile.nom
        elif hasattr(obj.user, 'assistant_profile'):
            return f"{obj.user.assistant_profile.nom} (Assistant)"
        return obj.user.username
    utilisateur.short_description = "Utilisateur"
    
    def type_utilisateur(self, obj):
        if hasattr(obj.user, 'admin_profile'):
            return "🏦 ADMIN"
        elif hasattr(obj.user, 'agent_profile'):
            return "👤 AGENT"
        elif hasattr(obj.user, 'assistant_profile'):
            return "🤝 ASSISTANT"
        return "-"
    type_utilisateur.short_description = "Type"
    
    def solde_total(self, obj):
        total = obj.solde_cash + obj.solde_uv + obj.solde_wave
        return f"{total:,.0f} FCFA"
    solde_total.short_description = "💰 Solde total"


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'utilisateur', 'role_affichage', 'type_transaction', 'operateur', 'montant', 'numero_client', 'date', 'statut')
    list_filter = ('type_transaction', 'operateur', 'statut', 'date', 'role')
    search_fields = ('reference', 'numero_client', 'reference_operateur', 'user__username')
    readonly_fields = ('reference', 'commission', 'frais_operateur', 'date', 'updated_at')
    
    fieldsets = (
        ('Informations', {
            'fields': ('user', 'role', 'type_transaction', 'operateur')
        }),
        ('Client', {
            'fields': ('numero_client', 'nom_client')
        }),
        ('Montants', {
            'fields': ('montant', 'commission', 'frais_operateur')
        }),
        ('Références', {
            'fields': ('reference', 'reference_operateur')
        }),
        ('Statut', {
            'fields': ('statut', 'notes')
        }),
        ('Horodatage', {
            'fields': ('date', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def utilisateur(self, obj):
        if hasattr(obj.user, 'admin_profile'):
            return obj.user.admin_profile.nom
        elif hasattr(obj.user, 'agent_profile'):
            return obj.user.agent_profile.nom
        elif hasattr(obj.user, 'assistant_profile'):
            return obj.user.assistant_profile.nom
        return obj.user.username
    utilisateur.short_description = "Utilisateur"
    
    def role_affichage(self, obj):
        colors = {
            'admin': '#dc2626',
            'agent': '#10b981',
            'assistant': '#f59e0b',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_role_display())
    role_affichage.short_description = "Rôle"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(DemandeApprovisionnement)
class DemandeApprovisionnementAdmin(admin.ModelAdmin):
    list_display = ('id', 'agent', 'type_echange_display', 'montant', 'statut', 'destinataire_affichage', 'date_demande', 'date_traitement')
    list_filter = ('type_echange', 'statut', 'destinataire_type', 'date_demande')
    search_fields = ('agent__nom', 'agent__telephone', 'motif')
    readonly_fields = ('date_demande', 'date_traitement')
    
    fieldsets = (
        ('Demande', {
            'fields': ('agent', 'type_echange', 'montant', 'motif')
        }),
        ('Destinataire', {
            'fields': ('destinataire_type', 'assistant_destinataire')
        }),
        ('Traitement', {
            'fields': ('statut', 'traite_par_admin', 'traite_par_assistant', 'date_traitement')
        }),
        ('Dates', {
            'fields': ('date_demande',),
            'classes': ('collapse',)
        }),
    )
    
    def type_echange_display(self, obj):
        colors = {
            'uv_to_cash': '#28a745',
            'wave_to_cash': '#17a2b8',
            'cash_to_uv': '#fd7e14',
            'cash_to_wave': '#6f42c1',
        }
        color = colors.get(obj.type_echange, '#6c757d')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_type_echange_display())
    type_echange_display.short_description = "Type d'échange"
    
    def destinataire_affichage(self, obj):
        if obj.destinataire_type == 'admin':
            return "🏦 Administrateur"
        else:
            if obj.assistant_destinataire:
                return f"🤝 Assistant {obj.assistant_destinataire.nom}"
            return "🤝 Assistant"
    destinataire_affichage.short_description = "Destinataire"
    
    actions = ['valider_demandes', 'refuser_demandes']
    
    def valider_demandes(self, request, queryset):
        from django.utils import timezone
        admin_user = None
        if hasattr(request.user, 'admin_profile'):
            admin_user = request.user.admin_profile
        
        count = 0
        for demande in queryset.filter(statut='en_attente'):
            if demande.valider_par_admin(admin_user):
                count += 1
        
        self.message_user(request, f"{count} demande(s) validée(s)")
    valider_demandes.short_description = "✅ Valider les demandes sélectionnées"
    
    def refuser_demandes(self, request, queryset):
        from django.utils import timezone
        
        count = 0
        for demande in queryset.filter(statut='en_attente'):
            demande.statut = 'refuse'
            if hasattr(request.user, 'admin_profile'):
                demande.traite_par_admin = request.user.admin_profile
            demande.date_traitement = timezone.now()
            demande.save()
            count += 1
        
        self.message_user(request, f"{count} demande(s) refusée(s)")
    refuser_demandes.short_description = "❌ Refuser les demandes sélectionnées"


@admin.register(ApprovisionnementDirect)
class ApprovisionnementDirectAdmin(admin.ModelAdmin):
    list_display = ('id', 'source_affichage', 'agent_destinataire', 'type_approvisionnement', 'montant', 'date')
    list_filter = ('source_type', 'type_approvisionnement', 'date')
    search_fields = ('admin_source__nom', 'assistant_source__nom', 'agent_destinataire__nom', 'notes')
    readonly_fields = ('date',)
    
    fieldsets = (
        ('Source', {
            'fields': ('source_type', 'admin_source', 'assistant_source')
        }),
        ('Destinataire', {
            'fields': ('agent_destinataire',)
        }),
        ('Approvisionnement', {
            'fields': ('type_approvisionnement', 'montant', 'notes')
        }),
        ('Date', {
            'fields': ('date',),
            'classes': ('collapse',)
        }),
    )
    
    def source_affichage(self, obj):
        if obj.source_type == 'admin':
            return f"🏦 {obj.admin_source.nom}" if obj.admin_source else "🏦 Admin"
        else:
            return f"🤝 {obj.assistant_source.nom}" if obj.assistant_source else "🤝 Assistant"
    source_affichage.short_description = "Source"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin_source', 'assistant_source', 'agent_destinataire')


# Configuration du titre de l'admin
admin.site.site_header = "Agent Money - Administration"
admin.site.site_title = "Agent Money"
admin.site.index_title = "Tableau de bord d'administration"