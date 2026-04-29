# transactions/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ==================== REDIRECTION ====================
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    
    # ==================== TABLEAUX DE BORD ====================
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/agent/', views.dashboard_agent, name='dashboard_agent'),
    path('dashboard/assistant/', views.dashboard_assistant, name='dashboard_assistant'),
    
    # ==================== TRANSACTIONS ====================
    path('transaction/<str:operateur>/<str:type_transaction>/', views.transaction_user, name='transaction_user'),
    path('impression/<str:transaction_id>/', views.impression_recu, name='impression_recu'),
    
    # ==================== DEMANDES D'APPROVISIONNEMENT ====================
    path('demander-approvisionnement/', views.demander_approvisionnement, name='demander_approvisionnement'),
    path('api/demander-approvisionnement/', views.demander_approvisionnement_api, name='demander_approvisionnement_api'),
    path('valider-demande/<int:demande_id>/', views.valider_demande, name='valider_demande'),
    
    # ==================== HISTORIQUES ====================
    path('historique/', views.historique_admin, name='historique_admin'),
    path('mes-transactions/', views.historique_agent, name='historique_agent'),
    path('mes-demandes/', views.historique_demandes_agent, name='historique_demandes_agent'),
    path('traiter-demande-assistant/<int:demande_id>/', views.traiter_demande_assistant, name='traiter_demande_assistant'),
    
    # ==================== GESTION DES AGENTS ====================
    path('gestion-agents/', views.gestion_agents, name='gestion_agents'),
    path('ajouter-agent/', views.ajouter_agent, name='ajouter_agent'),
    path('modifier-caisse/', views.modifier_caisse, name='modifier_caisse'),
    path('api/agent-caisse/<int:agent_id>/', views.api_agent_caisse, name='api_agent_caisse'),
    path('supprimer-agent/', views.supprimer_agent, name='supprimer_agent'),
    path('activer-agent/<int:agent_id>/', views.activer_agent, name='activer_agent'),
    path('agent/<int:agent_id>/', views.detail_agent, name='detail_agent'),
    
    # ==================== EXPORTS ====================
    path('exporter-historique-csv/', lambda request: views.exporter_historique_agent(request, 'csv'), name='exporter_historique_agent_csv'),
    path('exporter-historique-excel/', lambda request: views.exporter_historique_agent(request, 'excel'), name='exporter_historique_agent_excel'),
    path('exporter-rapport-pdf/', lambda request: views.exporter_rapport_complet_agent(request, 'pdf'), name='exporter_rapport_complet_agent_pdf'),
    path('exporter-rapport-excel/', lambda request: views.exporter_rapport_complet_agent(request, 'excel'), name='exporter_rapport_complet_agent_excel'),
    
    # ==================== API AJAX ====================
    path('api/calculer-frais/', views.ajax_calculer_frais, name='ajax_calculer_frais'),
    
    # ==================== RAPPORTS ADMIN ====================
    path('rapports-admin/', views.rapports_admin, name='rapports_admin'),
    path('generer-rapport-admin/', views.generer_rapport_admin, name='generer_rapport_admin'),
    
    # ==================== API FACTURES ====================
    path('api/factures/', views.api_factures, name='api_factures'),
    #path('api/factures/<int:facture_id>/', views.api_facture_detail, name='api_facture_detail'),
    
    # ==================== GESTION FACTURES (nouveau préfixe 'gestion/') ====================
    path('api/rechercher-client/', views.rechercher_client_api, name='rechercher_client_api'),
    path('detail-facture/<int:facture_id>/', views.detail_facture, name='detail_facture'),
    path('gestion/ajouter-facture/', views.creer_facture, name='creer_facture'),
    path('gestion/modifier-facture/<int:facture_id>/', views.modifier_facture, name='modifier_facture'),
    path('gestion/supprimer-facture/<int:facture_id>/', views.supprimer_facture, name='supprimer_facture'),
    path('gestion/enregistrer-paiement/<int:facture_id>/', views.enregistrer_paiement_facture, name='enregistrer_paiement_facture'),
    path('generer-facture-pdf/<int:facture_id>/', views.generer_facture_pdf, name='generer_facture_pdf'),
    path('generer-facture-80mm/<int:facture_id>/', views.generer_facture_80mm, name='generer_facture_80mm'),
    # ==================== API DETTES ====================
    path('api/dettes/', views.api_dettes, name='api_dettes'),
    path('api/dettes/<int:dette_id>/', views.api_dette_detail, name='api_dette_detail'),
    
    # ==================== GESTION DETTES (nouveau préfixe 'gestion/') ====================
    path('gestion/ajouter-dette/', views.ajouter_dette, name='ajouter_dette'),
    path('gestion/modifier-dette/<int:dette_id>/', views.modifier_dette, name='modifier_dette'),
    path('gestion/supprimer-dette/<int:dette_id>/', views.supprimer_dette, name='supprimer_dette'),
    path('gestion/enregistrer-remboursement/<int:dette_id>/', views.enregistrer_remboursement_dette, name='enregistrer_remboursement_dette'),
     
    # ==================== API COMPTES ÉPARGNE ====================
    path('api/comptes-epargne/', views.api_comptes_epargne, name='api_comptes_epargne'),
    path('gestion/operation-compte/<int:compte_id>/', views.operation_compte, name='operation_compte'),
    path('detail-assistant/<int:assistant_id>/', views.detail_assistant, name='detail_assistant'),
    path('api/historique-operations/', views.api_historique_operations, name='api_historique_operations'),
    path('api/totaux-operations/', views.api_totaux_operations, name='api_totaux_operations'),
    
    path('ajouter_assistant/', views.ajouter_assistant, name='ajouter_assistant'),
    path('detail_assistant/<int:assistant_id>/', views.detail_assistant, name='detail_assistant'),
    path('modifier-mot-de-passe-assistant/<int:assistant_id>/', views.modifier_mot_de_passe_assistant, name='modifier_mot_de_passe_assistant'),
    # ==================== API ANALYSE ====================
    path('api/analyse-stats/', views.api_analyse_stats, name='api_analyse_stats'),
    
    # ==================== AUTHENTIFICATION ====================
    path('logout/', views.logout_view, name='logout'),
]