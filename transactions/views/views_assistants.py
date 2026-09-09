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
def api_assistant_infos(request, assistant_id):
    """API pour récupérer les informations d'un assistant"""
    from transactions.models import Assistant
    
    try:
        assistant = Assistant.objects.get(id=assistant_id)
        return JsonResponse({
            'success': True,
            'username': assistant.user.username if assistant.user else ''
        })
    except Assistant.DoesNotExist:
        return JsonResponse({
            'success': False,
            'username': ''
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'username': '',
            'error': str(e)
        })

@login_required
def gestion_assistants(request):
    """Page de gestion des assistants"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistants = Assistant.objects.filter(admin=admin).order_by('-created_at')
    assistants_actifs = assistants.filter(est_actif=True).count()
    assistants_inactifs = assistants.filter(est_actif=False).count()
    
    context = {
        'title': 'Gestion des assistants',
        'assistants': assistants,
        'assistants_actifs': assistants_actifs,
        'assistants_inactifs': assistants_inactifs,
    }
    return render(request, 'transactions/gestion_assistants.html', context)

@login_required
def ajouter_assistant(request):
    """Ajouter un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    if request.method == 'POST':
        assistant_id = request.POST.get('assistant_id')
        nom = request.POST.get('nom')
        telephone = request.POST.get('telephone')
        email = request.POST.get('email', '')
        username = request.POST.get('username')
        password = request.POST.get('password')
        est_actif = request.POST.get('est_actif') == 'true'
        agent_id = request.POST.get('agent_id', '')
        
        if not nom or not telephone:
            messages.error(request, 'Le nom et le téléphone sont obligatoires.')
            return redirect('gestion_agents')  # ← Redirige vers gestion_agents
        
        if agent_id:
            try:
                agent_lie = Agent.objects.get(id=agent_id)
            except (Agent.DoesNotExist, ValueError, TypeError):
                messages.error(request, 'Agent introuvable.')
                return redirect('gestion_agents')
        else:
            agent_lie = None
        
        if assistant_id:
            # ===== Modification d'un assistant existant =====
            try:
                assistant = Assistant.objects.get(id=assistant_id, admin=admin)
            except Assistant.DoesNotExist:
                messages.error(request, 'Assistant non trouvé.')
                return redirect('gestion_agents')
            
            assistant.nom = nom
            assistant.telephone = telephone
            assistant.email = email
            assistant.est_actif = est_actif
            assistant.agent = agent_lie
            assistant.save()
            
            # Identifiant et mot de passe mis à jour si fournis
            user = assistant.user
            if username and username != user.username:
                if User.objects.filter(username=username).exclude(id=user.id).exists():
                    messages.error(request, f"Le nom d'utilisateur '{username}' existe déjà.")
                    return redirect('gestion_agents')
                user.username = username
            if password:
                user.set_password(password)
            user.email = email
            user.save()
            
            messages.success(request, f'✅ Assistant "{nom}" modifié avec succès. Identifiant: {user.username}')
            return redirect('gestion_agents')
        
        # ===== Création d'un nouvel assistant =====
        if not username or not password:
            messages.error(request, 'Le nom, le téléphone, l\'identifiant et le mot de passe sont obligatoires.')
            return redirect('gestion_agents')  # ← Redirige vers gestion_agents
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Le nom d'utilisateur '{username}' existe déjà.")
            return redirect('gestion_agents')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        assistant = Assistant.objects.create(
            user=user,
            nom=nom,
            telephone=telephone,
            email=email,
            admin=admin,
            agent=agent_lie,
            est_actif=est_actif,
            created_by=admin
        )
        
        messages.success(request, f'✅ Assistant "{nom}" créé avec succès. Identifiant: {username}')
        return redirect('gestion_agents')
    
    return redirect('gestion_agents')

