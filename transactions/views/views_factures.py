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

def creer_facture(request):
    """Creer une nouvelle facture"""
    if request.method == 'POST':
        type_facture = request.POST.get('type_facture')
        numero = request.POST.get('numero')
        personne_nom = request.POST.get('personne_nom')
        montant_total = request.POST.get('montant_total')
        date_echeance = request.POST.get('date_echeance')
        
        try:
            montant_total = int(montant_total)
            if montant_total <= 0:
                messages.error(request, "Le montant doit etre superieur a 0")
                return redirect('rapports_admin')
            
            # Generer un numero de facture unique
            import random
            import string
            numero = f"FAC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            
            facture = Facture.objects.create(
                numero=numero,
                type_facture=type_facture,
                
                personne_nom=personne_nom,
                montant_total=montant_total,
                montant_paye=0,
                date_echeance=date_echeance,
                statut='en_attente',
                cree_par=request.user
            )
            
            messages.success(request, f"Facture {numero} cree avec succes")
            
        except ValueError:
            messages.error(request, "Montant invalide")
        except Exception as e:
            messages.error(request, f"Erreur lors de la creation: {str(e)}")
        
        return redirect('rapports_admin')
    
    return redirect('rapports_admin')

def api_factures(request):
    """API pour recuperer les factures"""
    factures = Facture.objects.filter(cree_par=request.user).order_by('-date_emission')
    
    data = {
        'factures': [
            {
                'id': f.id,
                'numero': f.numero,
                'type_facture': f.type_facture,
                'personne_nom': f.personne_nom,
                'montant_total': f.montant_total,
                'montant_paye': f.montant_paye,
                'reste': f.montant_total - f.montant_paye,
                'date_emission': f.date_emission.strftime('%d/%m/%Y'),
                'date_echeance': f.date_echeance.strftime('%d/%m/%Y'),
                'statut': f.statut
            } for f in factures
        ]
    }
    return JsonResponse(data)

def rechercher_client_api(request):
    """API pour rechercher un client par téléphone"""
    numero = request.GET.get('numero', '')
    if numero:
        transactions = Transaction.objects.filter(
            numero_client=numero
        ).select_related('user__agent').order_by('-date')[:5]
        
        factures = Facture.objects.filter(
            personne_telephone=numero
        ).order_by('-date_emission')[:5]
        
        clients_data = []
        
        for t in transactions:
            agent_nom = t.user.agent.nom if hasattr(t.user, 'agent') else 'Agent'
            clients_data.append({
                'numero': t.numero_client,
                'nom': f"Client {t.numero_client}",
                'source': f'Transaction du {t.date.strftime("%d/%m/%Y")}',
                'montant_moyen': float(t.montant),
                'agent': agent_nom
            })
        
        for f in factures:
            clients_data.append({
                'numero': f.personne_telephone,
                'nom': f.personne_nom,
                'source': f'Facture {f.numero}',
                'type': f.get_type_facture_display(),
                'montant_total': float(f.montant_total)
            })
        
        uniques = {}
        for client in clients_data:
            if client['numero'] not in uniques:
                uniques[client['numero']] = client
        
        return JsonResponse({
            'success': True,
            'clients': list(uniques.values()),
            'found': len(uniques) > 0
        })
    
    return JsonResponse({'success': False, 'clients': []})

def detail_facture(request, facture_id):
    facture = get_object_or_404(Facture, id=facture_id)
    return render(request, 'transactions/detail_facture.html', {'facture': facture})

def modifier_facture(request, facture_id):
    """Modifier une facture"""
    facture = get_object_or_404(Facture, id=facture_id)
    
    if request.method == 'POST':
        facture.client_nom = request.POST.get('client_nom', facture.client_nom)
        facture.client_email = request.POST.get('client_email', facture.client_email)
        facture.client_telephone = request.POST.get('client_telephone', facture.client_telephone)
        facture.description = request.POST.get('description', facture.description)
        facture.save()
        messages.success(request, 'Facture modifiée avec succès')
    
    return redirect('rapports_admin')

