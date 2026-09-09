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

@login_required
def transaction_user(request, operateur, type_transaction):
    """
    Transaction pour l'utilisateur connecté (ADMIN, AGENT ou ASSISTANT)
    - ADMIN: utilise sa propre caisse
    - AGENT: utilise sa propre caisse
    - ASSISTANT: utilise la caisse de son ADMIN (impacte le solde admin)
    Vérifie les soldes avant d'effectuer la transaction
    Supporte les requêtes AJAX pour le modal de confirmation
    """
    # Vérifier le rôle
    is_admin = hasattr(request.user, 'admin_profile')
    is_agent = hasattr(request.user, 'agent_profile')
    is_assistant = hasattr(request.user, 'assistant_profile')
    
    if not (is_admin or is_agent or is_assistant):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas configuré.'})
        messages.error(request, 'Vous n\'êtes pas configuré.')
        return redirect('login')
    
    # Récupérer la caisse
    # - ADMIN: sa propre caisse
    # - AGENT: sa propre caisse
    # - ASSISTANT: la caisse de son ADMIN (impacte le solde admin)
    if is_assistant:
        assistant = request.user.assistant_profile
        caisse = assistant.get_caisse
    else:
        caisse = request.user.caisse  # ← Propre caisse
    
    # Déterminer le formulaire
    forms = {
        'orange': OrangeTransactionForm,
        'wave': WaveTransactionForm,
        'malitel': MalitelTransactionForm,
        'telecel': TelecelTransactionForm,
    }
    
    form_class = forms.get(operateur)
    if not form_class:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Opérateur invalide.'})
        messages.error(request, 'Opérateur invalide.')
        return redirect('dashboard_redirect')
    
    # Vérifier si l'opération est disponible pour cet opérateur
    if operateur == 'wave' and type_transaction == 'credit':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Le crédit Wave n\'est pas disponible'})
        messages.error(request, '❌ Le crédit Wave n\'est pas disponible')
        return redirect('dashboard_redirect')
    
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            montant = form.cleaned_data['montant']

            from django.db import transaction as db_transaction
            with db_transaction.atomic():
                # Verrouiller la ligne caisse : élimine les courses sur les soldes
                caisse = Caisse.objects.select_for_update().get(pk=caisse.pk)

                # ========== VÉRIFICATIONS DES SOLDES ==========
                solde_ok = True
                message_erreur = ""
                
                # ORANGE, MALITEL, TELECEL (via UV Touspiont)
                if operateur in ['orange', 'malitel', 'telecel']:
                    if type_transaction == 'depot':
                        # DÉPÔT: client donne cash → agent donne ses UV (il faut assez d'UV)
                        if caisse.solde_uv < montant:
                            solde_ok = False
                            message_erreur = f"❌ Solde UV Touspiont insuffisant. Solde actuel: {caisse.solde_uv:,.0f} FCFA"
                        
                    elif type_transaction == 'retrait':
                        # RETRAIT: client prend cash → agent donne son cash (il faut assez de cash)
                        if caisse.solde_cash < montant:
                            solde_ok = False
                            message_erreur = f"❌ Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"
                        
                    elif type_transaction == 'credit':
                        # CRÉDIT: client recharge → agent donne ses UV (il faut assez d'UV)
                        if caisse.solde_uv < montant:
                            solde_ok = False
                            message_erreur = f"❌ Solde UV Touspiont insuffisant pour le crédit. Solde actuel: {caisse.solde_uv:,.0f} FCFA"
                
                # WAVE
                elif operateur == 'wave':
                    if type_transaction == 'depot':
                        # DÉPÔT WAVE: client donne cash → agent donne ses Wave (il faut assez de Wave)
                        if caisse.solde_wave < montant:
                            solde_ok = False
                            message_erreur = f"❌ Solde Wave insuffisant. Solde actuel: {caisse.solde_wave:,.0f} FCFA"
                        
                    elif type_transaction == 'retrait':
                        # RETRAIT WAVE: client prend cash → agent donne son cash (il faut assez de cash)
                        if caisse.solde_cash < montant:
                            solde_ok = False
                            message_erreur = f"❌ Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"
                
                # Si solde insuffisant
                if not solde_ok:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': message_erreur})
                    messages.error(request, message_erreur)
                    return redirect('dashboard_redirect')
                
                # Déterminer le rôle et l'admin associé
                if is_admin:
                    role = 'admin'
                    assistant_admin = None
                elif is_agent:
                    role = 'agent'
                    assistant_admin = None
                else:
                    role = 'assistant'
                    assistant_admin = request.user.assistant_profile.admin
                
                # Créer et sauvegarder la transaction
                transaction = form.save(commit=False)
                transaction.user = request.user
                transaction.type_transaction = type_transaction
                transaction.operateur = operateur
                transaction.role = role
                transaction.assistant_admin = assistant_admin
                
                try:
                    transaction.save()  # ← Ici la logique du modèle Transaction met à jour la caisse
                    
                    # Réponse JSON pour AJAX
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'reference': transaction.reference,
                            'message': f'Transaction {operateur.capitalize()} effectuée avec succès!'
                        })
                    
                    messages.success(request, f'✅ Transaction {operateur.capitalize()} effectuée avec succès! Réf: {transaction.reference}')
                    
                    # Redirection selon le rôle
                    if is_admin:
                        return redirect('dashboard_admin')
                    elif is_agent:
                        return redirect('dashboard_agent')
                    else:
                        return redirect('dashboard_assistant')
                        
                except Exception as e:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': False, 'error': str(e)})
                    messages.error(request, f'Erreur: {str(e)}')
        else:
            # Erreurs du formulaire
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': list(form.errors.values())[0][0]})
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = form_class(initial={'type_transaction': type_transaction})
    
    # Déterminer l'URL de redirection pour le formulaire
    if is_admin:
        dashboard_url = 'dashboard_admin'
    elif is_agent:
        dashboard_url = 'dashboard_agent'
    else:
        dashboard_url = 'dashboard_assistant'
    
    context = {
        'title': f'{operateur.capitalize()} - {type_transaction.capitalize()}',
        'form': form,
        'type_transaction': type_transaction,
        'operateur': operateur,
        'is_admin': is_admin,
        'is_agent': is_agent,
        'is_assistant': is_assistant,
        'caisse': caisse,
        'dashboard_url': dashboard_url,
    }
    return render(request, 'transactions/transaction_form.html', context)

