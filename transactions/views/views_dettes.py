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

def ajouter_dette(request):
    """Ajouter une nouvelle dette - SAISIE LIBRE DU NOM"""
    if request.method == 'POST':
        try:
            montant = request.POST.get('montant', 0)
            try:
                montant = int(montant)
            except ValueError:
                montant = 0
            
            if montant <= 0:
                messages.error(request, 'Le montant doit être supérieur à 0')
                return redirect('rapports_admin')
            
            nom_debiteur = request.POST.get('nom_debiteur', '').strip()
            if not nom_debiteur:
                messages.error(request, 'Veuillez saisir le nom du débiteur')
                return redirect('rapports_admin')
            
            # Récupérer la valeur de la case "ajouter à la caisse"
            ajouter_caisse = request.POST.get('ajouter_caisse') == 'on'
            
            debiteur, created = Debiteur.objects.get_or_create(
                nom__iexact=nom_debiteur,
                defaults={
                    'nom': nom_debiteur,
                    'telephone': request.POST.get('telephone', ''),
                    'email': request.POST.get('email', ''),
                    'adresse': request.POST.get('adresse', ''),
                    'cree_par': request.user
                }
            )
            
            if not created:
                if request.POST.get('telephone') and not debiteur.telephone:
                    debiteur.telephone = request.POST.get('telephone')
                if request.POST.get('email') and not debiteur.email:
                    debiteur.email = request.POST.get('email')
                if request.POST.get('adresse') and not debiteur.adresse:
                    debiteur.adresse = request.POST.get('adresse')
                debiteur.save()
            
            dette = Dette.objects.create(
                debiteur=debiteur,
                montant=montant,
                date_echeance=request.POST.get('date_echeance'),
                motif=request.POST.get('motif', ''),
                cree_par=request.user
            )
            
            message = f'Dette de {montant:,.0f} FCFA ajoutée pour {debiteur.nom}'
            
            # ========== CRÉATION DETTE : ON SOUSTRAIT DE LA CAISSE ==========
            if ajouter_caisse:
                try:
                    caisse, cree = Caisse.objects.get_or_create(
                        user=request.user,
                        defaults={'solde_cash': 0, 'solde_uv': 0, 'solde_wave': 0}
                    )
                    # SOUSTRAIRE de la caisse (l'argent sort)
                    caisse.solde_cash -= montant
                    caisse.save()
                    message += f" et retiré {montant:,.0f} FCFA de la caisse espèces"
                except Exception as e:
                    message += f" (⚠️ erreur caisse: {str(e)})"
            
            if created:
                messages.success(request, f'Nouveau débiteur "{nom_debiteur}" créé. {message}')
            else:
                messages.success(request, message)
                
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('rapports_admin')

def modifier_dette(request, dette_id):
    """Modifier une dette"""
    dette = get_object_or_404(Dette, id=dette_id)
    
    if request.method == 'POST':
        try:
            montant = request.POST.get('montant', dette.montant)
            try:
                montant = int(montant)
            except ValueError:
                montant = dette.montant
            
            nouveau_nom = request.POST.get('nom_debiteur', '').strip()
            if nouveau_nom and nouveau_nom != dette.debiteur.nom:
                debiteur_existant = Debiteur.objects.filter(nom__iexact=nouveau_nom).first()
                if debiteur_existant:
                    dette.debiteur = debiteur_existant
                else:
                    dette.debiteur.nom = nouveau_nom
                    if request.POST.get('telephone'):
                        dette.debiteur.telephone = request.POST.get('telephone')
                    if request.POST.get('email'):
                        dette.debiteur.email = request.POST.get('email')
                    dette.debiteur.save()
            
            dette.montant = montant
            dette.date_echeance = request.POST.get('date_echeance', dette.date_echeance)
            dette.motif = request.POST.get('motif', dette.motif)
            dette.save()
            messages.success(request, 'Dette modifiée avec succès')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('rapports_admin')

