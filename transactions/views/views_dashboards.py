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

def dashboard_redirect(request):
    """
    Redirige vers le bon tableau de bord selon le rôle
    """
    # Vérifier si l'utilisateur est un ADMIN
    try:
        admin = Admin.objects.get(user=request.user)
        return redirect('dashboard_admin')
    except Admin.DoesNotExist:
        pass
    
    # Vérifier si l'utilisateur est un AGENT
    try:
        agent = Agent.objects.get(user=request.user)
        return redirect('dashboard_agent')
    except Agent.DoesNotExist:
        pass
    
    # Vérifier si l'utilisateur est un ASSISTANT
    try:
        assistant = Assistant.objects.get(user=request.user)
        return redirect('dashboard_assistant')
    except Assistant.DoesNotExist:
        pass
    
    # Sinon, rediriger vers login
    messages.error(request, 'Vous n\'avez pas de profil configuré.')
    return redirect('login')

def dashboard_admin(request):
    """
    Tableau de bord pour l'ADMIN
    - Voit son propre compte
    - Voit tous les agents
    - Voit les demandes en attente
    - Statistiques du jour et d'hier
    - Top agents
    """
    try:
        admin = Admin.objects.get(user=request.user)
        caisse_admin = admin.user.caisse
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # ========== AGENTS ET ASSISTANTS ==========
        agents = Agent.objects.filter(est_actif=True)
        assistants = Assistant.objects.filter(est_actif=True)
        total_agents = agents.count()
        total_assistants = assistants.count()
        
        # ========== TRANSACTIONS ==========
        transactions_today = Transaction.objects.filter(date__date=today)
        transactions_yesterday = Transaction.objects.filter(date__date=yesterday)
        
        # Stats du jour
        stats_today = {
            'depots': transactions_today.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0,
            'retraits': transactions_today.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
            'credits': transactions_today.filter(type_transaction='credit').aggregate(Sum('montant'))['montant__sum'] or 0,
            'commission': transactions_today.aggregate(Sum('commission'))['commission__sum'] or 0,
            'nombre': transactions_today.count(),
        }
        
        # Stats d'hier
        stats_yesterday = {
            'depots': transactions_yesterday.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0,
            'retraits': transactions_yesterday.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
            'credits': transactions_yesterday.filter(type_transaction='credit').aggregate(Sum('montant'))['montant__sum'] or 0,
            'commission': transactions_yesterday.aggregate(Sum('commission'))['commission__sum'] or 0,
            'nombre': transactions_yesterday.count(),
        }
        
        # Évolutions
        evolution = {
            'depots': ((stats_today['depots'] - stats_yesterday['depots']) / stats_yesterday['depots'] * 100) if stats_yesterday['depots'] > 0 else 0,
            'retraits': ((stats_today['retraits'] - stats_yesterday['retraits']) / stats_yesterday['retraits'] * 100) if stats_yesterday['retraits'] > 0 else 0,
            'credits': ((stats_today['credits'] - stats_yesterday['credits']) / stats_yesterday['credits'] * 100) if stats_yesterday['credits'] > 0 else 0,
            'commission': ((stats_today['commission'] - stats_yesterday['commission']) / stats_yesterday['commission'] * 100) if stats_yesterday['commission'] > 0 else 0,
            'nombre': ((stats_today['nombre'] - stats_yesterday['nombre']) / stats_yesterday['nombre'] * 100) if stats_yesterday['nombre'] > 0 else 0,
        }
        
        # ========== DEMANDES ==========
        demandes_attente = DemandeApprovisionnement.objects.filter(
            statut='en_attente'
        ).order_by('-date_demande')
        
        demandes_today = DemandeApprovisionnement.objects.filter(date_demande__date=today)
        demandes_yesterday = DemandeApprovisionnement.objects.filter(date_demande__date=yesterday)
        
        demandes_stats = {
            'aujourdhui': demandes_today.count(),
            'hier': demandes_yesterday.count(),
            'total_attente': demandes_attente.count(),
            'total_validees': DemandeApprovisionnement.objects.filter(statut='valide').count(),
            'total_refusees': DemandeApprovisionnement.objects.filter(statut='refuse').count(),
        }
        
        # ========== NOUVEAUX AGENTS ==========
        nouveaux_agents_today = Agent.objects.filter(created_at__date=today).count()
        nouveaux_agents_yesterday = Agent.objects.filter(created_at__date=yesterday).count()
        
        # ========== STATISTIQUES PAR OPÉRATEUR ==========
        stats_par_operateur = {}
        for operateur in ['orange', 'wave', 'malitel', 'telecel']:
            ops = transactions_today.filter(operateur=operateur)
            stats_par_operateur[operateur] = {
                'nombre': ops.count(),
                'montant': ops.aggregate(Sum('montant'))['montant__sum'] or 0,
            }
        
        # ========== STATISTIQUES PAR AGENT ==========
        stats_par_agent = []
        for agent in agents:
            transactions_agent = Transaction.objects.filter(
                user=agent.user,
                date__date=today
            )
            stats_par_agent.append({
                'agent': agent,
                'caisse': agent.user.caisse,
                'nombre': transactions_agent.count(),
                'montant': transactions_agent.aggregate(Sum('montant'))['montant__sum'] or 0,
            })
        
        # ========== TOP AGENTS ==========
        top_agents = []
        for agent in agents:
            nb_trans = Transaction.objects.filter(user=agent.user, date__date=today).count()
            if nb_trans > 0:
                top_agents.append({
                    'agent': agent,
                    'transactions': nb_trans,
                    'montant': Transaction.objects.filter(user=agent.user, date__date=today).aggregate(Sum('montant'))['montant__sum'] or 0,
                })
        top_agents = sorted(top_agents, key=lambda x: x['transactions'], reverse=True)[:5]
        
        # ========== TRANSACTIONS ADMIN ==========
        transactions_admin = Transaction.objects.filter(
            user=request.user,
            date__date=today
        )
        
        stats_admin = {
            'depots': transactions_admin.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0,
            'retraits': transactions_admin.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
            'credits': transactions_admin.filter(type_transaction='credit').aggregate(Sum('montant'))['montant__sum'] or 0,
            'commission': transactions_admin.aggregate(Sum('commission'))['commission__sum'] or 0,
            'nombre': transactions_admin.count(),
        }
        
        # ========== DERNIÈRES TRANSACTIONS ==========
        dernieres_transactions = Transaction.objects.all().order_by('-date')[:30]
        
        # ========== TOTAL COMMISSION ==========
        total_commission = Transaction.objects.aggregate(Sum('commission'))['commission__sum'] or 0
        
        context = {
            'title': 'Tableau de bord - ADMIN',
            'admin': admin,
            'caisse': caisse_admin,
            'agents': agents,
            'assistants': assistants,
            'total_agents': total_agents,
            'total_assistants': total_assistants,
            'stats_today': stats_today,
            'stats_yesterday': stats_yesterday,
            'evolution': evolution,
            'demandes_attente': demandes_attente,
            'demandes_stats': demandes_stats,
            'nouveaux_agents_today': nouveaux_agents_today,
            'nouveaux_agents_yesterday': nouveaux_agents_yesterday,
            'stats_par_operateur': stats_par_operateur,
            'stats_par_agent': stats_par_agent,
            'top_agents': top_agents,
            'stats_admin': stats_admin,
            'dernieres_transactions': dernieres_transactions,
            'total_commission': total_commission,
            'transactions_jour': transactions_today,
        }
        return render(request, 'transactions/dashboard_admin.html', context)
        
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas configuré comme administrateur.')
        return redirect('login')