def enregistrer_paiement_facture(request, facture_id):
    """Enregistrer un paiement sur une facture"""
    facture = get_object_or_404(Facture, id=facture_id)
    
    if request.method == 'POST':
        try:
            montant = request.POST.get('montant', 0)
            try:
                montant = int(montant)
            except ValueError:
                montant = 0
            
            mode = request.POST.get('mode_paiement', 'cash')
            
            if montant <= 0:
                messages.error(request, 'Montant invalide')
            elif montant > facture.reste_a_payer:
                messages.error(request, f'Montant dépasse le reste à payer ({facture.reste_a_payer:,.0f} FCFA)')
            else:
                facture.montant_paye += montant
                facture.save()
                
                PaiementFacture.objects.create(
                    facture=facture,
                    montant=montant,
                    mode_paiement=mode,
                    cree_par=request.user
                )
                messages.success(request, f'Paiement de {montant:,.0f} FCFA enregistré')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('rapports_admin')

def generer_facture_pdf(request, facture_id):
    """Générer une facture PDF professionnelle"""
    
    facture = get_object_or_404(Facture, id=facture_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="FACTURE_{facture.numero}.pdf"'
    
    doc = SimpleDocTemplate(
        response, 
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    
    # ========== COULEURS AMÉLIORÉES ==========
    primary = colors.HexColor('#0f766e')      # Teal élégant
    gold = colors.HexColor('#f59e0b')         # Orange doré
    danger = colors.HexColor('#dc2626')       # Rouge plus vif
    success = colors.HexColor('#059669')      # Vert plus profond
    light = colors.HexColor('#f0fdf4')        # Vert très clair
    border = colors.HexColor('#cbd5e1')       # Bordure plus douce
    medium = colors.HexColor('#475569')       # Gris plus soutenu
    dark = colors.HexColor('#1e293b')         # Gris très foncé
    
    style_h1 = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=22, textColor=primary, alignment=TA_LEFT, fontName='Helvetica-Bold')
    style_h1_right = ParagraphStyle('H1Right', parent=styles['Heading1'], fontSize=22, textColor=primary, alignment=TA_RIGHT, fontName='Helvetica-Bold')
    style_title = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=primary, alignment=TA_CENTER, spaceAfter=5, fontName='Helvetica-Bold')
    style_subtitle = ParagraphStyle('Subtitle', parent=normal, alignment=TA_CENTER, fontSize=9, textColor=medium, spaceAfter=15)
    style_section = ParagraphStyle('Section', parent=normal, fontSize=12, textColor=primary, spaceAfter=8, fontName='Helvetica-Bold')
    style_label = ParagraphStyle('Label', parent=normal, fontSize=8, textColor=medium, fontName='Helvetica-Bold')
    style_value = ParagraphStyle('Value', parent=normal, fontSize=9, textColor=dark)
    style_small = ParagraphStyle('Small', parent=normal, fontSize=7, textColor=medium)
    style_small_right = ParagraphStyle('SmallRight', parent=normal, fontSize=7, textColor=medium, alignment=TA_RIGHT)
    
    elements = []
    
    # En-tête
    header_row1 = [[Paragraph("KONE SERVICES", style_h1), Paragraph("FACTURE", style_h1_right)]]
    header_table1 = Table(header_row1, colWidths=[8.5*cm, 8.5*cm])
    header_table1.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table1)
    elements.append(Spacer(1, 5))
    
    header_row2 = [[Paragraph("✉ koneorange20@gmail.com", style_small), Paragraph(f"TYPE : {facture.type_facture}", style_small_right)]]
    header_table2 = Table(header_row2, colWidths=[8.5*cm, 8.5*cm])
    header_table2.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table2)
    elements.append(Spacer(1, 3))
    
    header_row3 = [[Paragraph("Bamako - Mali", style_small), Paragraph(f"N° {facture.numero}", style_small_right)]]
    header_table3 = Table(header_row3, colWidths=[8.5*cm, 8.5*cm])
    header_table3.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table3)
    elements.append(Spacer(1, 3))
    
    header_row4 = [[Paragraph("📞 +223 76 89 77 31", style_small), Paragraph(f"EMISSION : {facture.date_emission.strftime('%d/%m/%Y')}", style_small_right)]]
    header_table4 = Table(header_row4, colWidths=[8.5*cm, 8.5*cm])
    header_table4.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table4)
    elements.append(Spacer(1, 3))
    
    header_row5 = [[Paragraph("", style_small), Paragraph(f"ECHEANCE : {facture.date_echeance.strftime('%d/%m/%Y')}", style_small_right)]]
    header_table5 = Table(header_row5, colWidths=[8.5*cm, 8.5*cm])
    header_table5.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(header_table5)
    elements.append(Spacer(1, 10))
    
    line = Table([['']], colWidths=[17*cm], rowHeights=[2])
    line.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), primary)]))
    elements.append(line)
    elements.append(Spacer(1, 20))
    
    # Titre
    elements.append(Paragraph(f"FACTURE {facture.type_facture.upper()}", style_title))
    elements.append(Spacer(1, 20))
    # Informations client

    
    client_data = [
        [Paragraph("NOM", style_label), Paragraph(facture.personne_nom or "Non renseigné", style_value)],
        [Paragraph("TÉLÉPHONE", style_label), Paragraph(facture.personne_telephone or "Non renseigné", style_value)],
    ]
    
    client_table = Table(client_data, colWidths=[4.5*cm, 12*cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), light),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(client_table)
    elements.append(Spacer(1, 20))
    
    elements.append(Spacer(1, 20))
    
    # Détails
    elements.append(Paragraph("DETAILS", style_section))
    elements.append(Spacer(1, 8))
    
    details_header = [
        [Paragraph("DESIGNATION", style_label), Paragraph("QTE", style_label), Paragraph("MONTANT", style_label)]
    ]
    details_row = [
        
    ]
    
    if facture.description:
        details_row.insert(0, [Paragraph(facture.description[:50], style_value), Paragraph("1", style_value), Paragraph(f"{facture.montant_total:,.0f} FCFA", style_value)])
    
    details_table = Table(details_header + details_row, colWidths=[9*cm, 3*cm, 5*cm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (1,0), (2,0), 'CENTER'),
        ('ALIGN', (2,1), (2,1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('GRID', (0,1), (-1,-1), 0.5, border),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 20))
    
    # Totaux
    totals_data = [
        ["MONTANT TOTAL", f"{facture.montant_total:,.0f} FCFA"],
    ]
    
    if facture.montant_paye > 0:
        totals_data.insert(0, ["MONTANT PAYÉ", f"{facture.montant_paye:,.0f} FCFA"])
    
    totals_table = Table(totals_data, colWidths=[5*cm, 5*cm])
    totals_table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), gold),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,-1), (-1,-1), 11),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,-1), (-1,-1), 15),
        ('RIGHTPADDING', (0,-1), (-1,-1), 15),
    ]))
    
    totals_container = Table([[totals_table]], colWidths=[17*cm])
    totals_container.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT')]))
    elements.append(totals_container)
    elements.append(Spacer(1, 20))
    
    # Pied de page
    footer_line = Table([['']], colWidths=[17*cm], rowHeights=[1])
    footer_line.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), border)]))
    elements.append(footer_line)
    elements.append(Spacer(1, 8))
    
    footer = "MERCI POUR VOTRE CONFIANCE"
    elements.append(Paragraph(footer, style_small))
    elements.append(Paragraph(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}", style_small))
    
    doc.build(elements)
    return response

def generer_facture_80mm(request, facture_id):
    """Générer un ticket 80mm professionnel avec QR code, détails complets et design pro"""
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from django.http import HttpResponse
    from datetime import datetime
    import qrcode
    from io import BytesIO
    from reportlab.lib.utils import ImageReader
    
    facture = get_object_or_404(Facture, id=facture_id)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="TICKET_{facture.numero}.pdf"'
    
    # Dimensions exactes pour papier 80mm (182mm de haut pour 80mm de large)
    page_width = 8.0 * cm
    page_height = 28.0 * cm
    
    doc = SimpleDocTemplate(
        response, 
        pagesize=(page_width, page_height),
        topMargin=0.3*cm,
        bottomMargin=0.3*cm,
        leftMargin=0.3*cm,
        rightMargin=0.3*cm
    )
    
    styles = getSampleStyleSheet()
    
    # Styles personnalisés professionnels
    style_logo = ParagraphStyle(
        'Logo', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=14, 
        fontName='Helvetica-Bold', 
        textColor=colors.HexColor('#0f766e'),
        spaceAfter=4
    )
    
    style_soustitre = ParagraphStyle(
        'Soustitre', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=9, 
        textColor=colors.HexColor('#374151'),
        spaceAfter=2
    )
    
    style_sep = ParagraphStyle(
        'Sep', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=7, 
        textColor=colors.HexColor('#9ca3af'),
        spaceAfter=4,
        spaceBefore=4
    )
    
    style_title = ParagraphStyle(
        'Title', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=12, 
        fontName='Helvetica-Bold', 
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        spaceBefore=4
    )
    
    style_info = ParagraphStyle(
        'Info', parent=styles['Normal'], 
        alignment=TA_LEFT, fontSize=8, 
        fontName='Helvetica',
        spaceAfter=2
    )
    
    style_info_center = ParagraphStyle(
        'InfoCenter', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=8,
        spaceAfter=2
    )
    
    style_label = ParagraphStyle(
        'Label', parent=styles['Normal'], 
        alignment=TA_LEFT, fontSize=8, 
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#4b5563')
    )
    
    style_valeur = ParagraphStyle(
        'Valeur', parent=styles['Normal'], 
        alignment=TA_RIGHT, fontSize=8, 
        fontName='Helvetica'
    )
    
    style_montant = ParagraphStyle(
        'Montant', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=16, 
        fontName='Helvetica-Bold', 
        textColor=colors.HexColor('#0f766e'),
        spaceAfter=6,
        spaceBefore=4
    )
    
    style_total = ParagraphStyle(
        'Total', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=18, 
        fontName='Helvetica-Bold', 
        textColor=colors.HexColor('#ef4444'),
        spaceAfter=6,
        spaceBefore=4
    )
    
    style_badge = ParagraphStyle(
        'Badge', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=9, 
        fontName='Helvetica-Bold',
        spaceAfter=6,
        spaceBefore=4
    )
    
    style_footer = ParagraphStyle(
        'Footer', parent=styles['Normal'], 
        alignment=TA_CENTER, fontSize=7, 
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=2
    )
    
    elements = []
    
    # ==================== ENTÊTE ====================
    elements.append(Paragraph("🏦 KONE SERVICES ", style_logo))
    elements.append(Paragraph("• Solutions Financières •", style_soustitre))
    elements.append(Paragraph("Tel: +223 76 89 77 31", style_soustitre))
    elements.append(Paragraph("Email: koneorange20@gmail.com", style_soustitre))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#0f766e'), spaceAfter=4, spaceBefore=4))
    
    # ==================== TYPE DE DOCUMENT ====================
    if facture.type_facture == 'cliente':
        elements.append(Paragraph("📄 FACTURE CLIENT", style_title))
    elif facture.type_facture == 'fournisseur':
        elements.append(Paragraph("📄 FACTURE FOURNISSEUR", style_title))
    else:
        elements.append(Paragraph(f"📄 {facture.type_facture.upper()}", style_title))
    
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor('#d1d5db'), spaceAfter=4, spaceBefore=2))
    
    # ==================== INFORMATIONS FACTURE ====================
    # Tableau des infos facture
    info_data = [
        [Paragraph("<b>N° Facture</b>", style_label), Paragraph(facture.numero, style_valeur)],
        [Paragraph("<b>Date émission</b>", style_label), Paragraph(facture.date_emission.strftime('%d/%m/%Y à %H:%M'), style_valeur)],
    ]
    
    if facture.date_echeance:
        info_data.append([Paragraph("<b>Date échéance</b>", style_label), Paragraph(facture.date_echeance.strftime('%d/%m/%Y'), style_valeur)])
    
    info_table = Table(info_data, colWidths=[3.2*cm, 3.8*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor('#d1d5db'), spaceAfter=4, spaceBefore=4))
    
    # ==================== INFORMATIONS CLIENT ====================
    elements.append(Paragraph("<b>👤 INFORMATIONS CLIENT</b>", style_label))
    
    client_data = [
        [Paragraph("<b>Nom</b>", style_label), Paragraph(facture.personne_nom or "-", style_valeur)],
    ]
    
    if facture.personne_telephone:
        client_data.append([Paragraph("<b>Téléphone</b>", style_label), Paragraph(facture.personne_telephone, style_valeur)])
    
    client_table = Table(client_data, colWidths=[3.2*cm, 3.8*cm])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(client_table)
    
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor('#d1d5db'), spaceAfter=4, spaceBefore=4))
    
    # ==================== DÉTAIL DE LA FACTURE ====================
    elements.append(Paragraph("<b>📋 DÉTAIL DE LA FACTURE</b>", style_label))
    
    # Tableau des lignes de détail
    detail_data = [
        [Paragraph("<b>Désignation</b>", style_label), Paragraph("<b>Montant</b>", style_valeur)],
        [Paragraph("Prestation de service", style_info), Paragraph(f"{facture.montant_total:,.0f} FCFA", style_valeur)],
    ]
    
    if facture.description:
        detail_data.insert(2, [Paragraph(facture.description[:50], style_info), Paragraph("", style_valeur)])
    
    detail_table = Table(detail_data, colWidths=[4.5*cm, 2.5*cm])
    detail_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, 0), 0.5, colors.HexColor('#d1d5db')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(detail_table)
    
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor('#d1d5db'), spaceAfter=4, spaceBefore=4))
    
    # ==================== RÉCAPITULATIF FINANCIER (sans TVA ni RESTE À PAYER) ====================
    recap_data = [
        [Paragraph("<b>Montant total</b>", style_label), Paragraph(f"{facture.montant_total:,.0f} FCFA", style_valeur)],
    ]
    
    if facture.montant_paye > 0:
        recap_data.append([Paragraph("<b>Montant payé</b>", style_label), Paragraph(f"{facture.montant_paye:,.0f} FCFA", style_valeur)])
    
    recap_table = Table(recap_data, colWidths=[4.5*cm, 2.5*cm])
    recap_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(recap_table)
    
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#0f766e'), spaceAfter=4, spaceBefore=4))
    
    # ==================== STATUT ====================
   
    
    # ==================== QR CODE (POUR PAIEMENT RAPIDE) ====================
    try:
        # Génération du QR code avec les infos de la facture
        qr_data = f"FACTURE:{facture.numero}|MONTANT:{facture.montant_total - facture.montant_paye}|CLIENT:{facture.personne_nom}"
        qr = qrcode.QRCode(version=1, box_size=2, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#0f766e", back_color="white")
        
        # Convertir en bytes pour ReportLab
        qr_bytes = BytesIO()
        qr_img.save(qr_bytes, format='PNG')
        qr_bytes.seek(0)
        qr_reader = ImageReader(qr_bytes)
        
        # Ajouter le QR code
        from reportlab.platypus import Image
        qr_image = Image(qr_reader, width=1.5*cm, height=1.5*cm)
        qr_image.hAlign = 'CENTER'
        elements.append(Spacer(1, 4))
        elements.append(qr_image)
        elements.append(Paragraph("Scannez pour régler", style_footer))
    except Exception:
        pass  # Si erreur QR code, on continue sans
    
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor('#d1d5db'), spaceAfter=4, spaceBefore=4))
    
    # ==================== PIED DE PAGE ====================
    elements.append(Paragraph("Merci de votre confiance !", style_footer))
    
    elements.append(Paragraph("Conservez ce ticket comme justificatif", style_footer))
    
    # Construction du PDF
    doc.build(elements)
    return response

def supprimer_facture(request, facture_id):
    print(f"=== Tentative de suppression de la facture {facture_id} par {request.user} ===")
    
    try:
        from transactions.models import Facture
        print("Modèle Facture importé")
        
        facture = Facture.objects.get(id=facture_id)
        print(f"Facture trouvée: {facture.numero}")
        
        facture.delete()
        print("Facture supprimée avec succès")
        
        return JsonResponse({
            'success': True,
            'message': 'Facture supprimée avec succès'
        })
        
    except Facture.DoesNotExist:
        print(f"Facture {facture_id} non trouvée")
        return JsonResponse({
            'success': False,
            'error': f'Facture avec ID {facture_id} non trouvée'
        }, status=404)
    except Exception as e:
        print(f"Erreur: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