def supprimer_dette(request, dette_id):
    """Supprimer une dette"""
    dette = get_object_or_404(Dette, id=dette_id)
    
    if request.method == 'POST':
        dette.delete()
        messages.success(request, 'Dette supprimée')
    
    return redirect('rapports_admin')

def enregistrer_remboursement_dette(request, dette_id):
    """Enregistrer un remboursement et AJOUTER à la caisse"""
    dette = get_object_or_404(Dette, id=dette_id)
    
    if request.method == 'POST':
        from django.urls import reverse
        try:
            montant = request.POST.get('montant', 0)
            try:
                montant = int(montant)
            except ValueError:
                montant = 0
            
            mode = request.POST.get('mode_paiement', 'cash')
            generer_recu = request.POST.get('generer_recu') == 'on'
            ajouter_caisse = request.POST.get('ajouter_caisse') == 'on'
            
            if montant <= 0:
                messages.error(request, 'Montant invalide')
            elif montant > dette.reste_a_payer:
                messages.error(request, f'Montant dépasse le reste à payer ({dette.reste_a_payer:,.0f} FCFA)')
            else:
                # Enregistrer le remboursement
                remboursement = RemboursementDette.objects.create(
                    dette=dette,
                    montant=montant,
                    mode_paiement=mode,
                    cree_par=request.user
                )
                
                # Mettre à jour la dette
                dette.montant_rembourse += montant
                dette.save()
                
                message = f'✅ Remboursement de {montant:,.0f} FCFA enregistré'
                
                # ========== REMBOURSEMENT : ON AJOUTE À LA CAISSE ==========
                if ajouter_caisse:
                    try:
                        caisse, created = Caisse.objects.get_or_create(
                            user=request.user,
                            defaults={'solde_cash': 0, 'solde_uv': 0, 'solde_wave': 0}
                        )
                        
                        mode_labels = {'cash': 'espèces', 'uv': 'UV Touchpiont', 'wave': 'UV Wave'}
                        
                        # AJOUTER à la caisse selon le mode de paiement
                        if mode == 'cash':
                            caisse.solde_cash += montant
                        elif mode == 'uv':
                            caisse.solde_uv += montant
                        elif mode == 'wave':
                            caisse.solde_wave += montant
                        
                        caisse.save()
                        message += f" et ajouté {montant:,.0f} FCFA au solde {mode_labels.get(mode, mode)}"
                    except Exception as e:
                        message += f" (⚠️ erreur caisse: {str(e)})"
                
                # Générer le reçu si demandé (toujours rediriger, téléchargement auto via JS)
                if generer_recu:
                    return redirect(f"{reverse('rapports_admin')}?recu={remboursement.id}")
                
                messages.success(request, message)
                    
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('rapports_admin')