@login_required
def impression_recu(request, transaction_id):
    """
    Vue pour l'impression des reçus
    Envoie uniquement les données brutes, le JS fait le formatage
    """
    transaction = get_object_or_404(Transaction, reference=transaction_id)
    
    # Déterminer le rôle de l'utilisateur
    user_role = "Admin"
    if hasattr(transaction.user, 'agent'):
        user_role = "Agent"
    elif hasattr(transaction.user, 'assistant'):
        user_role = "Assistant"
    elif transaction.user.is_superuser or transaction.user.is_staff:
        user_role = "Admin"
    
    # Données brutes (sans formatage)
    data = {
        "operateur": transaction.user.username if transaction.user else "-",
        "role_operateur": user_role,
        "type": transaction.type_transaction if transaction.type_transaction else "-",
        "operateur_money": transaction.get_operateur_display() if transaction.operateur else "-",
        "client": transaction.numero_client if transaction.numero_client else "-",
        "nom_client": transaction.nom_client if transaction.nom_client else "-",
        "montant": int(transaction.montant) if transaction.montant else 0,
        "reference": transaction.reference if transaction.reference else "-",
        "date": transaction.date.strftime('%d/%m/%Y') if transaction.date else "-",
        "heure": transaction.date.strftime('%H:%M:%S') if transaction.date else "-",
    }
    
    # Retourner les données en JSON pour QZ Tray
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse(data)
    
    # Pour l'impression navigateur (fallback)
    context = {
        'transaction': transaction,
        'data': data,
        'user_role': user_role,
        'entreprise': {
            'nom': 'KONE SERVICES',
            'telephone': '76 89 77 31',
            'adresse': 'Services Transfert'
        }
    }
    return render(request, 'transactions/recu.html', context)

