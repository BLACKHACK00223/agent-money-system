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

def demander_approvisionnement_api(request):
    """
    API pour les demandes d'approvisionnement (AJAX seulement)
    L'agent peut choisir entre Admin ou Assistant comme destinataire
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
    except Agent.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas configuré comme agent.'})
    
    type_echange = request.POST.get('type_echange')
    montant = request.POST.get('montant')
    destinataire_type = request.POST.get('destinataire_type', 'admin')  # 'admin' ou 'assistant'
    assistant_id = request.POST.get('assistant_id')
    
    if not type_echange or not montant:
        return JsonResponse({'success': False, 'error': 'Veuillez remplir tous les champs'})
    
    if not destinataire_type:
        return JsonResponse({'success': False, 'error': 'Veuillez choisir un destinataire (Admin ou Assistant)'})
    
    # Si destinataire est assistant, vérifier que l'assistant_id est fourni
    if destinataire_type == 'assistant' and not assistant_id:
        return JsonResponse({'success': False, 'error': 'Veuillez sélectionner un assistant'})
    
    try:
        montant = Decimal(montant)
    except:
        return JsonResponse({'success': False, 'error': 'Montant invalide'})
    
    if montant < 1000:
        return JsonResponse({'success': False, 'error': 'Le montant minimum est de 1000 FCFA'})
    
    # Si destinataire est assistant, vérifier que l'assistant existe et est actif
    assistant_destinataire = None
    if destinataire_type == 'assistant':
        try:
            assistant_destinataire = Assistant.objects.get(id=assistant_id, est_actif=True)
        except Assistant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Assistant non trouvé ou inactif'})
    
    # Vérifier le solde selon le type d'échange
    if type_echange == 'uv_to_cash':
        if montant > caisse.solde_uv:
            return JsonResponse({'success': False, 'error': f"Solde UV insuffisant. Solde actuel: {caisse.solde_uv:,.0f} FCFA"})
    elif type_echange == 'wave_to_cash':
        if montant > caisse.solde_wave:
            return JsonResponse({'success': False, 'error': f"Solde Wave insuffisant. Solde actuel: {caisse.solde_wave:,.0f} FCFA"})
    elif type_echange == 'cash_to_uv':
        if montant > caisse.solde_cash:
            return JsonResponse({'success': False, 'error': f"Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"})
    elif type_echange == 'cash_to_wave':
        if montant > caisse.solde_cash:
            return JsonResponse({'success': False, 'error': f"Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"})
    else:
        return JsonResponse({'success': False, 'error': 'Type d\'échange invalide'})
    
    # Créer la demande avec le destinataire choisi (sans motif)
    try:
        demande = DemandeApprovisionnement.objects.create(
            agent=agent,
            type_echange=type_echange,
            montant=montant,
            motif='',  # Motif vide
            destinataire_type=destinataire_type,
            assistant_destinataire=assistant_destinataire,
            statut='en_attente'
        )
        
        # Message personnalisé selon le destinataire
        if destinataire_type == 'admin':
            message = f'Demande envoyée à l\'Administrateur'
        else:
            message = f'Demande envoyée à l\'Assistant {assistant_destinataire.nom}'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'demande_id': demande.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def demander_approvisionnement(request):
    """
    L'AGENT fait une demande d'approvisionnement
    Peut choisir entre ADMIN ou ASSISTANT comme destinataire
    Types d'échanges possibles:
    - uv_to_cash: Échanger UV contre Cash
    - wave_to_cash: Échanger Wave contre Cash
    - cash_to_uv: Échanger Cash contre UV
    - cash_to_wave: Échanger Cash contre Wave
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas configuré comme agent.')
        return redirect('login')
    
    # Récupérer la liste des assistants disponibles
    assistants = Assistant.objects.filter(est_actif=True)
    
    # Détecter si c'est une requête AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Pré-sélection du type depuis l'URL
    type_preset = request.GET.get('type', '')
    
    if request.method == 'POST':
        type_echange = request.POST.get('type_echange')
        montant = request.POST.get('montant')
        destinataire_type = request.POST.get('destinataire_type', 'admin')
        assistant_id = request.POST.get('assistant_id')
        
        if not type_echange or not montant or not destinataire_type:
            error_msg = 'Veuillez remplir tous les champs correctement.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('demander_approvisionnement')
        
        # Si destinataire est assistant, vérifier l'assistant_id
        if destinataire_type == 'assistant' and not assistant_id:
            error_msg = 'Veuillez sélectionner un assistant.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('demander_approvisionnement')
        
        try:
            montant = Decimal(montant)
        except:
            error_msg = 'Montant invalide'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('demander_approvisionnement')
        
        if montant < 1000:
            error_msg = 'Le montant minimum est de 1 000 FCFA'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('demander_approvisionnement')
        
        # Vérifier le solde selon le type d'échange
        solde_ok = True
        message_erreur = ""
        
        if type_echange == 'uv_to_cash':
            if montant > caisse.solde_uv:
                solde_ok = False
                message_erreur = f"Solde UV insuffisant. Solde actuel: {caisse.solde_uv:,.0f} FCFA"
        elif type_echange == 'wave_to_cash':
            if montant > caisse.solde_wave:
                solde_ok = False
                message_erreur = f"Solde Wave insuffisant. Solde actuel: {caisse.solde_wave:,.0f} FCFA"
        elif type_echange == 'cash_to_uv':
            if montant > caisse.solde_cash:
                solde_ok = False
                message_erreur = f"Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"
        elif type_echange == 'cash_to_wave':
            if montant > caisse.solde_cash:
                solde_ok = False
                message_erreur = f"Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA"
        else:
            solde_ok = False
            message_erreur = "Type d'échange invalide"
        
        if not solde_ok:
            if is_ajax:
                return JsonResponse({'success': False, 'error': message_erreur})
            messages.error(request, message_erreur)
            return redirect('demander_approvisionnement')
        
        # Récupérer l'assistant si nécessaire
        assistant_destinataire = None
        if destinataire_type == 'assistant' and assistant_id:
            try:
                assistant_destinataire = Assistant.objects.get(id=assistant_id, est_actif=True)
            except Assistant.DoesNotExist:
                error_msg = 'Assistant non trouvé.'
                if is_ajax:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('demander_approvisionnement')
        
        # Créer la demande (sans motif)
        try:
            demande = DemandeApprovisionnement.objects.create(
                agent=agent,
                type_echange=type_echange,
                montant=montant,
                motif='',  # Motif vide
                destinataire_type=destinataire_type,
                assistant_destinataire=assistant_destinataire,
                statut='en_attente'
            )
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Demande envoyée avec succès',
                    'demande_id': demande.id
                })
            
            if destinataire_type == 'admin':
                messages.success(request, f'✅ Demande envoyée à l\'Administrateur! {montant:,.0f} FCFA')
            else:
                messages.success(request, f'✅ Demande envoyée à l\'Assistant {assistant_destinataire.nom}! {montant:,.0f} FCFA')
            return redirect('dashboard_agent')
            
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'Erreur: {str(e)}')
            return redirect('demander_approvisionnement')
    
    context = {
        'title': 'Demander un approvisionnement',
        'agent': agent,
        'caisse': caisse,
        'type_preset': type_preset,
        'assistants': assistants,
    }
    return render(request, 'transactions/demande_approvisionnement.html', context)

