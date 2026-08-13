# Auto-split depuis transactions/views.py (refactor)
# imports partages (niveau module d'origine)

import base64

from pathlib import Path

import django

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required

from django.contrib import messages

from django.http import JsonResponse

from django.views.decorators.http import require_POST

from django.db.models import Sum, Q

from datetime import datetime, timedelta

from decimal import Decimal

import json

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

from django.contrib.auth.models import User

from django.contrib.auth.hashers import make_password

from django.contrib.auth import logout

from django.views.decorators.http import require_http_methods

from django.utils import timezone

import csv

from ..models import Admin, Agent, Assistant, Caisse, CompteEpargneAdmin, OperationCaisse, OperationEpargne, OperationUv, Transaction, DemandeApprovisionnement, ApprovisionnementDirect

from openpyxl import Workbook

from openpyxl.styles import Font, Alignment, PatternFill

from reportlab.lib.pagesizes import A4

from reportlab.lib.units import cm

from reportlab.lib import colors

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from django.http import HttpResponse

from django.template.loader import get_template

from xhtml2pdf import pisa

import io

from ..models import (
    Admin, Agent, Assistant, Caisse, Transaction, DemandeApprovisionnement, 
    ApprovisionnementDirect, Facture, PaiementFacture, Dette, RemboursementDette,
    CompteEpargne, OperationCompte
)

from ..forms import (OrangeTransactionForm, WaveTransactionForm, 
                   MalitelTransactionForm, TelecelTransactionForm)

from django.shortcuts import get_object_or_404

from django.http import JsonResponse

from django.contrib.auth.decorators import login_required

from django.template.loader import render_to_string

from django.utils import timezone

from decimal import Decimal

from django.contrib.auth.decorators import login_required

from django.http import JsonResponse

from django.shortcuts import redirect, render, get_object_or_404

from django.contrib import messages

from django.db.models import Sum

from transactions.models import Agent, Assistant, Admin, Caisse, HistoriqueAgent

from django.core.paginator import Paginator

from datetime import datetime

from django.db.models import Sum, Q

from transactions.models import HistoriqueAgent, Agent

import json

import csv

from datetime import datetime, timedelta

from django.db.models import Sum

from django.core.paginator import Paginator

from django.http import JsonResponse, HttpResponse

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.decorators import login_required

from django.contrib import messages

from django.utils import timezone

from openpyxl import Workbook

from openpyxl.styles import Font, Alignment, PatternFill

from ..models import (
    Transaction, Agent, Admin, Caisse, DemandeApprovisionnement,
    Facture, PaiementFacture, Dette, RemboursementDette,
    CompteEpargne, OperationCompte
)

from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib import messages

from django.db.models import Sum

from django.http import JsonResponse, FileResponse

from django.utils import timezone

from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_http_methods

import json

from datetime import datetime

from reportlab.lib import colors

from reportlab.lib.pagesizes import A4

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.lib.units import cm

from io import BytesIO

from ..models import Dette, RemboursementDette, Debiteur

from reportlab.lib.pagesizes import A4

from reportlab.lib.units import cm

from reportlab.lib import colors

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from django.http import HttpResponse

from datetime import datetime

from reportlab.lib.units import cm

from reportlab.lib import colors

from reportlab.lib.pagesizes import A4

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from django.http import HttpResponse

from datetime import datetime

from django.db.models import Sum, Count, Avg

from django.utils import timezone

from datetime import timedelta, datetime

from django.http import JsonResponse

from django.contrib.auth.decorators import login_required

from decimal import Decimal

from .views_exports import export_transactions