def generer_recu_pdf(remboursement):
    """Génère un PDF de reçu pour un paiement (format ticket 80mm)"""
    buffer = BytesIO()
    avail = 184
    doc = SimpleDocTemplate(buffer, pagesize=(200, 380), topMargin=8, bottomMargin=8, leftMargin=8, rightMargin=8)
    
    c_gray = colors.HexColor('#6b7280')
    c_dark = colors.HexColor('#111827')
    c_green = colors.HexColor('#059669')
    c_red = colors.HexColor('#dc2626')
    
    s_title = ParagraphStyle('T', fontSize=12, fontName='Helvetica-Bold', textColor=c_dark, alignment=TA_CENTER, spaceAfter=2)
    s_subtitle = ParagraphStyle('ST', fontSize=7, textColor=c_gray, alignment=TA_CENTER, spaceAfter=6)
    s_label = ParagraphStyle('L', fontSize=7, fontName='Helvetica-Bold', textColor=c_gray, spaceAfter=0)
    s_value = ParagraphStyle('V', fontSize=8, textColor=c_dark, spaceAfter=4)
    s_amount = ParagraphStyle('A', fontSize=18, fontName='Helvetica-Bold', textColor=c_green, alignment=TA_CENTER, spaceAfter=2)
    s_rest = ParagraphStyle('R', fontSize=12, fontName='Helvetica-Bold', textColor=c_red, alignment=TA_CENTER, spaceAfter=4)
    s_footer = ParagraphStyle('F', fontSize=6, textColor=c_gray, alignment=TA_CENTER, spaceAfter=0)
    
    story = []
    def hr(c='#d1d5db'): story.append(Table([['']], colWidths=[avail], rowHeights=[1], style=TableStyle([('LINEBELOW',(0,0),(-1,-1),0.5,c)])))
    
    story.append(Paragraph("<b>KONE SERVICES</b>", s_title))
    story.append(Paragraph("Tél : 76 89 77 31", ParagraphStyle('Tel', fontSize=8, fontName='Helvetica-Bold', textColor=c_dark, alignment=TA_CENTER, spaceAfter=2)))
    story.append(Paragraph("Reçu de paiement", s_subtitle))
    hr()
    story.append(Spacer(1, 3))
    
    info = [
        [Paragraph("N° reçu", s_label), Paragraph(f"REC-{remboursement.id:06d}", s_value)],
        [Paragraph("Date", s_label), Paragraph(f"{remboursement.date_remboursement.strftime('%d/%m/%Y %H:%M')}", s_value)],
        [Paragraph("Agent", s_label), Paragraph(f"{remboursement.cree_par.username[:18]}", s_value)],
        [Paragraph("Débiteur", s_label), Paragraph(f"{remboursement.dette.debiteur.nom[:22]}", s_value)],
    ]
    if remboursement.dette.debiteur.telephone:
        info.append([Paragraph("Tél", s_label), Paragraph(f"{remboursement.dette.debiteur.telephone}", s_value)])
    motif = remboursement.dette.motif or "Prêt"
    info.append([Paragraph("Motif", s_label), Paragraph(f"{motif[:22]}", s_value)])
    
    t = Table(info, colWidths=[50, avail-50])
    t.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (1,0), (1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(t)
    story.append(Spacer(1, 4))
    hr()
    story.append(Spacer(1, 4))
    
    def sf(v): return f"{v:,.0f}".replace(",", " ")
    story.append(Paragraph(f"{sf(remboursement.montant)} FCFA", s_amount))
    story.append(Spacer(1, 10))
    paye_label = remboursement.get_mode_paiement_display()
    story.append(Paragraph(f"Payé par {paye_label}", s_subtitle))
    story.append(Spacer(1, 8))
    hr()
    story.append(Spacer(1, 4))
    
    recap = [
        [Paragraph("Total dette", s_label), Paragraph(f"{sf(remboursement.dette.montant)} FCFA", s_value)],
        [Paragraph("Déjà remboursé", s_label), Paragraph(f"{sf(remboursement.dette.montant_rembourse - remboursement.montant)} FCFA", s_value)],
        [Paragraph("Ce paiement", s_label), Paragraph(f"{sf(remboursement.montant)} FCFA", s_value)],
    ]
    tr = Table(recap, colWidths=[75, avail-75])
    tr.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,-1), 'LEFT'), ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(tr)
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("RESTE À PAYER", s_label))
    story.append(Paragraph(f"{sf(remboursement.dette.reste_a_payer)} FCFA", s_rest))
    story.append(Spacer(1, 3))
    hr()
    story.append(Spacer(1, 4))
    
    story.append(Paragraph("Merci de votre confiance", ParagraphStyle('Thanks', fontSize=7, textColor=c_gray, alignment=TA_CENTER, spaceAfter=0)))
    story.append(Paragraph(f"Édité le {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", s_footer))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def download_recu(request, remboursement_id):
    """Télécharger le reçu PDF"""
    remboursement = get_object_or_404(RemboursementDette, id=remboursement_id)
    
    if remboursement.cree_par != request.user and not request.user.is_staff:
        messages.error(request, "Permission non accordée")
        return redirect('rapports_admin')
    
    buffer = generer_recu_pdf(remboursement)
    
    filename = f"recu_{remboursement.dette.debiteur.nom}_{remboursement.date_remboursement.strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return FileResponse(
        buffer,
        as_attachment=True,
        filename=filename,
        content_type='application/pdf'
    )