@login_required
def historique_admin(request):
    """
    Historique des transactions pour l'ADMIN (toutes)
    Supporte l'AJAX pour le chargement dynamique
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    # ========== FILTRES ==========
    type_filtre = request.GET.get('type')
    operateur_filtre = request.GET.get('operateur')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    user_id = request.GET.get('user_id')
    
    transactions = Transaction.objects.all()
    
    # Filtre par utilisateur (par ID)
    if user_id:
        transactions = transactions.filter(user_id=user_id)
    
    if type_filtre:
        transactions = transactions.filter(type_transaction=type_filtre)
    if operateur_filtre:
        transactions = transactions.filter(operateur=operateur_filtre)
    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            transactions = transactions.filter(date__date__gte=date_debut_obj)
        except ValueError:
            pass
    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            transactions = transactions.filter(date__date__lte=date_fin_obj)
        except ValueError:
            pass
    
    # ========== TOTAUX (avant pagination) ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    total_commission = transactions.aggregate(Sum('commission'))['commission__sum'] or 0
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions.order_by('-date'), 10)
    
    try:
        transactions_page = paginator.page(page)
    except:
        transactions_page = paginator.page(1)
    
    # ========== DÉTECTION AJAX ==========
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        transactions_data = []
        for t in transactions_page:
            if hasattr(t.user, 'admin_profile'):
                user_type = 'admin'
                user_name = t.user.admin_profile.nom
            elif hasattr(t.user, 'agent_profile'):
                user_type = 'agent'
                user_name = t.user.agent_profile.nom
            elif hasattr(t.user, 'assistant_profile'):
                user_type = 'assistant'
                user_name = t.user.assistant_profile.nom
            else:
                user_type = 'unknown'
                user_name = t.user.username
            
            transactions_data.append({
                'reference': t.reference,
                'user_type': user_type,
                'user_name': user_name,
                'type': t.type_transaction,
                'operateur': t.operateur,
                'operateur_label': t.get_operateur_display(),
                'numero_client': t.numero_client,
                'montant': float(t.montant),
                'commission': float(t.commission),
                'date': t.date.strftime('%d/%m/%Y %H:%M'),
                'est_annule': t.est_annule,
            })
        
        current = transactions_page.number
        total_pages = paginator.num_pages
        start_page = max(1, current - 2)
        end_page = min(total_pages, current + 2)
        
        return JsonResponse({
            'success': True,
            'transactions': transactions_data,
            'stats': {
                'count': transactions.count(),
                'total_entree': float(total_entree),
                'total_sortie': float(total_sortie),
                'total_commission': float(total_commission),
            },
            'pagination': {
                'current_page': current,
                'total_pages': total_pages,
                'has_next': transactions_page.has_next(),
                'has_previous': transactions_page.has_previous(),
                'next_page': transactions_page.next_page_number() if transactions_page.has_next() else None,
                'previous_page': transactions_page.previous_page_number() if transactions_page.has_previous() else None,
                'start_page': start_page,
                'end_page': end_page,
            }
        })
    
    # ========== RENDU NORMAL ==========
    admins = Admin.objects.all()
    agents = Agent.objects.filter(est_actif=True)
    assistants = Assistant.objects.filter(est_actif=True)
    
    demandes_attente = DemandeApprovisionnement.objects.filter(statut='en_attente')
    context = {
        'title': 'Historique des transactions',
        'transactions': transactions_page,
        'total_entree': total_entree,
        'total_sortie': total_sortie,
        'total_commission': total_commission,
        'admins': admins,
        'agents': agents,
        'assistants': assistants,
        'demandes_attente': demandes_attente,
    }
    return render(request, 'transactions/historique_admin.html', context)

@login_required
@login_required
def historique_agent(request):
    """
    Historique des transactions pour l'AGENT ou ASSISTANT (ses propres transactions)
    Avec filtres par date, opérateur et type
    Affiche par défaut les transactions du jour
    """
    # Vérifier si c'est un agent ou un assistant
    try:
        agent = Agent.objects.get(user=request.user)
        is_agent = True
    except Agent.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
            is_agent = False
            agent = assistant  # Pour garder la compatibilité avec le template
        except Assistant.DoesNotExist:
            messages.error(request, 'Vous n\'êtes pas autorisé.')
            return redirect('login')
    
    # ========== TRANSACTIONS DE L'UTILISATEUR ==========
    # Pour l'AGENT : ses propres transactions + celles de SES ASSISTANTS
    # (toutes touchent sa caisse). Pour l'ASSISTANT : uniquement les siennes.
    fait_par = {}
    if is_agent:
        assistants = Assistant.objects.filter(agent=agent).select_related('user')
        user_ids = [agent.user_id] + [a.user_id for a in assistants]
        transactions = Transaction.objects.filter(user_id__in=user_ids).order_by('-date')
        fait_par[agent.user_id] = f"Agent {agent.nom}"
        for a in assistants:
            fait_par[a.user_id] = f"Assistant {a.nom}"
    else:
        transactions = Transaction.objects.filter(user=request.user).order_by('-date')
        fait_par[request.user.id] = "Moi"
    
    # ========== ENVOIS & RETRAITS (ApprovisionnementDirect) ==========
    # L'agent voit tous les envois/retraits le concernant ;
    # l'assistant voit ceux de son agent ou ceux qu'il a effectués.
    if is_agent:
        er_operations = ApprovisionnementDirect.objects.filter(agent_destinataire=agent)
    elif assistant.agent_id:
        er_operations = ApprovisionnementDirect.objects.filter(
            Q(agent_destinataire_id=assistant.agent_id) | Q(assistant_source_id=assistant.id)
        )
    else:
        er_operations = ApprovisionnementDirect.objects.filter(
            Q(admin_source_id=assistant.admin_id) | Q(assistant_source_id=assistant.id)
        )
    
    # Date d'aujourd'hui avec timezone
    today = timezone.now().date()
    
    # ========== FILTRES ==========
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    operateur = request.GET.get('operateur')
    type_transaction = request.GET.get('type')
    
    # Si aucun filtre de date n'est appliqué, afficher uniquement les transactions du jour
    if not date_debut and not date_fin:
        transactions = transactions.filter(date__date=today)
        date_debut_display = today.strftime('%Y-%m-%d')
        date_fin_display = today.strftime('%Y-%m-%d')
    else:
        date_debut_display = date_debut
        date_fin_display = date_fin
        
        # Filtre par date début
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                transactions = transactions.filter(date__date__gte=date_debut_obj)
            except ValueError:
                pass
        
        # Filtre par date fin
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                transactions = transactions.filter(date__date__lte=date_fin_obj)
            except ValueError:
                pass
    
    # Filtre par opérateur
    if operateur:
        transactions = transactions.filter(operateur=operateur)
    
    # Filtre par type
    if type_transaction:
        transactions = transactions.filter(type_transaction=type_transaction)
    
    # ========== FILTRES APPLIQUÉS AUX ENVOIS & RETRAITS ==========
    if not date_debut and not date_fin:
        er_operations = er_operations.filter(date__date=today)
    else:
        if date_debut:
            try:
                date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
                er_operations = er_operations.filter(date__date__gte=date_debut_obj)
            except ValueError:
                pass
        if date_fin:
            try:
                date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
                er_operations = er_operations.filter(date__date__lte=date_fin_obj)
            except ValueError:
                pass
    
    # Les Envois/Retraits n'ont pas d'opérateur mobile :
    # si un opérateur est filtré, on les exclut.
    if operateur or type_transaction == 'credit':
        er_operations = er_operations.none()
    elif type_transaction == 'depot':
        er_operations = er_operations.filter(type_operation='envoi')
    elif type_transaction == 'retrait':
        er_operations = er_operations.filter(type_operation='retrait')
    
    # ========== CALCUL DES TOTAUX (APRES FILTRES) ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    total_commission = transactions.aggregate(Sum('commission'))['commission__sum'] or 0
    
    # Les ENVOIS entrent dans la caisse de l'agent, les RETRAITS en sortent
    total_envois = er_operations.filter(type_operation='envoi').aggregate(Sum('montant'))['montant__sum'] or 0
    total_retraits = er_operations.filter(type_operation='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    total_entree += total_envois
    total_sortie += total_retraits
    
    # ========== FUSION TRANSACTIONS + ENVOIS/RETRAITS ==========
    items = [{
        'kind': 'transaction',
        'obj': t,
        'date': t.date,
        'fait_par': fait_par.get(t.user_id, t.user.username),
    } for t in transactions]
    for op in er_operations:
        if op.source_type == 'admin':
            source_label = f"Admin {op.admin_source.nom}" if op.admin_source else "Admin"
        else:
            source_label = f"Assistant {op.assistant_source.nom}" if op.assistant_source else "Assistant"
        items.append({
            'kind': 'er',
            'obj': op,
            'date': op.date,
            'fait_par': source_label,
        })
    items.sort(key=lambda x: x['date'], reverse=True)
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(items, 10)
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    context = {
        'title': 'Mes transactions',
        'agent': agent,  # Garde le nom agent pour la compatibilité avec le template
        'transactions': transactions_page,
        'total_entree': total_entree,
        'total_sortie': total_sortie,
        'total_commission': total_commission,
        'date_debut': date_debut_display,
        'date_fin': date_fin_display,
    }
    return render(request, 'transactions/historique_agent.html', context)

@login_required
def operation_agent(request):
    """
    Opération sur agent : Admin ou Assistant peut ajouter ou retirer des fonds
    Admin et Assistant partagent le même solde (caisse de l'admin)
    """
    if request.method != 'POST':
        return redirect('gestion_agents')
    
    agent_id = request.POST.get('agent_id')
    operation_type = request.POST.get('operation_type')  # 'ajout' ou 'retrait'
    type_fonds = request.POST.get('type_fonds')  # 'cash', 'uv', 'wave'
    montant = request.POST.get('montant')
    description = request.POST.get('description', '')
    
    if not agent_id:
        messages.error(request, "Veuillez sélectionner un agent")
        return redirect('gestion_agents')
    
    try:
        montant = Decimal(str(montant))
        if montant <= 0:
            messages.error(request, "Le montant doit être supérieur à 0")
            return redirect('gestion_agents')
        
        if montant < 100:
            messages.error(request, "Le montant minimum est de 100 FCFA")
            return redirect('gestion_agents')
        
        # Récupérer l'agent
        agent = Agent.objects.get(id=agent_id)
        
        # Déterminer qui est l'opérateur et la caisse partagée
        try:
            admin_obj = Admin.objects.get(user=request.user)
            operateur_type = 'admin'
            operateur_nom = admin_obj.nom
            caisse_partagee = admin_obj.user.caisse
        except Admin.DoesNotExist:
            assistant = Assistant.objects.get(user=request.user)
            operateur_type = 'assistant'
            operateur_nom = assistant.nom
            caisse_partagee = assistant.get_caisse
        
        # Déterminer le champ et les soldes
        if type_fonds == 'cash':
            champ = 'solde_cash'
            solde_partage = getattr(caisse_partagee, champ, 0)
            solde_agent = getattr(agent.user.caisse, champ, 0)
            type_label = "Cash"
        elif type_fonds == 'uv':
            champ = 'solde_uv'
            solde_partage = getattr(caisse_partagee, champ, 0)
            solde_agent = getattr(agent.user.caisse, champ, 0)
            type_label = "UV Touchpoint"
        else:
            champ = 'solde_wave'
            solde_partage = getattr(caisse_partagee, champ, 0)
            solde_agent = getattr(agent.user.caisse, champ, 0)
            type_label = "UV Wave"
        
        if operation_type == 'ajout':
            # ➕ AJOUT : Donner à l'agent
            if solde_partage < montant:
                messages.error(request, f"Solde {type_label} insuffisant. Disponible: {solde_partage:,.0f} FCFA")
                return redirect('gestion_agents')
            
            # Débiter la caisse partagée
            setattr(caisse_partagee, champ, solde_partage - montant)
            caisse_partagee.save()
            
            # Créditer l'agent
            setattr(agent.user.caisse, champ, solde_agent + montant)
            agent.user.caisse.save()
            
            # Enregistrer l'historique
            HistoriqueAgent.objects.create(
                agent=agent,
                type_operation='decaissement',
                operateur_type=operateur_type,
                operateur_nom=operateur_nom,
                montant_cash=montant if type_fonds == 'cash' else 0,
                montant_uv=montant if type_fonds == 'uv' else 0,
                montant_wave=montant if type_fonds == 'wave' else 0,
                description=f"Ajout de {montant:,.0f} FCFA en {type_label} - {description}" if description else f"Ajout de {montant:,.0f} FCFA en {type_label}"
            )
            
            messages.success(request, f"✅ {montant:,.0f} FCFA ajoutés à {agent.nom} en {type_label}")
            
        elif operation_type == 'retrait':
            # ➖ RETRAIT : Reprendre à l'agent
            if solde_agent < montant:
                messages.error(request, f"Solde {type_label} de {agent.nom} insuffisant. Disponible: {solde_agent:,.0f} FCFA")
                return redirect('gestion_agents')
            
            # Débiter l'agent
            setattr(agent.user.caisse, champ, solde_agent - montant)
            agent.user.caisse.save()
            
            # Créditer la caisse partagée
            setattr(caisse_partagee, champ, solde_partage + montant)
            caisse_partagee.save()
            
            # Enregistrer l'historique
            HistoriqueAgent.objects.create(
                agent=agent,
                type_operation='encaissement',
                operateur_type=operateur_type,
                operateur_nom=operateur_nom,
                montant_cash=montant if type_fonds == 'cash' else 0,
                montant_uv=montant if type_fonds == 'uv' else 0,
                montant_wave=montant if type_fonds == 'wave' else 0,
                description=f"Retrait de {montant:,.0f} FCFA en {type_label} - {description}" if description else f"Retrait de {montant:,.0f} FCFA en {type_label}"
            )
            
            messages.success(request, f"✅ {montant:,.0f} FCFA retirés de {agent.nom} en {type_label}")
        
        else:
            messages.error(request, "Type d'opération invalide")
        
    except Agent.DoesNotExist:
        messages.error(request, "Agent introuvable")
    except Assistant.DoesNotExist:
        messages.error(request, "Assistant non trouvé")
    except Admin.DoesNotExist:
        messages.error(request, "Admin non trouvé")
    except Exception as e:
        messages.error(request, f"Erreur: {str(e)}")
    
    return redirect('gestion_agents')

@login_required
def historique_operations(request):
    """Page d'historique des opérations (Admin/Assistant → Agents)"""
    agents = Agent.objects.all()
    return render(request, 'transactions/historique_operations.html', {'agents': agents})

@login_required
def api_historique_agent_page(request):
    """API pour récupérer l'historique des opérations avec pagination et filtres"""
    
    # Récupérer les paramètres
    page = request.GET.get('page', 1)
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')
    agent_id = request.GET.get('agent_id')
    type_operation = request.GET.get('type')  # 'decaissement' ou 'encaissement'
    
    # Base des opérations
    historique = HistoriqueAgent.objects.all().order_by('-date_operation')
    
    # Appliquer les filtres
    if date_debut_str:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            historique = historique.filter(date_operation__date__gte=date_debut)
        except:
            pass
    
    if date_fin_str:
        try:
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
            historique = historique.filter(date_operation__date__lte=date_fin)
        except:
            pass
    
    if agent_id:
        try:
            historique = historique.filter(agent_id=int(agent_id))
        except:
            pass
    
    if type_operation:
        historique = historique.filter(type_operation=type_operation)
    
    # Calcul des stats (sans pagination)
    total_ajouts = 0
    total_retraits = 0
    
    for h in historique:
        montant_total = float(h.get_montant_total())
        if h.type_operation == 'decaissement':
            total_ajouts += montant_total
        else:
            total_retraits += montant_total
    
    # Pagination
    paginator = Paginator(historique, 20)
    page_obj = paginator.get_page(page)
    
    # Formater les données
    data = []
    for h in page_obj:
        isAjout = h.type_operation == 'decaissement'
        data.append({
            'id': h.id,
            'agent': h.agent.nom,
            'agent_id': h.agent.id,
            'type_operation': h.type_operation,
            'type_label': 'Ajout (Donné)' if isAjout else 'Retrait (Récupéré)',
            'operateur_type': h.operateur_type,
            'operateur_label': 'Admin' if h.operateur_type == 'admin' else 'Assistant',
            'operateur_nom': h.operateur_nom,
            'montant_total': float(h.get_montant_total()),
            'description': h.description or '',
            'date': h.date_operation.strftime('%d/%m/%Y %H:%M:%S')
        })
    
    # Pagination info
    start_page = max(1, page_obj.number - 2)
    end_page = min(paginator.num_pages, page_obj.number + 2)
    
    return JsonResponse({
        'success': True,
        'historique': data,
        'stats': {
            'total_ajouts': total_ajouts,
            'total_retraits': total_retraits,
            'total_operations': historique.count()
        },
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_previous': page_obj.has_previous(),
            'has_next': page_obj.has_next(),
            'previous_page': page_obj.previous_page_number() if page_obj.has_previous() else None,
            'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
            'start_page': start_page,
            'end_page': end_page,
        }
    })