@login_required
def gestion_agents(request):
    """
    Page de gestion des agents ET assistants (vue unifiée)
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    # ========== AGENTS ==========
    agents = Agent.objects.all().order_by('-created_at')
    agents_actifs = agents.filter(est_actif=True).count()
    agents_inactifs = agents.filter(est_actif=False).count()
    
    # ========== ASSISTANTS ==========
    assistants = Assistant.objects.filter(admin=admin).order_by('-created_at')
    assistants_actifs = assistants.filter(est_actif=True).count()
    assistants_inactifs = assistants.filter(est_actif=False).count()
    
    demandes_attente = DemandeApprovisionnement.objects.filter(statut='en_attente')
    context = {
        'title': 'Gestion des utilisateurs',
        'agents': agents,
        'agents_actifs': agents_actifs,
        'agents_inactifs': agents_inactifs,
        'assistants': assistants,
        'assistants_actifs': assistants_actifs,
        'assistants_inactifs': assistants_inactifs,
        'demandes_attente': demandes_attente,
    }
    return render(request, 'transactions/gestion_agents.html', context)

@login_required
def ajouter_agent(request):
    """
    Ajouter ou modifier un agent
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')
        nom = request.POST.get('nom')
        telephone = request.POST.get('telephone')
        email = request.POST.get('email')
        est_actif = request.POST.get('est_actif') == 'true'
        password = request.POST.get('password')
        
        if not nom or not telephone:
            messages.error(request, 'Le nom et le téléphone sont obligatoires.')
            return redirect('gestion_agents')
        
        if agent_id:
            # Modification d'un agent existant
            try:
                agent = Agent.objects.get(id=agent_id)
                agent.nom = nom
                agent.telephone = telephone
                agent.email = email
                agent.est_actif = est_actif
                agent.save()
                
                # Mettre à jour l'utilisateur associé
                user = agent.user
                user.email = email
                if password:
                    user.password = make_password(password)
                user.save()
                
                messages.success(request, f'✅ Agent "{nom}" modifié avec succès.')
            except Agent.DoesNotExist:
                messages.error(request, 'Agent non trouvé.')
        else:
            # Création d'un nouvel agent
            if not password:
                messages.error(request, 'Le mot de passe est obligatoire pour un nouvel agent.')
                return redirect('gestion_agents')
            
            # Créer l'utilisateur
            username = telephone
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Créer l'agent
            agent = Agent.objects.create(
                user=user,
                nom=nom,
                telephone=telephone,
                email=email,
                est_actif=est_actif
            )
            
            messages.success(request, f'✅ Agent "{nom}" créé avec succès. Identifiant: {username}')
        
        return redirect('gestion_agents')
    
    return redirect('gestion_agents')

@login_required
def modifier_mot_de_passe_agent(request, user_id):
    if request.method == 'POST':
        nouveau_password = request.POST.get('nouveau_password')
        
        if not nouveau_password or len(nouveau_password) < 4:
            messages.error(request, "Le mot de passe doit contenir au moins 4 caractères")
            return redirect('gestion_agents')
        
        try:
            user = User.objects.get(id=user_id)
            agent = Agent.objects.get(user=user)
            
            # Modifier le mot de passe hashé
            user.password = make_password(nouveau_password)
            user.save()
            
            # Modifier le mot de passe en clair
            agent.mot_de_passe_clair = nouveau_password
            agent.save()
            
            messages.success(request, f"Mot de passe de {agent.nom} modifié avec succès")
            
        except User.DoesNotExist:
            messages.error(request, "Utilisateur introuvable")
        except Agent.DoesNotExist:
            messages.error(request, "Agent introuvable")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
        
        return redirect('gestion_agents')
    
    return redirect('gestion_agents')

@login_required
def modifier_caisse(request):
    """Modifier la caisse d'un agent"""
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')  # ← c'est l'ID de l'agent
        nouveau_cash = request.POST.get('solde_cash')
        nouveau_uv = request.POST.get('solde_uv')
        nouveau_wave = request.POST.get('solde_wave')
        
        if not agent_id:
            messages.error(request, "Agent non spécifié")
            return redirect('gestion_agents')
        
        try:
            # Récupérer L'AGENT (pas l'admin)
            from transactions.models import Agent
            agent = Agent.objects.get(id=agent_id)
            user_agent = agent.user  # ← l'utilisateur agent
            
            # Récupérer la caisse de l'AGENT
            caisse = Caisse.objects.get(user=user_agent)
            
            # Sauvegarder les anciennes valeurs
            ancien_cash = caisse.solde_cash
            ancien_uv = caisse.solde_uv
            ancien_wave = caisse.solde_wave
            
            # Mettre à jour la caisse de l'AGENT
            caisse.solde_cash = Decimal(str(nouveau_cash)) if nouveau_cash else Decimal('0')
            caisse.solde_uv = Decimal(str(nouveau_uv)) if nouveau_uv else Decimal('0')
            caisse.solde_wave = Decimal(str(nouveau_wave)) if nouveau_wave else Decimal('0')
            caisse.save()
            
            messages.success(request, f"Caisse de l'agent {agent.nom} mise à jour avec succès")
            
        except Agent.DoesNotExist:
            messages.error(request, "Agent introuvable")
        except Caisse.DoesNotExist:
            messages.error(request, "Caisse de l'agent introuvable")
        except Exception as e:
            messages.error(request, f"Erreur: {str(e)}")
        
        return redirect('gestion_agents')
    
    return redirect('gestion_agents')