def dashboard_agent(request):
    """
    Tableau de bord pour l'AGENT
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
        
        # Vérifier si l'agent a une caisse
        if not caisse:
            messages.error(request, 'Votre caisse n\'est pas configurée.')
            return redirect('login')
        
        # ========== RÉCUPÉRER LES ASSISTANTS ==========
        assistants = Assistant.objects.filter(est_actif=True)
        
        # Transactions du jour
        today = datetime.now().date()
        transactions_jour = Transaction.objects.filter(
            user=request.user,
            date__date=today
        )
        
        # Statistiques du jour
        stats_jour = {
            'depots': transactions_jour.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0,
            'retraits': transactions_jour.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
            'credits': transactions_jour.filter(type_transaction='credit').aggregate(Sum('montant'))['montant__sum'] or 0,
            'commission': transactions_jour.aggregate(Sum('commission'))['commission__sum'] or 0,
            'nombre': transactions_jour.count(),
        }
        
        # Statistiques par opérateur
        stats_par_operateur = {}
        for operateur in ['orange', 'wave', 'malitel', 'telecel']:
            ops = transactions_jour.filter(operateur=operateur)
            stats_par_operateur[operateur] = {
                'nombre': ops.count(),
                'montant': ops.aggregate(Sum('montant'))['montant__sum'] or 0,
            }
        
        # Dernières transactions
        dernieres_transactions = Transaction.objects.filter(
            user=request.user
        ).order_by('-date')[:20]
        
        # Demandes en cours
        demandes_en_cours = DemandeApprovisionnement.objects.filter(
            agent=agent,
            statut='en_attente'
        )
        
        # Historique des demandes
        historique_demandes = DemandeApprovisionnement.objects.filter(
            agent=agent
        ).order_by('-date_demande')[:10]
        
        context = {
            'title': 'Tableau de bord - Agent',
            'agent': agent,
            'caisse': caisse,
            'assistants': assistants,  # ← TRÈS IMPORTANT : AJOUTER CETTE LIGNE
            'stats_jour': stats_jour,
            'stats_par_operateur': stats_par_operateur,
            'transactions_jour': transactions_jour[:20],
            'dernieres_transactions': dernieres_transactions,
            'demandes_en_cours': demandes_en_cours,
            'historique_demandes': historique_demandes,
        }
        return render(request, 'transactions/dashboard_agent.html', context)
        
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas configuré comme agent.')
        return redirect('login')

def dashboard_assistant(request):
    """
    Tableau de bord pour l'ASSISTANT
    - Partage la caisse de l'admin
    - Voit les demandes d'approvisionnement des agents qui lui sont destinées
    - Peut faire des transactions (dépôt, retrait, crédit)
    """
    try:
        assistant = Assistant.objects.get(user=request.user)
    except Assistant.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas configuré comme assistant.')
        return redirect('login')
    
    # L'assistant partage la caisse de son admin
    caisse = assistant.admin.user.caisse
    
    today = datetime.now().date()
    
    # Transactions du jour
    transactions_jour = Transaction.objects.filter(
        user=request.user,
        date__date=today
    )
    
    # Statistiques du jour
    stats_jour = {
        'depots': transactions_jour.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0,
        'retraits': transactions_jour.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
        'credits': transactions_jour.filter(type_transaction='credit').aggregate(Sum('montant'))['montant__sum'] or 0,
        'commission': transactions_jour.aggregate(Sum('commission'))['commission__sum'] or 0,
        'nombre': transactions_jour.count(),
    }
    
    # Dernières transactions
    dernieres_transactions = Transaction.objects.filter(
        user=request.user
    ).order_by('-date')[:20]
    
    # ========== DEMANDES REÇUES DES AGENTS ==========
    # L'assistant reçoit les demandes des agents qui l'ont choisi comme destinataire
    demandes_recues = DemandeApprovisionnement.objects.filter(
        destinataire_type='assistant',
        assistant_destinataire=assistant
    ).order_by('-date_demande')
    
    # Statistiques des demandes
    demandes_stats = {
        'en_attente': demandes_recues.filter(statut='en_attente').count(),
        'validees': demandes_recues.filter(statut='valide').count(),
        'refusees': demandes_recues.filter(statut='refuse').count(),
    }
    
    context = {
        'title': 'Tableau de bord - Assistant',
        'assistant': assistant,
        'caisse': caisse,
        'stats_jour': stats_jour,
        'transactions_jour': transactions_jour[:20],
        'dernieres_transactions': dernieres_transactions,
        'demandes_recues': demandes_recues[:10],
        'demandes_stats': demandes_stats,
    }
    return render(request, 'transactions/dashboard_assistant.html', context)