@login_required
def api_historique_agent(request, agent_id=None):
    """API pour récupérer l'historique des opérations sur les agents"""
    historique = HistoriqueAgent.objects.all().order_by('-date_operation')[:200]
    
    if agent_id:
        historique = historique.filter(agent_id=agent_id)
    
    data = {
        'success': True,
        'historique': []
    }
    
    for h in historique:
        if h.type_operation == 'decaissement':
            type_label = '📤 Ajout (Admin/Assistant donne)'
        else:
            type_label = '📥 Retrait (Admin/Assistant reprend)'
        
        operateur_label = '👨‍💼 Admin' if h.operateur_type == 'admin' else '🤝 Assistant'
        
        data['historique'].append({
            'id': h.id,
            'agent': h.agent.nom,
            'agent_id': h.agent.id,
            'type_operation': h.type_operation,
            'type_label': type_label,
            'operateur_type': h.operateur_type,
            'operateur_label': operateur_label,
            'operateur_nom': h.operateur_nom,
            'montant_cash': float(h.montant_cash),
            'montant_uv': float(h.montant_uv),
            'montant_wave': float(h.montant_wave),
            'montant_total': float(h.get_montant_total()),
            'description': h.description or '',
            'date': h.date_operation.strftime('%d/%m/%Y %H:%M:%S')
        })
    
    return JsonResponse(data)

