# transactions/urls.py (version simplifiée avec Admin et Agent)
from django.urls import path
from . import views

urlpatterns = [
    # Redirection vers le bon dashboard
    path('', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Tableaux de bord
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('dashboard/agent/', views.dashboard_agent, name='dashboard_agent'),
    
    # Transaction pour l'utilisateur connecté (ADMIN ou AGENT)
    path('transaction/<str:operateur>/<str:type_transaction>/', views.transaction_user, name='transaction_user'),
    
    # Demandes d'approvisionnement
    path('demander-approvisionnement/', views.demander_approvisionnement, name='demander_approvisionnement'),
    path('api/demander-approvisionnement/', views.demander_approvisionnement_api, name='demander_approvisionnement_api'),
    
    path('valider-demande/<int:demande_id>/', views.valider_demande, name='valider_demande'),
    
    # Historique
    path('historique/', views.historique_admin, name='historique_admin'),
    path('mes-transactions/', views.historique_agent, name='historique_agent'),
    path('mes-demandes/', views.historique_demandes_agent, name='historique_demandes_agent'),
    
    # Impression
    path('impression/<str:transaction_id>/', views.impression_recu, name='impression_recu'),
    
    # API AJAX
    path('api/calculer-frais/', views.ajax_calculer_frais, name='ajax_calculer_frais'),
    # urls.py
    path('gestion-agents/', views.gestion_agents, name='gestion_agents'),
    path('ajouter-agent/', views.ajouter_agent, name='ajouter_agent'),
    path('modifier-caisse/', views.modifier_caisse, name='modifier_caisse'),
    path('api/agent-caisse/<int:agent_id>/', views.api_agent_caisse, name='api_agent_caisse'),
    path('supprimer-agent/', views.supprimer_agent, name='supprimer_agent'),
    path('activer-agent/<int:agent_id>/', views.activer_agent, name='activer_agent'),
    path('agent/<int:agent_id>/', views.detail_agent, name='detail_agent'),
    path('exporter-historique-csv/', lambda request: views.exporter_historique_agent(request, 'csv'), name='exporter_historique_agent_csv'),
    path('exporter-historique-excel/', lambda request: views.exporter_historique_agent(request, 'excel'), name='exporter_historique_agent_excel'),
    path('exporter-rapport-csv/', lambda request: views.exporter_rapport_complet_agent(request, 'csv'), name='exporter_rapport_complet_agent_csv'),
    path('exporter-rapport-excel/', lambda request: views.exporter_rapport_complet_agent(request, 'excel'), name='exporter_rapport_complet_agent_excel'), path('logout/', views.logout_view, name='logout'),
]
