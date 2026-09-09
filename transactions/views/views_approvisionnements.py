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

from django.db import transaction as db_transaction

@login_required
@require_http_methods(["POST"])
def creer_envoi_retrait(request):
    """
    API : l'ADMIN ou l'ASSISTANT crée une opération ENVOI ou RETRAIT vers un agent.
    statut 'entente' => soldes appliqués immédiatement, listée en Ententes
    statut 'valide'  => soldes appliqués, historique direct
    """
    try:
        admin = Admin.objects.get(user=request.user)
        source_type = 'admin'
        admin_source = admin
        assistant_source = None
    except Admin.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
        except Assistant.DoesNotExist:
            return JsonResponse({'success': False, 'error': "Vous n'êtes pas autorisé."})
        source_type = 'assistant'
        admin_source = None
        assistant_source = assistant

    type_operation = request.POST.get('type_operation')
    type_approvisionnement = request.POST.get('type_approvisionnement')
    agent_id = request.POST.get('agent_id')
    montant_str = request.POST.get('montant')
    statut = request.POST.get('statut', 'entente')

    if type_operation not in ('envoi', 'retrait'):
        return JsonResponse({'success': False, 'error': "Type d'opération invalide."})
    if statut not in ('entente', 'valide'):
        statut = 'entente'

    try:
        agent = Agent.objects.get(id=agent_id, est_actif=True)
    except (Agent.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Agent introuvable ou inactif.'})

    if source_type == 'admin':
        caisse = admin.user.caisse
    else:
        caisse = assistant_source.get_caisse
    if not caisse:
        return JsonResponse({'success': False, 'error': 'Votre caisse n\'est pas configurée.'})

    if source_type == 'assistant' and assistant_source.agent and assistant_source.agent_id == agent.id:
        return JsonResponse({'success': False, 'error': "Impossible d'opérer sur votre propre agent."})

    try:
        montant = Decimal(montant_str)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Montant invalide.'})
    if montant <= 0 or montant_str is None:
        return JsonResponse({'success': False, 'error': 'Montant invalide.'})
    if montant < 1000:
        return JsonResponse({'success': False, 'error': 'Le montant minimum est de 1 000 FCFA.'})

    if type_approvisionnement not in ('cash', 'uv', 'wave'):
        return JsonResponse({'success': False, 'error': 'Type invalide.'})
    if type_operation == 'retrait' and type_approvisionnement not in ('uv', 'wave'):
        return JsonResponse({'success': False, 'error': 'Retrait possible uniquement en UV Touchpoint ou UV Wave.'})

    try:
        with db_transaction.atomic():
            # Verrouiller les caisses : élimine les courses sur les soldes
            caisse = Caisse.objects.select_for_update().get(pk=caisse.pk)

            # ====== Contrôles de solde ======
            if type_operation == 'envoi':
                if type_approvisionnement == 'cash' and montant > caisse.solde_cash:
                    return JsonResponse({'success': False, 'error': f"Solde Argent insuffisant. Solde actuel : {caisse.solde_cash:,.0f} FCFA"})
                if type_approvisionnement == 'uv' and montant > caisse.solde_uv:
                    return JsonResponse({'success': False, 'error': f"Solde UV Touchpoint insuffisant. Solde actuel : {caisse.solde_uv:,.0f} FCFA"})
                if type_approvisionnement == 'wave' and montant > caisse.solde_wave:
                    return JsonResponse({'success': False, 'error': f"Solde UV Wave insuffisant. Solde actuel : {caisse.solde_wave:,.0f} FCFA"})
            else:
                caisse_agent = Caisse.objects.select_for_update().get(pk=agent.user.caisse.pk)
                if montant > caisse.solde_cash:
                    return JsonResponse({'success': False, 'error': f"Solde Argent insuffisant. Solde actuel : {caisse.solde_cash:,.0f} FCFA"})
                if type_approvisionnement == 'uv' and montant > caisse_agent.solde_uv:
                    return JsonResponse({'success': False, 'error': f"Solde UV Touchpoint de l'agent insuffisant. Solde actuel : {caisse_agent.solde_uv:,.0f} FCFA"})
                if type_approvisionnement == 'wave' and montant > caisse_agent.solde_wave:
                    return JsonResponse({'success': False, 'error': f"Solde UV Wave de l'agent insuffisant. Solde actuel : {caisse_agent.solde_wave:,.0f} FCFA"})

            operation = ApprovisionnementDirect.objects.create(
                type_operation=type_operation,
                source_type=source_type,
                admin_source=admin_source,
                assistant_source=assistant_source,
                agent_destinataire=agent,
                type_approvisionnement=type_approvisionnement,
                montant=montant,
                statut=statut,
                date_validation=timezone.now() if statut == 'valide' else None,
                notes=request.POST.get('notes', ''),
            )
    except (ValueError, Caisse.DoesNotExist) as e:
        return JsonResponse({'success': False, 'error': str(e)})

    message = 'Envoi confirmé' if type_operation == 'envoi' else 'Retrait confirmé'
    message += ' en Entente' if statut == 'entente' else ' et Validé'
    return JsonResponse({
        'success': True,
        'message': message,
        'id': operation.id,
        'reference': f"ER-{operation.id:06d}",
        'operation_label': operation.get_type_operation_display(),
        'type_label': operation.get_type_approvisionnement_display(),
    })

@login_required
def envois_retraits(request):
    """
    Page Envois & Retraits (ADMIN ou ASSISTANT) :
    formulaire de création + registre unique avec filtres.
    L'assistant d'un agent utilise la caisse de son agent.
    """
    try:
        admin = Admin.objects.get(user=request.user)
        is_admin = True
        assistant = None
        caisse = admin.user.caisse
    except Admin.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
        except Assistant.DoesNotExist:
            messages.error(request, "Vous n'êtes pas autorisé.")
            return redirect('dashboard_redirect')
        is_admin = False
        admin = None
        caisse = assistant.get_caisse

    agents = Agent.objects.filter(est_actif=True).select_related('user__caisse').order_by('nom')
    filter_agents = Agent.objects.order_by('nom')
    if not is_admin and assistant.agent:
        agents = agents.exclude(id=assistant.agent_id)
        filter_agents = filter_agents.exclude(id=assistant.agent_id)

    operations = ApprovisionnementDirect.objects.select_related(
        'agent_destinataire', 'admin_source', 'assistant_source'
    ).order_by('-date')
    if not is_admin:
        if assistant.agent_id:
            operations = operations.filter(
                Q(agent_destinataire_id=assistant.agent_id) | Q(assistant_source_id=assistant.id)
            )
        elif assistant.admin_id:
            operations = operations.filter(
                Q(admin_source_id=assistant.admin_id) | Q(assistant_source_id=assistant.id)
            )

    stats = {
        'ententes_count': operations.filter(statut='entente').count(),
        'ententes_montant': operations.filter(statut='entente').aggregate(Sum('montant'))['montant__sum'] or 0,
        'valides_count': operations.filter(statut='valide').count(),
        'valides_montant': operations.filter(statut='valide').aggregate(Sum('montant'))['montant__sum'] or 0,
        'envois_count': operations.filter(type_operation='envoi').count(),
        'envois_montant': operations.filter(type_operation='envoi').aggregate(Sum('montant'))['montant__sum'] or 0,
        'retraits_count': operations.filter(type_operation='retrait').count(),
        'retraits_montant': operations.filter(type_operation='retrait').aggregate(Sum('montant'))['montant__sum'] or 0,
    }

    search = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    type_operation = request.GET.get('operation', '')
    type_approvisionnement = request.GET.get('type', '')
    agent_id = request.GET.get('agent', '')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')

    if search:
        search_filter = (
            Q(agent_destinataire__nom__icontains=search) |
            Q(agent_destinataire__telephone__icontains=search)
        )
        reference = search.upper().replace('ER-', '').lstrip('0')
        if reference.isdigit():
            search_filter |= Q(id=int(reference))
        operations = operations.filter(search_filter)
    if statut in ('entente', 'valide'):
        operations = operations.filter(statut=statut)
    else:
        statut = ''
    if type_operation in ('envoi', 'retrait'):
        operations = operations.filter(type_operation=type_operation)
    else:
        type_operation = ''
    if type_approvisionnement in ('cash', 'uv', 'wave'):
        operations = operations.filter(type_approvisionnement=type_approvisionnement)
    else:
        type_approvisionnement = ''
    if agent_id.isdigit():
        agent_id = int(agent_id)
        operations = operations.filter(agent_destinataire_id=agent_id)
    else:
        agent_id = ''
    if date_debut:
        try:
            operations = operations.filter(date__date__gte=datetime.strptime(date_debut, '%Y-%m-%d').date())
        except ValueError:
            date_debut = ''
    if date_fin:
        try:
            operations = operations.filter(date__date__lte=datetime.strptime(date_fin, '%Y-%m-%d').date())
        except ValueError:
            date_fin = ''

    paginator = Paginator(operations, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    filter_query = request.GET.copy()
    filter_query.pop('page', None)

    context = {
        'title': 'Envois & Retraits',
        'admin': admin,
        'assistant': assistant,
        'is_admin': is_admin,
        'caisse': caisse,
        'agents': agents,
        'filter_agents': filter_agents,
        'operations': page_obj,
        'operations_count': paginator.count,
        'page_obj': page_obj,
        'filter_query': filter_query.urlencode(),
        'filters': {
            'q': search,
            'statut': statut,
            'operation': type_operation,
            'type': type_approvisionnement,
            'agent': agent_id,
            'date_debut': date_debut,
            'date_fin': date_fin,
        },
        'stats': stats,
    }
    template_name = 'transactions/envois_retraits.html' if is_admin else 'transactions/envois_retraits_assistant.html'
    return render(request, template_name, context)

@login_required
@require_POST
def promouvoir_entente(request, operation_id):
    """
    L'ADMIN ou l'ASSISTANT promeut une Entente en Valide.
    Changement de statut uniquement : les soldes ont déjà été appliqués à la création.
    """
    is_assistant = False
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
            is_assistant = True
        except Assistant.DoesNotExist:
            messages.error(request, "Vous n'êtes pas autorisé.")
            return redirect('dashboard_redirect')

    operation = get_object_or_404(ApprovisionnementDirect, id=operation_id, statut='entente')
    if is_assistant and not (
        operation.assistant_source_id == assistant.id or
        (assistant.agent_id and operation.agent_destinataire_id == assistant.agent_id)
    ):
        messages.error(request, "Vous n'êtes pas autorisé sur cette opération.")
        return redirect('dashboard_redirect')

    operation.statut = 'valide'
    operation.date_validation = timezone.now()
    operation.save()
    messages.success(request, f"Entente n°{operation.id:06d} promue en Valide. Soldes déjà appliqués, aucun nouveau mouvement.")
    return redirect('envois_retraits')

@login_required
def api_agent_soldes(request, agent_id):
    """
    API : soldes de l'agent + téléphone (récap côté admin, avant création)
    """
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': "Vous n'êtes pas autorisé."})

    try:
        agent = Agent.objects.get(id=agent_id, est_actif=True)
    except Agent.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Agent introuvable.'})

    caisse = agent.user.caisse
    return JsonResponse({
        'success': True,
        'agent': agent.nom,
        'cash': float(caisse.solde_cash) if caisse else 0,
        'uv': float(caisse.solde_uv) if caisse else 0,
        'wave': float(caisse.solde_wave) if caisse else 0,
        'telephone': agent.telephone or '',
    })

@login_required
def api_ententes_count(request):
    """
    API : nombre d'ententes en attente (cloche du tableau de bord admin)
    """
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'count': 0})
    count = ApprovisionnementDirect.objects.filter(statut='entente').count()
    return JsonResponse({'count': count})