@login_required
@require_POST
def ajax_calculer_frais(request):
    """
    API pour calculer les frais en temps réel (AJAX)
    """
    data = json.loads(request.body)
    operateur = data.get('operateur')
    type_transaction = data.get('type')
    montant = Decimal(data.get('montant', 0))
    
    temp_transaction = Transaction(
        operateur=operateur,
        type_transaction=type_transaction,
        montant=montant
    )
    
    commission = temp_transaction.calculer_commission()
    frais = temp_transaction.calculer_frais_operateur()
    
    return JsonResponse({
        'commission': str(commission),
        'frais': str(frais),
        'total_a_payer': str(montant + frais) if type_transaction == 'depot' else str(montant)
    })

@login_required
def api_annuler_transaction(request):
    import json
    try:
        data = json.loads(request.body)
        reference = data.get('reference', '').strip().upper()
        motif = data.get('motif', '').strip()
        chercher = data.get('chercher', False)
    except (json.JSONDecodeError, AttributeError):
        reference = request.POST.get('reference', '').strip().upper()
        motif = request.POST.get('motif', '').strip()
        chercher = request.POST.get('chercher') == 'true'

    if not reference:
        return JsonResponse({'success': False, 'error': 'Référence obligatoire.'})

    try:
        transaction = Transaction.objects.select_related('user__agent_profile', 'user__admin_profile', 'user__assistant_profile').get(reference=reference)
    except Transaction.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Aucune transaction trouvée avec cette référence.'})

    if chercher:
        agent_nom = ''
        if hasattr(transaction.user, 'agent_profile'):
            agent_nom = transaction.user.agent_profile.nom
        elif hasattr(transaction.user, 'assistant_profile'):
            agent_nom = f"{transaction.user.assistant_profile.nom} (Assistant)"
        elif hasattr(transaction.user, 'admin_profile'):
            agent_nom = f"{transaction.user.admin_profile.nom} (Admin)"
        return JsonResponse({
            'success': True,
            'transaction': {
                'reference': transaction.reference,
                'date': transaction.date.strftime('%d/%m/%Y %H:%M'),
                'type': transaction.get_type_transaction_display(),
                'operateur': transaction.get_operateur_display(),
                'montant': f"{transaction.montant:,.0f}".replace(',', ' '),
                'client': f"{transaction.numero_client} {transaction.nom_client or ''}",
                'agent': agent_nom,
                'est_annule': transaction.est_annule,
            }
        })

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'})

    # Sécurité : seuls l'auteur de la transaction ou un ADMIN peuvent annuler
    is_admin_user = hasattr(request.user, 'admin_profile')
    if not is_admin_user and transaction.user_id != request.user.id:
        return JsonResponse({'success': False, 'error': "Vous n'êtes pas autorisé à annuler cette transaction."})

    if transaction.est_annule:
        return JsonResponse({'success': False, 'error': 'Cette transaction est déjà annulée.'})

    from django.utils import timezone
    transaction.annuler(user=request.user, motif=motif)
    return JsonResponse({'success': True, 'message': f'Transaction {reference} annulée avec succès.'})