@login_required
def toggle_assistant_status(request, assistant_id):
    """Activer/Désactiver un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    assistant.est_actif = not assistant.est_actif
    assistant.save()
    
    status = "activé" if assistant.est_actif else "désactivé"
    messages.success(request, f'✅ Assistant "{assistant.nom}" {status}.')
    return redirect('gestion_assistants')

@login_required
def modifier_assistant(request, assistant_id):
    """Modifier un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    
    if request.method == 'POST':
        assistant.nom = request.POST.get('nom', assistant.nom)
        assistant.telephone = request.POST.get('telephone', assistant.telephone)
        assistant.email = request.POST.get('email', assistant.email)
        assistant.est_actif = request.POST.get('est_actif') == 'true'
        assistant.save()
        
        messages.success(request, f'✅ Assistant "{assistant.nom}" modifié avec succès.')
        return redirect('gestion_assistants')
    
    return redirect('gestion_assistants')

@login_required
def activer_assistant(request, assistant_id):
    """Activer/Désactiver un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    assistant.est_actif = not assistant.est_actif
    assistant.save()
    
    status = "activé" if assistant.est_actif else "désactivé"
    messages.success(request, f'✅ Assistant "{assistant.nom}" {status}.')
    return redirect('gestion_assistants')

@login_required
def supprimer_assistant(request, assistant_id):
    """Supprimer un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    nom = assistant.nom
    user = assistant.user
    
    assistant.delete()
    user.delete()
    
    messages.success(request, f'✅ Assistant "{nom}" supprimé définitivement.')
    return redirect('gestion_assistants')

@login_required
def detail_assistant(request, assistant_id):
    """Page dédiée à un assistant avec ses demandes reçues"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    caisse = assistant.get_caisse  # Caisse partagée (admin ou agent)
    
    today = datetime.now().date()
    
    # ========== TRANSACTIONS DE L'ASSISTANT ==========
    transactions = Transaction.objects.filter(user=assistant.user).order_by('-date')
    
    # ========== TRANSACTIONS D'AUJOURD'HUI ==========
    transactions_today = transactions.filter(date__date=today)
    
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
    
    # ========== DEMANDES VALIDÉES PAR L'ASSISTANT AUJOURD'HUI ==========
    demandes_validees_today = DemandeApprovisionnement.objects.filter(
        destinataire_type='assistant',
        assistant_destinataire=assistant,
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
    
    # ========== DEMANDES REÇUES PAR L'ASSISTANT ==========
    show_all_demandes = request.GET.get('show_all_demandes')
    demande_statut = request.GET.get('demande_statut')
    demande_type = request.GET.get('demande_type')
    demande_date_debut = request.GET.get('demande_date_debut')
    demande_date_fin = request.GET.get('demande_date_fin')
    
    # Demandes REÇUES par l'assistant
    demandes = DemandeApprovisionnement.objects.filter(
        destinataire_type='assistant',
        assistant_destinataire=assistant
    ).order_by('-date_demande')
    
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
    demandes_all = DemandeApprovisionnement.objects.filter(
        destinataire_type='assistant',
        assistant_destinataire=assistant
    )
    demande_stats = {
        'attente': demandes_all.filter(statut='en_attente').count(),
        'valide': demandes_all.filter(statut='valide').count(),
        'refuse': demandes_all.filter(statut='refuse').count(),
        'total': demandes_all.count(),
        'montant_total': demandes_all.aggregate(Sum('montant'))['montant__sum'] or 0,
    }
    
    # ========== EXPORT ==========
    export_format = request.GET.get('export')
    if export_format in ['csv', 'excel']:
        return export_transactions(transactions, assistant, caisse, total_entree, total_sortie, total_commission, demandes, export_format)
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions, 15)
    transactions_page = paginator.get_page(page)
    
    context = {
        'title': f'Assistant - {assistant.nom}',
        'assistant': assistant,
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
    return render(request, 'transactions/detail_assistant.html', context)

@login_required
def modifier_mot_de_passe_assistant(request, assistant_id):
    """Modifier le mot de passe d'un assistant"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    assistant = get_object_or_404(Assistant, id=assistant_id, admin=admin)
    
    if request.method == 'POST':
        nouveau_password = request.POST.get('nouveau_password')
        
        if not nouveau_password or len(nouveau_password) < 4:
            messages.error(request, 'Le mot de passe doit contenir au moins 4 caractères.')
            return redirect('gestion_assistants')
        
        assistant.user.set_password(nouveau_password)
        assistant.user.save()
        
        messages.success(request, f'✅ Mot de passe modifié pour "{assistant.nom}".')
        return redirect('gestion_assistants')
    
    return redirect('gestion_assistants')