@login_required
def api_ententes_list(request):
    """
    API : liste des ententes en attente (modale cloche du tableau de bord admin)
    """
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'ententes': []})

    ententes = ApprovisionnementDirect.objects.filter(statut='entente').select_related('agent_destinataire')[:10]
    data = [{
        'id': e.id,
        'agent_nom': e.agent_destinataire.nom,
        'type_operation': e.get_type_operation_display(),
        'type': e.get_type_approvisionnement_display(),
        'montant': f"{e.montant:,.0f}".replace(',', ' '),
        'date': e.date.strftime('%d/%m %H:%M'),
    } for e in ententes]
    return JsonResponse({'ententes': data})

@login_required
def recu_envoi_retrait(request, operation_id):
    """
    Reçu d'une opération Envoi / Retrait.
    JSON pour l'impression QZ Tray, page HTML en fallback.
    Admin et Assistant autorisés (l'assistant d'un agent voit les opérations le concernant).
    """
    is_assistant = False
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        try:
            assistant = Assistant.objects.get(user=request.user)
            is_assistant = True
        except Assistant.DoesNotExist:
            messages.error(request, "Vous n'êtes pas autorisé.")
            return redirect('dashboard_redirect')

    operation = get_object_or_404(ApprovisionnementDirect, id=operation_id)
    if is_assistant and not (
        operation.assistant_source_id == assistant.id or
        (assistant.agent_id and operation.agent_destinataire_id == assistant.agent_id)
    ):
        messages.error(request, "Vous n'êtes pas autorisé sur cette opération.")
        return redirect('dashboard_redirect')
    data = {
        'reference': f"ER-{operation.id:06d}",
        'date': operation.date.strftime('%d/%m/%Y'),
        'heure': operation.date.strftime('%H:%M'),
        'operation': operation.get_type_operation_display(),
        'type': operation.get_type_approvisionnement_display(),
        'agent': operation.agent_destinataire.nom,
        'montant': f"{operation.montant:,.0f}".replace(',', ' '),
        'statut': operation.get_statut_display(),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse(data)
    return render(request, 'transactions/recu_envoi_retrait.html', {'data': data})