def valider_demande(request, demande_id):
    """
    L'ADMIN valide ou refuse une demande d'approvisionnement
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    demande = django.shortcuts.get_object_or_404(DemandeApprovisionnement, id=demande_id)
    
    print(f"=== VALIDATION DEMANDE ===")
    print(f"Demande ID: {demande_id}")
    print(f"Statut actuel: {demande.statut}")
    
    # Vérifier que la demande est en attente
    if demande.statut != 'en_attente':
        messages.error(request, f'Cette demande a déjà été {demande.get_statut_display().lower()}.')
        return redirect('dashboard_admin')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        print(f"Action: {action}")
        
        if action == 'valider':
            print("Tentative de validation...")
            if demande.valider_par_admin(admin):
                messages.success(request, f'✅ Demande validée! {demande.montant:,.0f} FCFA échangés.')
                print(f"Validation réussie - Nouveau statut: {demande.statut}")
            else:
                messages.error(request, '❌ Solde insuffisant pour valider cette demande.')
                print("Échec de la validation - Solde insuffisant")
        
        elif action == 'refuser':
            demande.statut = 'refuse'
            demande.traite_par_admin = admin
            demande.date_traitement = datetime.now()
            demande.save()
            messages.info(request, 'Demande refusée.')
            print(f"Demande refusée - Nouveau statut: {demande.statut}")
        
        return redirect('dashboard_admin')
    
    context = {
        'title': 'Valider une demande',
        'demande': demande,
    }
    return render(request, 'transactions/valider_demande.html', context)

def historique_demandes_agent(request):
    """
    Historique des demandes d'approvisionnement ET des opérations de caisse
    - Pour un AGENT: ses demandes envoyées + ses opérations de caisse
    - Pour un ASSISTANT: les demandes qu'il a reçues + les opérations de sa caisse
    Avec filtres par date, statut et type d'échange
    """
    from decimal import Decimal
    
    # Vérifier si c'est un agent ou un assistant
    try:
        agent = Agent.objects.get(user=request.user)
        type_utilisateur = 'agent'
        # Demandes de l'agent
        demandes = DemandeApprovisionnement.objects.filter(agent=agent).order_by('-date_demande')
        # Opérations de caisse de l'agent
        operations = OperationCaisse.objects.filter(caisse__user=request.user).order_by('-date_operation')

    except Agent.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
            type_utilisateur = 'assistant'
            # Demandes reçues par l'assistant
            demandes = DemandeApprovisionnement.objects.filter(
                destinataire_type='assistant',
                assistant_destinataire=assistant
            ).order_by('-date_demande')
            # Opérations de caisse de l'assistant (même caisse que l'admin)
            operations = OperationCaisse.objects.filter(caisse__user=request.user).order_by('-date_operation')
        except Assistant.DoesNotExist:
            messages.error(request, 'Vous n\'êtes pas autorisé.')
            return redirect('login')
    
    today = timezone.now().date()
    
    # ========== FILTRES ==========
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    statut = request.GET.get('statut')
    type_echange = request.GET.get('type_echange')
    type_operation_filtre = request.GET.get('type_operation')
    
    # Appliquer les filtres de date sur les demandes et opérations
    if date_debut:
        try:
            date_debut_obj = datetime.strptime(date_debut, '%Y-%m-%d').date()
            demandes = demandes.filter(date_demande__date__gte=date_debut_obj)
            operations = operations.filter(date_operation__date__gte=date_debut_obj)
        except ValueError:
            pass
    
    if date_fin:
        try:
            date_fin_obj = datetime.strptime(date_fin, '%Y-%m-%d').date()
            demandes = demandes.filter(date_demande__date__lte=date_fin_obj)
            operations = operations.filter(date_operation__date__lte=date_fin_obj)
        except ValueError:
            pass
    
    # Si aucun filtre de date n'est appliqué, afficher les demandes et opérations du jour
    if not date_debut and not date_fin:
        demandes = demandes.filter(date_demande__date=today)
        operations = operations.filter(date_operation__date=today)
        date_debut_display = today.strftime('%Y-%m-%d')
        date_fin_display = today.strftime('%Y-%m-%d')
    else:
        date_debut_display = date_debut or today.strftime('%Y-%m-%d')
        date_fin_display = date_fin or today.strftime('%Y-%m-%d')
    
    # Filtre par statut sur les demandes
    if statut:
        demandes = demandes.filter(statut=statut)
    
    # Filtre par type d'échange sur les demandes
    if type_echange:
        demandes = demandes.filter(type_echange=type_echange)
    
    # Filtre par type d'opération sur les opérations de caisse
    if type_operation_filtre:
        operations = operations.filter(type_operation=type_operation_filtre)
    
    # ========== STATISTIQUES ==========
    if type_utilisateur == 'agent':
        stats = {
            'demandes_attente': DemandeApprovisionnement.objects.filter(agent=agent, statut='en_attente').count(),
            'demandes_valide': DemandeApprovisionnement.objects.filter(agent=agent, statut='valide').count(),
            'demandes_refuse': DemandeApprovisionnement.objects.filter(agent=agent, statut='refuse').count(),
            'operations_encaissement': OperationCaisse.objects.filter(caisse__user=request.user, type_operation='encaissement').count(),
            'operations_decaissement': OperationCaisse.objects.filter(caisse__user=request.user, type_operation='decaissement').count(),
        }
    else:
        stats = {
            'demandes_attente': DemandeApprovisionnement.objects.filter(
                destinataire_type='assistant',
                assistant_destinataire=assistant,
                statut='en_attente'
            ).count(),
            'demandes_valide': DemandeApprovisionnement.objects.filter(
                destinataire_type='assistant',
                assistant_destinataire=assistant,
                statut='valide'
            ).count(),
            'demandes_refuse': DemandeApprovisionnement.objects.filter(
                destinataire_type='assistant',
                assistant_destinataire=assistant,
                statut='refuse'
            ).count(),
            'operations_encaissement': OperationCaisse.objects.filter(caisse__user=request.user, type_operation='encaissement').count(),
            'operations_decaissement': OperationCaisse.objects.filter(caisse__user=request.user, type_operation='decaissement').count(),
        }
    
    # Montants totaux des demandes par statut
    stats['montant_attente'] = demandes.filter(statut='en_attente').aggregate(Sum('montant'))['montant__sum'] or 0
    stats['montant_valide'] = demandes.filter(statut='valide').aggregate(Sum('montant'))['montant__sum'] or 0
    
    # Montants totaux des opérations de caisse
    stats['total_encaissements'] = operations.filter(type_operation='encaissement').aggregate(Sum('montant'))['montant__sum'] or 0
    stats['total_decaissements'] = operations.filter(type_operation='decaissement').aggregate(Sum('montant'))['montant__sum'] or 0
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(demandes, 10)
    
    try:
        demandes_page = paginator.page(page)
    except PageNotAnInteger:
        demandes_page = paginator.page(1)
    except EmptyPage:
        demandes_page = paginator.page(paginator.num_pages)
    
    # Pagination pour les opérations
    page_ops = request.GET.get('page_ops', 1)
    paginator_ops = Paginator(operations, 10)
    
    try:
        operations_page = paginator_ops.page(page_ops)
    except PageNotAnInteger:
        operations_page = paginator_ops.page(1)
    except EmptyPage:
        operations_page = paginator_ops.page(paginator_ops.num_pages)
    
    context = {
        'title': 'Mon historique',
        'type_utilisateur': type_utilisateur,
        'demandes': demandes_page,
        'operations': operations_page,
        'stats': stats,
        'date_debut': date_debut_display,
        'date_fin': date_fin_display,
        'statut_filtre': statut,
        'type_echange_filtre': type_echange,
        'type_operation_filtre': type_operation_filtre,
    }
    return render(request, 'transactions/historique_demandes.html', context)

def traiter_demande_assistant(request, demande_id):
    """
    L'ASSISTANT traite (valide ou refuse) une demande d'approvisionnement
    L'assistant utilise la caisse de son ADMIN
    """
    try:
        assistant = Assistant.objects.get(user=request.user)
    except Assistant.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas autorisé.'})
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    demande = get_object_or_404(
        DemandeApprovisionnement, 
        id=demande_id,
        destinataire_type='assistant',
        assistant_destinataire=assistant,
        statut='en_attente'
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if action == 'valider':
            # Récupérer la caisse de l'ADMIN
            caisse_admin = assistant.admin.user.caisse
            caisse_agent = demande.agent.user.caisse
            
            # Vérifier les soldes selon le type d'échange
            solde_ok = True
            message_erreur = ""
            
            print(f"=== DEBUG VALIDATION ===")
            print(f"Type échange: {demande.type_echange}")
            print(f"Montant: {demande.montant}")
            print(f"Solde Admin Cash: {caisse_admin.solde_cash}")
            print(f"Solde Admin UV: {caisse_admin.solde_uv}")
            print(f"Solde Admin Wave: {caisse_admin.solde_wave}")
            print(f"Solde Agent Cash: {caisse_agent.solde_cash}")
            print(f"Solde Agent UV: {caisse_agent.solde_uv}")
            print(f"Solde Agent Wave: {caisse_agent.solde_wave}")
            
            if demande.type_echange == 'uv_to_cash':
                if caisse_agent.solde_uv < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde UV de l'agent insuffisant. Solde actuel: {caisse_agent.solde_uv:,.0f} FCFA"
                elif caisse_admin.solde_cash < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Cash de l'administrateur insuffisant. Solde actuel: {caisse_admin.solde_cash:,.0f} FCFA"
                    
            elif demande.type_echange == 'wave_to_cash':
                if caisse_agent.solde_wave < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Wave de l'agent insuffisant. Solde actuel: {caisse_agent.solde_wave:,.0f} FCFA"
                elif caisse_admin.solde_cash < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Cash de l'administrateur insuffisant. Solde actuel: {caisse_admin.solde_cash:,.0f} FCFA"
                    
            elif demande.type_echange == 'cash_to_uv':
                if caisse_agent.solde_cash < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Cash de l'agent insuffisant. Solde actuel: {caisse_agent.solde_cash:,.0f} FCFA"
                elif caisse_admin.solde_uv < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde UV de l'administrateur insuffisant. Solde actuel: {caisse_admin.solde_uv:,.0f} FCFA"
                    
            elif demande.type_echange == 'cash_to_wave':
                if caisse_agent.solde_cash < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Cash de l'agent insuffisant. Solde actuel: {caisse_agent.solde_cash:,.0f} FCFA"
                elif caisse_admin.solde_wave < demande.montant:
                    solde_ok = False
                    message_erreur = f"Solde Wave de l'administrateur insuffisant. Solde actuel: {caisse_admin.solde_wave:,.0f} FCFA"
            
            if not solde_ok:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': message_erreur})
                messages.error(request, message_erreur)
                return redirect('dashboard_assistant')
            
            # Effectuer la transaction manuellement
            try:
                # Mise à jour des soldes
                if demande.type_echange == 'uv_to_cash':
                    caisse_agent.solde_uv -= demande.montant
                    caisse_agent.solde_cash += demande.montant
                    caisse_admin.solde_cash -= demande.montant
                    caisse_admin.solde_uv += demande.montant
                    
                elif demande.type_echange == 'wave_to_cash':
                    caisse_agent.solde_wave -= demande.montant
                    caisse_agent.solde_cash += demande.montant
                    caisse_admin.solde_cash -= demande.montant
                    caisse_admin.solde_wave += demande.montant
                    
                elif demande.type_echange == 'cash_to_uv':
                    caisse_agent.solde_cash -= demande.montant
                    caisse_agent.solde_uv += demande.montant
                    caisse_admin.solde_uv -= demande.montant
                    caisse_admin.solde_cash += demande.montant
                    
                elif demande.type_echange == 'cash_to_wave':
                    caisse_agent.solde_cash -= demande.montant
                    caisse_agent.solde_wave += demande.montant
                    caisse_admin.solde_wave -= demande.montant
                    caisse_admin.solde_cash += demande.montant
                
                # Sauvegarde
                caisse_agent.save()
                caisse_admin.save()
                
                # Mise à jour de la demande
                demande.statut = 'valide'
                demande.traite_par_assistant = assistant
                demande.date_traitement = timezone.now()
                demande.save()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Demande validée avec succès'})
                messages.success(request, f'✅ Demande validée ! {demande.montant:,.0f} FCFA échangés.')
                
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': str(e)})
                messages.error(request, f'Erreur: {str(e)}')
        
        elif action == 'refuser':
            demande.statut = 'refuse'
            demande.traite_par_assistant = assistant
            demande.date_traitement = timezone.now()
            demande.save()
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Demande refusée'})
            messages.info(request, 'Demande refusée.')
        
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Action invalide'})
        return redirect('dashboard_assistant')
    
    return redirect('dashboard_assistant')

def get_demandes_filter_for_user(user):
    q = Q(statut='en_attente')
    if hasattr(user, 'assistant_profile'):
        q &= Q(destinataire_type='assistant', assistant_destinataire=user.assistant_profile)
    else:
        q &= Q(destinataire_type='admin')
    return q

def api_demandes_attente_count(request):
    q = get_demandes_filter_for_user(request.user)
    count = DemandeApprovisionnement.objects.filter(q).count()
    return JsonResponse({'count': count})

def api_demandes_attente_list(request):
    q = get_demandes_filter_for_user(request.user)
    demandes = DemandeApprovisionnement.objects.filter(q).select_related('agent')
    data = []
    for d in demandes:
        data.append({
            'id': d.id,
            'agent_nom': d.agent.nom,
            'type_echange': d.get_type_echange_display(),
            'montant': f"{d.montant:,.0f}".replace(',', ' '),
            'motif': d.motif[:40] if d.motif else '',
        })
    return JsonResponse({'demandes': data})
