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

def api_analyse_stats(request):
    """
    API pour les statistiques d'analyse
    """
    try:
        today = timezone.now().date()
        
        # ========== PERFORMANCE JOURNALIERE ==========
        transactions_today = Transaction.objects.filter(date__date=today)
        volume_today = transactions_today.aggregate(Sum('montant'))['montant__sum'] or 0
        transactions_count_today = transactions_today.count()
        
        # Convertir Decimal en int/float
        if isinstance(volume_today, Decimal):
            volume_today = int(volume_today)
        
        # Taux de croissance (comparaison avec hier)
        yesterday = today - timedelta(days=1)
        transactions_yesterday = Transaction.objects.filter(date__date=yesterday)
        volume_yesterday = transactions_yesterday.aggregate(Sum('montant'))['montant__sum'] or 0
        
        if isinstance(volume_yesterday, Decimal):
            volume_yesterday = int(volume_yesterday)
        
        if volume_yesterday > 0:
            croissance = ((volume_today - volume_yesterday) / volume_yesterday) * 100
        else:
            croissance = 0 if volume_today == 0 else 100
        
        # ========== MEILLEUR AGENT / UTILISATEUR ==========
        from django.contrib.auth.models import User
        
        user_stats = []
        for user_obj in User.objects.filter(is_active=True):
            total_volume = Transaction.objects.filter(
                user=user_obj,
                date__date__gte=today - timedelta(days=30)
            ).aggregate(Sum('montant'))['montant__sum'] or 0
            
            if isinstance(total_volume, Decimal):
                total_volume = int(total_volume)
            
            if total_volume > 0:
                nom_complet = f"{user_obj.first_name} {user_obj.last_name}".strip()
                if not nom_complet:
                    nom_complet = user_obj.username
                user_stats.append({
                    'nom': nom_complet,
                    'volume': total_volume
                })
        
        user_stats.sort(key=lambda x: x['volume'], reverse=True)
        
        if user_stats:
            meilleur_agent = user_stats[0]['nom']
        else:
            meilleur_agent = "Aucune transaction"
        
        # ========== OPERATEUR PREFERE ==========
        operateur_stats = Transaction.objects.values('operateur')\
            .annotate(total_volume=Sum('montant'), total_count=Count('id'))\
            .order_by('-total_volume')\
            .first()
        
        operateur_labels = {
            'orange': 'Orange Money',
            'malitel': 'Malitel',
            'telecel': 'Telecel',
            'wave': 'Wave'
        }
        
        if operateur_stats:
            operateur_prefere = operateur_labels.get(operateur_stats['operateur'], operateur_stats['operateur'])
        else:
            operateur_prefere = "Aucune opération"
        
        # ========== PREVISION MENSUELLE ==========
        # Calculer la moyenne des 3 derniers mois complets
        three_months_ago = today - timedelta(days=90)
        start_date = datetime(three_months_ago.year, three_months_ago.month, 1).date()
        end_date = datetime(today.year, today.month, 1).date() - timedelta(days=1)
        
        if start_date <= end_date:
            monthly_transactions = Transaction.objects.filter(
                date__date__gte=start_date,
                date__date__lte=end_date
            )
            total_volume_3mois = monthly_transactions.aggregate(Sum('montant'))['montant__sum'] or 0
            
            if isinstance(total_volume_3mois, Decimal):
                total_volume_3mois = int(total_volume_3mois)
            
            prevision_mensuelle = total_volume_3mois / 3 if total_volume_3mois > 0 else 0
        else:
            prevision_mensuelle = 0
        
        # ========== EVOLUTION SUR 12 MOIS ==========
        evolution_12_mois = []
        for i in range(11, -1, -1):
            date_cible = today.replace(day=1) - timedelta(days=30 * i)
            mois = date_cible.month
            annee = date_cible.year
            
            # Premier jour du mois
            debut_mois = date_cible.replace(day=1)
            # Dernier jour du mois
            if mois == 12:
                fin_mois = debut_mois.replace(year=annee+1, month=1) - timedelta(days=1)
            else:
                fin_mois = debut_mois.replace(month=mois+1) - timedelta(days=1)
            
            volume_mois = Transaction.objects.filter(
                date__date__gte=debut_mois,
                date__date__lte=fin_mois
            ).aggregate(Sum('montant'))['montant__sum'] or 0
            
            if isinstance(volume_mois, Decimal):
                volume_mois = int(volume_mois)
            
            # Convertir en millions (avec 1 décimale)
            evolution_12_mois.append(round(float(volume_mois / 1000000), 1))
        
        # ========== TOP 5 USERS ==========
        top_5_users = []
        for us in user_stats[:5]:
            user_obj = User.objects.filter(
                username__icontains=us['nom'].split()[-1] if ' ' in us['nom'] else us['nom']
            ).first()
            if user_obj:
                if hasattr(user_obj, 'admin_profile') and user_obj.admin_profile:
                    role = 'admin'
                elif hasattr(user_obj, 'agent_profile') and user_obj.agent_profile:
                    role = 'agent'
                elif hasattr(user_obj, 'assistant_profile') and user_obj.assistant_profile:
                    role = 'assistant'
                else:
                    role = 'agent'
            else:
                role = 'agent'
            top_5_users.append({
                'nom': us['nom'],
                'volume': us['volume'],
                'type': role
            })
        
        return JsonResponse({
            'success': True,
            'performance_journaliere': {
                'volume': int(volume_today),
                'transactions': transactions_count_today,
                'croissance': round(float(croissance), 1)
            },
            'meilleur_agent': meilleur_agent,
            'operateur_prefere': operateur_prefere,
            'prevision_mensuelle': int(prevision_mensuelle),
            'evolution_12_mois': evolution_12_mois,
            'top_5_users': top_5_users
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