def api_dettes(request):
    """API REST pour les dettes"""
    if request.method == 'GET':
        dettes = Dette.objects.all().order_by('-date_creation')
        
        statut = request.GET.get('statut')
        debiteur_nom = request.GET.get('debiteur_nom')
        
        if statut and statut != 'all':
            dettes = dettes.filter(statut=statut)
        if debiteur_nom:
            dettes = dettes.filter(debiteur__nom__icontains=debiteur_nom)
        
        total_montant = dettes.aggregate(Sum('montant'))['montant__sum'] or 0
        total_rembourse = dettes.aggregate(Sum('montant_rembourse'))['montant_rembourse__sum'] or 0
        
        data = {
            'success': True,
            'dettes': [
                {
                    'id': d.id,
                    'debiteur_nom': d.debiteur.nom,
                    'debiteur_id': d.debiteur.id,
                    'montant': float(d.montant),
                    'montant_rembourse': float(d.montant_rembourse),
                    'reste': float(d.reste_a_payer),
                    'statut': d.statut,
                    'date_creation': d.date_creation.strftime('%d/%m/%Y'),
                    'date_echeance': d.date_echeance.strftime('%d/%m/%Y'),
                    'motif': d.motif,
                } for d in dettes
            ],
            'total': float(total_montant),
            'payees': float(total_rembourse),
            'attente': float(total_montant - total_rembourse),
            'nombre': dettes.count(),
        }
        return JsonResponse(data)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

def api_dette_detail(request, dette_id):
    """API REST pour le détail d'une dette"""
    if request.method == 'GET':
        dette = get_object_or_404(Dette, id=dette_id)
        
        data = {
            'success': True,
            'id': dette.id,
            'debiteur_nom': dette.debiteur.nom,
            'debiteur_id': dette.debiteur.id,
            'debiteur_telephone': dette.debiteur.telephone or '',
            'debiteur_email': dette.debiteur.email or '',
            'montant': float(dette.montant),
            'montant_rembourse': float(dette.montant_rembourse),
            'reste': float(dette.reste_a_payer),
            'statut': dette.statut,
            'date_creation': dette.date_creation.strftime('%d/%m/%Y'),
            'date_echeance': dette.date_echeance.strftime('%d/%m/%Y'),
            'motif': dette.motif,
            'remboursements': [
                {
                    'id': r.id,
                    'montant': float(r.montant),
                    'mode_paiement': r.mode_paiement,
                    'mode_display': r.get_mode_paiement_display(),
                    'date': r.date_remboursement.strftime('%d/%m/%Y %H:%M:%S'),
                    'cree_par': r.cree_par.username,
                } for r in dette.remboursements.all()
            ]
        }
        return JsonResponse(data)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

def api_chercher_debiteurs(request):
    """API pour rechercher des débiteurs par nom (autocomplétion)"""
    if request.method == 'GET':
        terme = request.GET.get('q', '')
        if len(terme) >= 2:
            debiteurs = Debiteur.objects.filter(nom__icontains=terme)[:10]
            data = {
                'success': True,
                'debiteurs': [
                    {
                        'id': d.id,
                        'nom': d.nom,
                        'telephone': d.telephone or '',
                        'email': d.email or '',
                    } for d in debiteurs
                ]
            }
        else:
            data = {'success': True, 'debiteurs': []}
        return JsonResponse(data)
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})
