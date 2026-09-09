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
def api_comptes_epargne(request):
    """API REST pour les comptes epargne"""
    from django.core.serializers import json
    from django.http import JsonResponse
    
    if request.method == 'GET':
        comptes = CompteEpargneAdmin.objects.all().order_by('-date_creation')
        total_solde = comptes.aggregate(Sum('solde'))['solde__sum'] or 0
        
        data = {
            'success': True,
            'comptes': [
                {
                    'id': c.id,
                    'titulaire': c.titulaire,
                    'solde': int(c.solde),
                    'date_ouverture': c.date_creation.strftime('%d/%m/%Y'),
                } for c in comptes
            ],
            'total': int(total_solde),
            'nombre': comptes.count(),
        }
        return JsonResponse(data)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def operation_compte(request, compte_id):
    """Effectuer une operation sur un compte epargne"""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    
    compte = get_object_or_404(CompteEpargneAdmin, id=compte_id)
    
    if request.method == 'POST':
        type_operation = request.POST.get('type_operation')
        montant = request.POST.get('montant', 0)
        
        try:
            montant = int(montant)
        except ValueError:
            montant = 0
        
        if montant <= 0:
            messages.error(request, 'Montant invalide')
        elif type_operation == 'retrait' and montant > compte.solde:
            messages.error(request, 'Solde insuffisant')
        else:
            if type_operation == 'depot':
                compte.solde += montant
                description = f"Depot de {montant:,.0f} FCFA"
            else:
                compte.solde -= montant
                description = f"Retrait de {montant:,.0f} FCFA"
            
            compte.save()
            OperationEpargne.objects.create(
                compte=compte,
                type_operation=type_operation,
                montant=montant,
                description=description
            )
            messages.success(request, f'{description} effectue')
    
    return redirect('rapports_admin')

@login_required
def get_caisse_operations(request):
    """API pour recuperer les operations de caisse"""
    from django.http import JsonResponse
    
    operations = OperationCaisse.objects.filter(user=request.user).order_by('-date_operation')[:50]
    data = {
        'success': True,
        'operations': [
            {
                'id': op.id,
                'type': op.type_operation,
                'montant': int(op.montant),
                'description': op.description,
                'date': op.date_operation.strftime('%d/%m/%Y %H:%M:%S')
            } for op in operations
        ]
    }
    return JsonResponse(data)