@login_required
def api_agent_caisse(request, agent_id):
    """
    API pour récupérer les soldes de la caisse d'un agent
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Non autorisé'})
    
    try:
        agent = Agent.objects.get(id=agent_id)
        caisse = agent.user.caisse
        
        return JsonResponse({
            'success': True,
            'solde_cash': float(caisse.solde_cash),
            'solde_uv': float(caisse.solde_uv),
            'solde_wave': float(caisse.solde_wave),
        })
    except Agent.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Agent non trouvé'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def supprimer_agent(request):
    """
    Supprimer un agent (désactivation ou suppression définitive)
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')
        action = request.POST.get('action', 'desactiver')
        
        try:
            agent = Agent.objects.get(id=agent_id)
            
            if action == 'supprimer':
                # Suppression définitive
                user = agent.user
                agent.delete()
                user.delete()
                messages.success(request, f'✅ Agent "{agent.nom}" supprimé définitivement.')
            else:
                # Désactivation simple
                agent.est_actif = False
                agent.save()
                messages.success(request, f'✅ Agent "{agent.nom}" désactivé.')
                
        except Agent.DoesNotExist:
            messages.error(request, 'Agent non trouvé.')
    
    return redirect('gestion_agents')

@login_required
def activer_agent(request, agent_id):
    """
    Réactiver un agent désactivé
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    try:
        agent = Agent.objects.get(id=agent_id)
        agent.est_actif = True
        agent.save()
        messages.success(request, f'✅ Agent "{agent.nom}" réactivé avec succès.')
    except Agent.DoesNotExist:
        messages.error(request, 'Agent non trouvé.')
    
    return redirect('gestion_agents')

@login_required
def detail_agent(request, agent_id):
    """
    Page dédiée à un agent avec tous ses détails
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    agent = get_object_or_404(Agent, id=agent_id)
    user = agent.user
    caisse = user.caisse
    
    today = datetime.now().date()
    
    # ========== TRANSACTIONS D'AUJOURD'HUI ==========
    transactions_today = Transaction.objects.filter(user=user, date__date=today)
    
    # Calcul des variations des transactions
    cash_depot_today = transactions_today.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_today = transactions_today.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_transactions = cash_depot_today - cash_retrait_today
    
    uv_depot_today = transactions_today.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_retrait_today = transactions_today.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_credit_today = transactions_today.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='credit'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_uv_transactions = uv_retrait_today - uv_depot_today - uv_credit_today
    
    wave_depot_today = transactions_today.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_today = transactions_today.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_transactions = wave_retrait_today - wave_depot_today
    
    # ========== DEMANDES VALIDÉES D'AUJOURD'HUI ==========
    demandes_validees_today = DemandeApprovisionnement.objects.filter(
        agent=agent,
        statut='valide',
        date_traitement__date=today
    )
    
    # Calcul des variations des demandes
    variation_cash_demandes = 0
    variation_uv_demandes = 0
    variation_wave_demandes = 0
    
    for demande in demandes_validees_today:
        if demande.type_echange == 'uv_to_cash':
            variation_uv_demandes -= demande.montant
            variation_cash_demandes += demande.montant
        elif demande.type_echange == 'wave_to_cash':
            variation_wave_demandes -= demande.montant
            variation_cash_demandes += demande.montant
        elif demande.type_echange == 'cash_to_uv':
            variation_cash_demandes -= demande.montant
            variation_uv_demandes += demande.montant
        elif demande.type_echange == 'cash_to_wave':
            variation_cash_demandes -= demande.montant
            variation_wave_demandes += demande.montant
    
    # ========== VARIATION TOTALE (transactions + demandes) ==========
    variation_cash_today = variation_cash_transactions + variation_cash_demandes
    variation_uv_today = variation_uv_transactions + variation_uv_demandes
    variation_wave_today = variation_wave_transactions + variation_wave_demandes
    
    # ========== SOLDES D'HIER ==========
    if caisse.last_balance_update == today:
        solde_cash_hier = caisse.solde_cash_hier
        solde_uv_hier = caisse.solde_uv_hier
        solde_wave_hier = caisse.solde_wave_hier
    else:
        solde_cash_hier = caisse.solde_cash - variation_cash_today
        solde_uv_hier = caisse.solde_uv - variation_uv_today
        solde_wave_hier = caisse.solde_wave - variation_wave_today
        
        caisse.solde_cash_hier = solde_cash_hier
        caisse.solde_uv_hier = solde_uv_hier
        caisse.solde_wave_hier = solde_wave_hier
        caisse.last_balance_update = today
        caisse.save()
    
    evolution_cash = caisse.solde_cash - solde_cash_hier
    evolution_uv = caisse.solde_uv - solde_uv_hier
    evolution_wave = caisse.solde_wave - solde_wave_hier
    
    # ========== FILTRES TRANSACTIONS ==========
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    type_filtre = request.GET.get('type')
    operateur_filtre = request.GET.get('operateur')
    show_all = request.GET.get('show_all')
    
    # ========== TRANSACTIONS ==========
    transactions = Transaction.objects.filter(user=user).order_by('-date')
    
    if not show_all and not date_debut and not date_fin and not type_filtre and not operateur_filtre:
        transactions = transactions.filter(date__date=today)
    else:
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                transactions = transactions.filter(date__date__gte=date_debut_obj)
            except:
                pass
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                transactions = transactions.filter(date__date__lte=date_fin_obj)
            except:
                pass
        if type_filtre:
            transactions = transactions.filter(type_transaction=type_filtre)
        if operateur_filtre:
            transactions = transactions.filter(operateur=operateur_filtre)
    
    # ========== STATS TRANSACTIONS ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    total_commission = transactions.aggregate(Sum('commission'))['commission__sum'] or 0
    nombre_transactions = transactions.count()
    
    # ========== DEMANDES DE L'AGENT ==========
    show_all_demandes = request.GET.get('show_all_demandes')
    demande_statut = request.GET.get('demande_statut')
    demande_type = request.GET.get('demande_type')
    demande_date_debut = request.GET.get('demande_date_debut')
    demande_date_fin = request.GET.get('demande_date_fin')
    
    # Demandes ENVOYÉES par l'agent
    demandes = DemandeApprovisionnement.objects.filter(agent=agent).order_by('-date_demande')
    
    # Filtres des demandes
    if demande_date_debut:
        try:
            date_debut_obj = datetime.strptime(demande_date_debut, '%Y-%m-%d').date()
            demandes = demandes.filter(date_demande__date__gte=date_debut_obj)
        except:
            pass
    if demande_date_fin:
        try:
            date_fin_obj = datetime.strptime(demande_date_fin, '%Y-%m-%d').date()
            demandes = demandes.filter(date_demande__date__lte=date_fin_obj)
        except:
            pass
    if demande_statut:
        demandes = demandes.filter(statut=demande_statut)
    if demande_type:
        demandes = demandes.filter(type_echange=demande_type)
    
    if not show_all_demandes:
        demandes = demandes.filter(date_demande__date=today)
    
    total_demandes = demandes.count()
    
    # Stats des demandes (toutes, sans filtre pour les stats globales)
    demandes_all = DemandeApprovisionnement.objects.filter(agent=agent)
    demande_stats = {
        'attente': demandes_all.filter(statut='en_attente').count(),
        'valide': demandes_all.filter(statut='valide').count(),
        'refuse': demandes_all.filter(statut='refuse').count(),
        'total': demandes_all.count(),
    }
    
    # ========== EXPORT ==========
    export_format = request.GET.get('export')
    if export_format in ['csv', 'excel']:
        return export_transactions(transactions, agent, caisse, total_entree, total_sortie, total_commission, demandes, export_format)
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions, 15)
    transactions_page = paginator.get_page(page)
    
    context = {
        'title': f'Agent - {agent.nom}',
        'agent': agent,
        'caisse': caisse,
        'transactions': transactions_page,
        'total_entree': total_entree,
        'total_sortie': total_sortie,
        'total_commission': total_commission,
        'nombre_transactions': nombre_transactions,
        'demandes': demandes[:20],  # Limite à 20 pour l'affichage
        'demande_stats': demande_stats,
        'total_demandes': total_demandes,
        'solde_cash_hier': solde_cash_hier,
        'solde_uv_hier': solde_uv_hier,
        'solde_wave_hier': solde_wave_hier,
        'evolution_cash': evolution_cash,
        'evolution_uv': evolution_uv,
        'evolution_wave': evolution_wave,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'type_filtre': type_filtre,
        'operateur_filtre': operateur_filtre,
        'show_all': show_all,
        'show_all_demandes': show_all_demandes,
        'demande_statut': demande_statut,
        'demande_type': demande_type,
        'demande_date_debut': demande_date_debut,
        'demande_date_fin': demande_date_fin,
    }
    return render(request, 'transactions/detail_agent.html', context)

@login_required
def api_user_password(request, user_id):
    """API pour récupérer le mot de passe d'un utilisateur"""
    try:
        user = User.objects.get(id=user_id)
        
        # Essayer de récupérer depuis Agent
        try:
            agent = Agent.objects.get(user=user)
            if agent.mot_de_passe_clair:
                return JsonResponse({
                    'success': True,
                    'password': agent.mot_de_passe_clair
                })
        except Agent.DoesNotExist:
            pass
        
        # Essayer de récupérer depuis Assistant
        try:
            assistant = Assistant.objects.get(user=user)
            if assistant.mot_de_passe_clair:
                return JsonResponse({
                    'success': True,
                    'password': assistant.mot_de_passe_clair
                })
        except Assistant.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'password': 'Mot de passe non stocké en clair'
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'password': 'Utilisateur introuvable'
        })
