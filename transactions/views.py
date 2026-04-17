# transactions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal
import django.shortcuts
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import Admin, Agent, Caisse, Transaction, DemandeApprovisionnement, ApprovisionnementDirect
from .forms import (OrangeTransactionForm, WaveTransactionForm, 
                   MalitelTransactionForm, TelecelTransactionForm)

from django.contrib.auth import logout
from django.views.decorators.http import require_http_methods

def logout_view(request):
    """Vue personnalisée pour la déconnexion"""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')

@login_required
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
    
    # Sinon, rediriger vers login
    messages.error(request, 'Vous n\'avez pas de profil configuré.')
    return redirect('login')

@login_required
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
        
        # ========== AGENTS ==========
        agents = Agent.objects.filter(est_actif=True)
        total_agents = agents.count()
        
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
            'total_agents': total_agents,
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

@login_required
def dashboard_agent(request):
    """
    Tableau de bord pour l'AGENT
    - Voit son propre compte
    - Voit ses propres transactions
    - Peut faire des demandes d'approvisionnement
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
        
        # Vérifier si l'agent a une caisse
        if not caisse:
            messages.error(request, 'Votre caisse n\'est pas configurée.')
            return redirect('login')
        
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

@login_required
@require_http_methods(["POST"])
def demander_approvisionnement_api(request):
    """
    API pour les demandes d'approvisionnement (AJAX seulement)
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
    except Agent.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas configuré comme agent.'})
    
    type_echange = request.POST.get('type_echange')
    montant = request.POST.get('montant')
    motif = request.POST.get('motif', '')
    
    if not type_echange or not montant:
        return JsonResponse({'success': False, 'error': 'Veuillez remplir tous les champs'})
    
    try:
        montant = Decimal(montant)
    except:
        return JsonResponse({'success': False, 'error': 'Montant invalide'})
    
    if montant < 1000:
        return JsonResponse({'success': False, 'error': 'Le montant minimum est de 1000 FCFA'})
    
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
    
    # Créer la demande
    try:
        demande = DemandeApprovisionnement.objects.create(
            agent=agent,
            type_echange=type_echange,
            montant=montant,
            motif=motif,
            statut='en_attente'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Demande envoyée avec succès',
            'demande_id': demande.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def demander_approvisionnement(request):
    """
    Vue pour les requêtes normales (formulaire)
    """
    try:
        agent = Agent.objects.get(user=request.user)
        caisse = agent.user.caisse
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas configuré comme agent.')
        return redirect('login')
    
    if request.method == 'POST':
        type_echange = request.POST.get('type_echange')
        montant = request.POST.get('montant')
        motif = request.POST.get('motif', '')
        
        if not type_echange or not montant:
            messages.error(request, 'Veuillez remplir tous les champs')
            return redirect('dashboard_agent')
        
        try:
            montant = Decimal(montant)
        except:
            messages.error(request, 'Montant invalide')
            return redirect('dashboard_agent')
        
        # Vérifier le solde
        if type_echange == 'uv_to_cash' and montant > caisse.solde_uv:
            messages.error(request, f"Solde UV insuffisant. Solde actuel: {caisse.solde_uv:,.0f} FCFA")
            return redirect('dashboard_agent')
        elif type_echange == 'wave_to_cash' and montant > caisse.solde_wave:
            messages.error(request, f"Solde Wave insuffisant. Solde actuel: {caisse.solde_wave:,.0f} FCFA")
            return redirect('dashboard_agent')
        elif type_echange in ['cash_to_uv', 'cash_to_wave'] and montant > caisse.solde_cash:
            messages.error(request, f"Solde Cash insuffisant. Solde actuel: {caisse.solde_cash:,.0f} FCFA")
            return redirect('dashboard_agent')
        
        # Créer la demande
        demande = DemandeApprovisionnement.objects.create(
            agent=agent,
            type_echange=type_echange,
            montant=montant,
            motif=motif,
            statut='en_attente'
        )
        
        messages.success(request, f'✅ Demande envoyée! {montant:,.0f} FCFA')
        return redirect('dashboard_agent')
    
    context = {
        'title': 'Demander un approvisionnement',
        'agent': agent,
        'caisse': caisse,
    }
    return render(request, 'transactions/demande_approvisionnement.html', context)

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal

@login_required
def transaction_user(request, operateur, type_transaction):
    """
    Transaction pour l'utilisateur connecté (ADMIN ou AGENT)
    Vérifie les soldes avant d'effectuer la transaction
    Supporte les requêtes AJAX pour le modal de confirmation
    """
    # Vérifier si c'est un ADMIN ou un AGENT
    is_admin = False
    try:
        admin = Admin.objects.get(user=request.user)
        is_admin = True
    except Admin.DoesNotExist:
        pass
    
    try:
        agent = Agent.objects.get(user=request.user)
    except Agent.DoesNotExist:
        if not is_admin:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas configuré.'})
            messages.error(request, 'Vous n\'êtes pas configuré.')
            return redirect('login')
    
    # Récupérer la caisse de l'utilisateur
    caisse = request.user.caisse
    
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
            
            # Créer et sauvegarder la transaction
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.type_transaction = type_transaction
            transaction.operateur = operateur
            
            try:
                transaction.save()
                
                # Réponse JSON pour AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'reference': transaction.reference,
                        'message': f'Transaction {operateur.capitalize()} effectuée avec succès!'
                    })
                
                messages.success(request, f'✅ Transaction {operateur.capitalize()} effectuée avec succès! Réf: {transaction.reference}')
                if is_admin:
                    return redirect('dashboard_admin')
                else:
                    return redirect('dashboard_agent')
                    
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
    
    context = {
        'title': f'{operateur.capitalize()} - {type_transaction.capitalize()}',
        'form': form,
        'type_transaction': type_transaction,
        'operateur': operateur,
        'is_admin': is_admin,
        'caisse': caisse,
    }
    return render(request, 'transactions/transaction_form.html', context)

@login_required
def demander_approvisionnement(request):
    """
    L'AGENT fait une demande d'approvisionnement
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
    
    # Détecter si c'est une requête AJAX
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    # Pré-sélection du type depuis l'URL
    type_preset = request.GET.get('type', '')
    
    if request.method == 'POST':
        type_echange = request.POST.get('type_echange')
        montant = request.POST.get('montant')
        motif = request.POST.get('motif', '')
        
        if not type_echange or not montant:
            error_msg = 'Veuillez remplir tous les champs correctement.'
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
        
        # Créer la demande
        try:
            demande = DemandeApprovisionnement.objects.create(
                agent=agent,
                type_echange=type_echange,
                montant=montant,
                motif=motif,
                statut='en_attente'
            )
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Demande envoyée avec succès',
                    'demande_id': demande.id
                })
            
            messages.success(request, f'✅ Demande envoyée! {montant:,.0f} FCFA - {demande.get_type_echange_display()}')
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
    }
    return render(request, 'transactions/demande_approvisionnement.html', context)

@login_required
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
            if demande.valider(admin):
                messages.success(request, f'✅ Demande validée! {demande.montant:,.0f} FCFA échangés.')
                print(f"Validation réussie - Nouveau statut: {demande.statut}")
            else:
                messages.error(request, '❌ Solde insuffisant pour valider cette demande.')
                print("Échec de la validation - Solde insuffisant")
        
        elif action == 'refuser':
            demande.statut = 'refuse'
            demande.traite_par = admin
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

@login_required
def impression_recu(request, transaction_id):
    """
    Imprimer le reçu d'une transaction
    """
    transaction = django.shortcuts.get_object_or_404(Transaction, reference=transaction_id)
    context = {
        'transaction': transaction,
        'date_impression': datetime.now()
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
    agent_id = request.GET.get('agent')
    
    transactions = Transaction.objects.all()
    
    if agent_id:
        transactions = transactions.filter(user_id=agent_id)
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
        # Sérialiser les transactions
        transactions_data = []
        for t in transactions_page:
            # Déterminer le type d'utilisateur
            if hasattr(t.user, 'admin_profile'):
                user_type = 'admin'
                user_name = t.user.admin_profile.nom
            elif hasattr(t.user, 'agent_profile'):
                user_type = 'agent'
                user_name = t.user.agent_profile.nom
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
            })
        
        # Calcul des pages pour l'affichage
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
    
    # ========== RENDU NORMAL (première charge) ==========
    context = {
        'title': 'Historique des transactions',
        'transactions': transactions_page,
        'total_entree': total_entree,
        'total_sortie': total_sortie,
        'total_commission': total_commission,
        'agents': Agent.objects.filter(est_actif=True),
    }
    return render(request, 'transactions/historique_admin.html', context)

from django.utils import timezone
from datetime import datetime

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

@login_required
def historique_agent(request):
    """
    Historique des transactions pour l'AGENT (ses propres transactions)
    Avec filtres par date, opérateur et type
    Affiche par défaut les transactions du jour
    """
    try:
        agent = Agent.objects.get(user=request.user)
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    # Récupérer toutes les transactions de l'agent
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    
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
    
    # ========== CALCUL DES TOTAUX (APRES FILTRES) ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    total_commission = transactions.aggregate(Sum('commission'))['commission__sum'] or 0
    
    # ========== PAGINATION ==========
    page = request.GET.get('page', 1)
    paginator = Paginator(transactions, 10)
    
    try:
        transactions_page = paginator.page(page)
    except PageNotAnInteger:
        transactions_page = paginator.page(1)
    except EmptyPage:
        transactions_page = paginator.page(paginator.num_pages)
    
    context = {
        'title': 'Mes transactions',
        'agent': agent,
        'transactions': transactions_page,
        'total_entree': total_entree,
        'total_sortie': total_sortie,
        'total_commission': total_commission,
        'date_debut': date_debut_display,
        'date_fin': date_fin_display,
    }
    return render(request, 'transactions/historique_agent.html', context)


@login_required
def exporter_historique_agent(request, format_type):
    """
    Exporte les transactions de l'agent avec les filtres appliqués
    Inclut les soldes, variations et demandes
    format_type: 'csv' ou 'excel'
    """
    try:
        agent = Agent.objects.get(user=request.user)
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    # Récupérer les dates du filtre
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')
    
    # Définir la période à analyser
    if date_debut_str and date_fin_str:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            date_debut = timezone.now().date()
            date_fin = timezone.now().date()
    else:
        # Par défaut: aujourd'hui
        date_debut = timezone.now().date()
        date_fin = timezone.now().date()
    
    # Vérifier que date_debut <= date_fin
    if date_debut > date_fin:
        date_debut, date_fin = date_fin, date_debut
    
    # Date du jour pour le nom du fichier
    today = timezone.now().date()
    
    # Date de la veille pour calculer solde hier
    date_hier = date_debut - timedelta(days=1)
    
    # Récupérer la caisse de l'agent
    caisse = agent.user.caisse
    
    # Récupérer les transactions pour la période (date__date__range)
    transactions = Transaction.objects.filter(
        user=request.user,
        date__date__range=[date_debut, date_fin]
    ).order_by('-date')
    
    # Récupérer les demandes pour la période
    demandes = DemandeApprovisionnement.objects.filter(
        agent=agent,
        date_demande__date__range=[date_debut, date_fin]
    ).order_by('-date_demande')
    
    # Récupérer les transactions avant la période (jusqu'à la veille inclus)
    transactions_avant = Transaction.objects.filter(
        user=request.user,
        date__date__lte=date_hier
    )
    
    # ========== CALCUL DES TOTAUX POUR LA PÉRIODE ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    
    # ========== CALCUL DES SOLDES ==========
    
    # 1. Calculer les soldes à HIER (avant la période)
    cash_depot_avant = transactions_avant.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_avant = transactions_avant.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_avant = cash_depot_avant - cash_retrait_avant
    
    uv_depot_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_retrait_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_credit_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='credit'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_uv_avant = uv_retrait_avant - uv_depot_avant - uv_credit_avant
    
    wave_depot_avant = transactions_avant.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_avant = transactions_avant.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_avant = wave_retrait_avant - wave_depot_avant
    
    # Solde à HIER (avant la période)
    solde_cash_hier = caisse.solde_cash - variation_cash_avant
    solde_uv_hier = caisse.solde_uv - variation_uv_avant
    solde_wave_hier = caisse.solde_wave - variation_wave_avant
    
    # 2. Calculer les variations PENDANT la période
    cash_depot_periode = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_periode = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_periode = cash_depot_periode - cash_retrait_periode
    
    uv_depot_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_retrait_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_credit_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='credit'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_uv_periode = uv_retrait_periode - uv_depot_periode - uv_credit_periode
    
    wave_depot_periode = transactions.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_periode = transactions.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_periode = wave_retrait_periode - wave_depot_periode
    
    # Solde à la FIN de la période
    solde_cash_fin = solde_cash_hier + variation_cash_periode
    solde_uv_fin = solde_uv_hier + variation_uv_periode
    solde_wave_fin = solde_wave_hier + variation_wave_periode
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="historique_{today.strftime("%Y%m%d")}.csv"'
        
        response.write('\ufeff')
        writer = csv.writer(response)
        
        # En-tête principal
        writer.writerow([f"HISTORIQUE COMPLET - {agent.nom}"])
        writer.writerow([f"Période: du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"])
        writer.writerow([f"Date d'export: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([])
        
        # SOLDES
        writer.writerow(["=== SOLDES ==="])
        writer.writerow(["Compte", f"Solde au {date_hier.strftime('%d/%m/%Y')}", f"Solde au {date_fin.strftime('%d/%m/%Y')}", "Variation"])
        writer.writerow(["Argent Cash", f"{solde_cash_hier:,.0f} FCFA", f"{solde_cash_fin:,.0f} FCFA", f"{variation_cash_periode:+,.0f} FCFA"])
        writer.writerow(["UV Touspiont", f"{solde_uv_hier:,.0f} FCFA", f"{solde_uv_fin:,.0f} FCFA", f"{variation_uv_periode:+,.0f} FCFA"])
        writer.writerow(["UV Wave", f"{solde_wave_hier:,.0f} FCFA", f"{solde_wave_fin:,.0f} FCFA", f"{variation_wave_periode:+,.0f} FCFA"])
        writer.writerow([])
        
        # TOTAUX TRANSACTIONS
        writer.writerow(["=== TOTAUX DES TRANSACTIONS ==="])
        writer.writerow([f"Total Entrées (Dépôts)", f"{total_entree:,.0f} FCFA"])
        writer.writerow([f"Total Sorties (Retraits)", f"{total_sortie:,.0f} FCFA"])
        writer.writerow(["Nombre de transactions", transactions.count()])
        writer.writerow([])
        
        # DEMANDES
        writer.writerow(["=== DEMANDES D'APPROVISIONNEMENT ==="])
        writer.writerow(["Date", "Type", "Montant", "Statut", "Motif"])
        for d in demandes:
            writer.writerow([
                d.date_demande.strftime('%d/%m/%Y %H:%M'),
                d.get_type_echange_display(),
                f"{d.montant:,.0f} FCFA",
                d.get_statut_display(),
                d.motif or ""
            ])
        writer.writerow([])
        
        # DETAIL DES TRANSACTIONS
        writer.writerow(["=== DETAIL DES TRANSACTIONS ==="])
        writer.writerow(['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Date'])
        
        for t in transactions:
            writer.writerow([
                t.reference,
                t.get_type_transaction_display(),
                t.get_operateur_display(),
                t.numero_client,
                f"{t.montant:,.0f}",
                t.date.strftime('%d/%m/%Y %H:%M:%S')
            ])
        
        return response
    
    elif format_type == 'excel':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="historique_{today.strftime("%Y%m%d")}.xlsx"'
        
        wb = Workbook()
        
        # Styles
        title_font = Font(bold=True, size=14)
        header_font = Font(bold=True, size=12)
        center_align = Alignment(horizontal='center')
        
        # ========== FEUILLE 1: RÉCAPITULATIF ==========
        ws_summary = wb.active
        ws_summary.title = "Récapitulatif"
        
        ws_summary.merge_cells('A1:D1')
        ws_summary['A1'] = f"HISTORIQUE COMPLET - {agent.nom}"
        ws_summary['A1'].font = title_font
        ws_summary['A1'].alignment = center_align
        
        ws_summary['A2'] = f"Période: du {date_debut.strftime('%d/%m/%Y')} au {date_fin.strftime('%d/%m/%Y')}"
        ws_summary['A3'] = f"Date d'export: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        # Soldes
        ws_summary['A5'] = "SOLDES"
        ws_summary['A5'].font = header_font
        ws_summary['A6'] = "Compte"
        ws_summary['B6'] = f"Solde au {date_hier.strftime('%d/%m/%Y')}"
        ws_summary['C6'] = f"Solde au {date_fin.strftime('%d/%m/%Y')}"
        ws_summary['D6'] = "Variation"
        
        for col in range(1, 5):
            ws_summary.cell(row=6, column=col).font = header_font
            ws_summary.cell(row=6, column=col).alignment = center_align
        
        soldes_data = [
            ["Argent Cash", f"{solde_cash_hier:,.0f} FCFA", f"{solde_cash_fin:,.0f} FCFA", f"{variation_cash_periode:+,.0f} FCFA"],
            ["UV Touspiont", f"{solde_uv_hier:,.0f} FCFA", f"{solde_uv_fin:,.0f} FCFA", f"{variation_uv_periode:+,.0f} FCFA"],
            ["UV Wave", f"{solde_wave_hier:,.0f} FCFA", f"{solde_wave_fin:,.0f} FCFA", f"{variation_wave_periode:+,.0f} FCFA"],
        ]
        
        for row, data in enumerate(soldes_data, 7):
            for col, val in enumerate(data, 1):
                ws_summary.cell(row=row, column=col, value=val)
        
        # Totaux transactions
        ws_summary['A11'] = "TOTAUX DES TRANSACTIONS"
        ws_summary['A11'].font = header_font
        ws_summary['A12'] = "Total Entrées (Dépôts)"
        ws_summary['B12'] = f"{total_entree:,.0f} FCFA"
        ws_summary['A13'] = "Total Sorties (Retraits)"
        ws_summary['B13'] = f"{total_sortie:,.0f} FCFA"
        ws_summary['A14'] = "Nombre de transactions"
        ws_summary['B14'] = transactions.count()
        
        # Stats des demandes
        ws_summary['A16'] = "STATISTIQUES DES DEMANDES"
        ws_summary['A16'].font = header_font
        ws_summary['A17'] = "En attente"
        ws_summary['B17'] = demandes.filter(statut='attente').count()
        ws_summary['A18'] = "Validées"
        ws_summary['B18'] = demandes.filter(statut='valide').count()
        ws_summary['A19'] = "Refusées"
        ws_summary['B19'] = demandes.filter(statut='refuse').count()
        
        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 25
        ws_summary.column_dimensions['C'].width = 25
        ws_summary.column_dimensions['D'].width = 20
        
        # ========== FEUILLE 2: DEMANDES ==========
        ws_demandes = wb.create_sheet("Demandes")
        
        headers_demandes = ['Date', 'Type', 'Montant', 'Statut', 'Motif']
        for col, header in enumerate(headers_demandes, 1):
            cell = ws_demandes.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, d in enumerate(demandes, 2):
            ws_demandes.cell(row=row, column=1, value=d.date_demande.strftime('%d/%m/%Y %H:%M'))
            ws_demandes.cell(row=row, column=2, value=d.get_type_echange_display())
            ws_demandes.cell(row=row, column=3, value=f"{d.montant:,.0f} FCFA")
            ws_demandes.cell(row=row, column=4, value=d.get_statut_display())
            ws_demandes.cell(row=row, column=5, value=d.motif or "")
        
        for col in range(1, 6):
            ws_demandes.column_dimensions[chr(64 + col)].width = 20
        
        # ========== FEUILLE 3: TRANSACTIONS ==========
        ws_trans = wb.create_sheet("Transactions")
        
        headers_trans = ['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Date']
        for col, header in enumerate(headers_trans, 1):
            cell = ws_trans.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, t in enumerate(transactions, 2):
            ws_trans.cell(row=row, column=1, value=t.reference)
            ws_trans.cell(row=row, column=2, value=t.get_type_transaction_display())
            ws_trans.cell(row=row, column=3, value=t.get_operateur_display())
            ws_trans.cell(row=row, column=4, value=t.numero_client)
            ws_trans.cell(row=row, column=5, value=float(t.montant))
            ws_trans.cell(row=row, column=6, value=t.date.strftime('%d/%m/%Y %H:%M:%S'))
        
        # Format des nombres
        for row in range(2, transactions.count() + 2):
            ws_trans.cell(row=row, column=5).number_format = '#,##0'
        
        for col in range(1, 7):
            ws_trans.column_dimensions[chr(64 + col)].width = 18
        
        wb.save(response)
        return response
    
    return None
@login_required
def historique_demandes_agent(request):
    """
    Historique des demandes d'approvisionnement pour l'AGENT
    """
    try:
        agent = Agent.objects.get(user=request.user)
    except Agent.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    demandes = DemandeApprovisionnement.objects.filter(agent=agent).order_by('-date_demande')
    
    context = {
        'title': 'Historique des demandes',
        'demandes': demandes,
    }
    return render(request, 'transactions/historique_demandes.html', context)

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
def gestion_agents(request):
    """
    Page de gestion des agents
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Vous n\'êtes pas autorisé.')
        return redirect('login')
    
    agents = Agent.objects.all().order_by('-created_at')
    
    # Compter les agents actifs et inactifs
    agents_actifs = agents.filter(est_actif=True).count()
    agents_inactifs = agents.filter(est_actif=False).count()
    
    context = {
        'title': 'Gestion des agents',
        'agents': agents,
        'agents_actifs': agents_actifs,
        'agents_inactifs': agents_inactifs,
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
def modifier_caisse(request):
    """
    Modifier les soldes de la caisse d'un agent
    """
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Non autorisé'})
    
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')
        solde_cash = request.POST.get('solde_cash')
        solde_uv = request.POST.get('solde_uv')
        solde_wave = request.POST.get('solde_wave')
        
        try:
            agent = Agent.objects.get(id=agent_id)
            caisse = agent.user.caisse
            
            if solde_cash is not None:
                caisse.solde_cash = Decimal(solde_cash)
            if solde_uv is not None:
                caisse.solde_uv = Decimal(solde_uv)
            if solde_wave is not None:
                caisse.solde_wave = Decimal(solde_wave)
            
            caisse.save()
            messages.success(request, f'✅ Caisse de "{agent.nom}" mise à jour avec succès.')
        except Agent.DoesNotExist:
            messages.error(request, 'Agent non trouvé.')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
        
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
    
    agent = django.shortcuts.get_object_or_404(Agent, id=agent_id)
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
    # Si les soldes d'hier sont déjà stockés, on les utilise
    if caisse.last_balance_update == today:
        solde_cash_hier = caisse.solde_cash_hier
        solde_uv_hier = caisse.solde_uv_hier
        solde_wave_hier = caisse.solde_wave_hier
    else:
        # Calculer les soldes d'hier
        solde_cash_hier = caisse.solde_cash - variation_cash_today
        solde_uv_hier = caisse.solde_uv - variation_uv_today
        solde_wave_hier = caisse.solde_wave - variation_wave_today
        
        # Stocker pour les prochaines fois
        caisse.solde_cash_hier = solde_cash_hier
        caisse.solde_uv_hier = solde_uv_hier
        caisse.solde_wave_hier = solde_wave_hier
        caisse.last_balance_update = today
        caisse.save()
    
    # Évolution (pour affichage)
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
    
    # ========== DEMANDES ==========
    show_all_demandes = request.GET.get('show_all_demandes')
    demandes = DemandeApprovisionnement.objects.filter(agent=agent).order_by('-date_demande')
    
    if not show_all_demandes:
        demandes = demandes.filter(date_demande__date=today)
    
    total_demandes = demandes.count()
    
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
        'demandes': demandes,
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
    }
    return render(request, 'transactions/detail_agent.html', context)

def export_transactions(transactions, agent, caisse, total_entree, total_sortie, total_commission, demandes, format_type):
    """
    Exporte les transactions, demandes et soldes au format CSV ou Excel
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # Calcul des soldes d'hier
    transactions_today = Transaction.objects.filter(user=agent.user, date__date=today)
    
    cash_depot_today = transactions_today.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_today = transactions_today.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_today = cash_depot_today - cash_retrait_today
    
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
    variation_uv_today = uv_retrait_today - uv_depot_today - uv_credit_today
    
    wave_depot_today = transactions_today.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_today = transactions_today.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_today = wave_retrait_today - wave_depot_today
    
    solde_cash_hier = caisse.solde_cash - variation_cash_today
    solde_uv_hier = caisse.solde_uv - variation_uv_today
    solde_wave_hier = caisse.solde_wave - variation_wave_today
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="rapport_{agent.nom}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
        
        writer = csv.writer(response)
        
        # En-tête principal
        writer.writerow([f"RAPPORT DETAILLE - {agent.nom}"])
        writer.writerow([f"Date d'export: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([])
        
        # SOLDES
        writer.writerow(["=== SOLDES ==="])
        writer.writerow(["Compte", "Solde actuel", "Solde hier", "Variation"])
        writer.writerow(["Argent Cash", f"{caisse.solde_cash:,.0f} FCFA", f"{solde_cash_hier:,.0f} FCFA", f"{caisse.solde_cash - solde_cash_hier:+,.0f} FCFA"])
        writer.writerow(["UV Touspiont", f"{caisse.solde_uv:,.0f} FCFA", f"{solde_uv_hier:,.0f} FCFA", f"{caisse.solde_uv - solde_uv_hier:+,.0f} FCFA"])
        writer.writerow(["UV Wave", f"{caisse.solde_wave:,.0f} FCFA", f"{solde_wave_hier:,.0f} FCFA", f"{caisse.solde_wave - solde_wave_hier:+,.0f} FCFA"])
        writer.writerow([])
        
        # TOTAUX TRANSACTIONS
        writer.writerow(["=== TOTAUX DES TRANSACTIONS ==="])
        writer.writerow(["Total Entrées", f"{total_entree:,.0f} FCFA"])
        writer.writerow(["Total Sorties", f"{total_sortie:,.0f} FCFA"])
        writer.writerow(["Total Commission", f"{total_commission:,.0f} FCFA"])
        writer.writerow(["Nombre de transactions", transactions.count()])
        writer.writerow([])
        
        # DEMANDES
        writer.writerow(["=== DEMANDES D'APPROVISIONNEMENT ==="])
        writer.writerow(["Date", "Type", "Montant", "Statut", "Motif"])
        for d in demandes:
            writer.writerow([
                d.date_demande.strftime('%d/%m/%Y %H:%M'),
                d.get_type_echange_display(),
                f"{d.montant:,.0f} FCFA",
                d.get_statut_display(),
                d.motif or ""
            ])
        writer.writerow([])
        
        # DETAIL DES TRANSACTIONS
        writer.writerow(["=== DETAIL DES TRANSACTIONS ==="])
        writer.writerow(['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Commission (FCFA)', 'Date'])
        
        for t in transactions:
            writer.writerow([
                t.reference,
                t.get_type_transaction_display(),
                t.get_operateur_display(),
                t.numero_client,
                f"{t.montant:,.0f}",
                f"{t.commission:,.0f}",
                t.date.strftime('%d/%m/%Y %H:%M:%S')
            ])
        
        return response
    
    elif format_type == 'excel':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="rapport_{agent.nom}_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx"'
        
        wb = Workbook()
        
        # Styles
        title_font = Font(bold=True, size=14)
        header_font = Font(bold=True, size=12)
        center_align = Alignment(horizontal='center')
        green_fill = PatternFill(start_color="10b981", end_color="10b981", fill_type="solid")
        blue_fill = PatternFill(start_color="6366f1", end_color="6366f1", fill_type="solid")
        
        # ========== FEUILLE 1: RÉCAPITULATIF ==========
        ws_summary = wb.active
        ws_summary.title = "Récapitulatif"
        
        ws_summary['A1'] = f"RAPPORT - {agent.nom}"
        ws_summary['A1'].font = title_font
        ws_summary['A2'] = f"Date d'export: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        # Soldes
        ws_summary['A4'] = "SOLDES"
        ws_summary['A4'].font = header_font
        ws_summary['A5'] = "Compte"
        ws_summary['B5'] = "Solde actuel"
        ws_summary['C5'] = "Solde hier"
        ws_summary['D5'] = "Variation"
        
        for col in range(1, 5):
            ws_summary.cell(row=5, column=col).font = header_font
        
        soldes_data = [
            ["Argent Cash", f"{caisse.solde_cash:,.0f} FCFA", f"{solde_cash_hier:,.0f} FCFA", f"{caisse.solde_cash - solde_cash_hier:+,.0f} FCFA"],
            ["UV Touspiont", f"{caisse.solde_uv:,.0f} FCFA", f"{solde_uv_hier:,.0f} FCFA", f"{caisse.solde_uv - solde_uv_hier:+,.0f} FCFA"],
            ["UV Wave", f"{caisse.solde_wave:,.0f} FCFA", f"{solde_wave_hier:,.0f} FCFA", f"{caisse.solde_wave - solde_wave_hier:+,.0f} FCFA"],
        ]
        
        for row, data in enumerate(soldes_data, 6):
            for col, val in enumerate(data, 1):
                ws_summary.cell(row=row, column=col, value=val)
        
        # Totaux transactions
        ws_summary['A10'] = "TOTAUX DES TRANSACTIONS"
        ws_summary['A10'].font = header_font
        ws_summary['A11'] = "Total Entrées"
        ws_summary['B11'] = f"{total_entree:,.0f} FCFA"
        ws_summary['A12'] = "Total Sorties"
        ws_summary['B12'] = f"{total_sortie:,.0f} FCFA"
        ws_summary['A13'] = "Total Commission"
        ws_summary['B13'] = f"{total_commission:,.0f} FCFA"
        ws_summary['A14'] = "Nombre de transactions"
        ws_summary['B14'] = transactions.count()
        
        ws_summary.column_dimensions['A'].width = 25
        ws_summary.column_dimensions['B'].width = 25
        ws_summary.column_dimensions['C'].width = 25
        ws_summary.column_dimensions['D'].width = 20
        
        # ========== FEUILLE 2: DEMANDES ==========
        ws_demandes = wb.create_sheet("Demandes")
        
        headers_demandes = ['Date', 'Type', 'Montant', 'Statut', 'Motif']
        for col, header in enumerate(headers_demandes, 1):
            cell = ws_demandes.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, d in enumerate(demandes, 2):
            ws_demandes.cell(row=row, column=1, value=d.date_demande.strftime('%d/%m/%Y %H:%M'))
            ws_demandes.cell(row=row, column=2, value=d.get_type_echange_display())
            ws_demandes.cell(row=row, column=3, value=f"{d.montant:,.0f} FCFA")
            ws_demandes.cell(row=row, column=4, value=d.get_statut_display())
            ws_demandes.cell(row=row, column=5, value=d.motif or "")
        
        for col in range(1, 6):
            ws_demandes.column_dimensions[chr(64 + col)].width = 20
        
        # ========== FEUILLE 3: TRANSACTIONS ==========
        ws_trans = wb.create_sheet("Transactions")
        
        headers_trans = ['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Commission (FCFA)', 'Date']
        for col, header in enumerate(headers_trans, 1):
            cell = ws_trans.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, t in enumerate(transactions, 2):
            ws_trans.cell(row=row, column=1, value=t.reference)
            ws_trans.cell(row=row, column=2, value=t.get_type_transaction_display())
            ws_trans.cell(row=row, column=3, value=t.get_operateur_display())
            ws_trans.cell(row=row, column=4, value=t.numero_client)
            ws_trans.cell(row=row, column=5, value=float(t.montant))
            ws_trans.cell(row=row, column=6, value=float(t.commission))
            ws_trans.cell(row=row, column=7, value=t.date.strftime('%d/%m/%Y %H:%M:%S'))
        
        for col in range(1, 8):
            ws_trans.column_dimensions[chr(64 + col)].width = 18
        
        wb.save(response)
        return response
    
    return None

from datetime import datetime, timedelta
from django.db.models import Sum
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

@login_required
def exporter_rapport_complet_agent(request, format_type):
    """
    Exporte un rapport complet: soldes, transactions, demandes
    Pour agent ou admin
    format_type: 'csv' ou 'excel'
    Prend en compte les filtres de date pour calculer les soldes
    """
    # Récupérer les dates du filtre (si présentes)
    date_debut_str = request.GET.get('date_debut')
    date_fin_str = request.GET.get('date_fin')
    
    # Définir la période à analyser
    if date_debut_str and date_fin_str:
        try:
            date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
        except ValueError:
            date_debut = timezone.now().date()
            date_fin = timezone.now().date()
    else:
        # Par défaut: aujourd'hui
        date_debut = timezone.now().date()
        date_fin = timezone.now().date()
    
    # Date du jour pour le nom du fichier
    today = timezone.now().date()
    
    # Date de la veille pour calculer solde hier
    date_hier = date_debut - timedelta(days=1)
    
    # Vérifier si l'utilisateur est un agent ou un admin
    if hasattr(request.user, 'agent'):
        # C'est un agent
        agent = request.user.agent
        caisse = agent.user.caisse
        user_type = "Agent"
        user_name = agent.nom
        
        # Récupérer les transactions de l'agent pour la période
        transactions = Transaction.objects.filter(
            user=request.user,
            date__date__gte=date_debut,
            date__date__lte=date_fin
        ).order_by('-date')
        
        # Récupérer les demandes de l'agent UNIQUEMENT pour la période
        demandes = DemandeApprovisionnement.objects.filter(
            agent=agent,
            date_demande__date__gte=date_debut,
            date_demande__date__lte=date_fin
        ).order_by('-date_demande')
        
        # Calculer les soldes à la date de début
        transactions_avant = Transaction.objects.filter(
            user=request.user,
            date__date__lt=date_debut
        )
        
    elif hasattr(request.user, 'admin_profile'):
        # C'est un admin
        admin = request.user.admin_profile
        caisse = request.user.caisse
        user_type = "Administrateur"
        user_name = admin.nom
        
        # Récupérer toutes les transactions pour la période
        transactions = Transaction.objects.filter(
            date__date__gte=date_debut,
            date__date__lte=date_fin
        ).order_by('-date')
        
        # Récupérer toutes les demandes pour la période
        demandes = DemandeApprovisionnement.objects.filter(
            date_demande__date__gte=date_debut,
            date_demande__date__lte=date_fin
        ).order_by('-date_demande')
        
        # Calculer les soldes à la date de début
        transactions_avant = Transaction.objects.filter(
            date__date__lt=date_debut
        )
        
    else:
        # Superutilisateur ou autre
        try:
            caisse = Caisse.objects.get(user=request.user)
            user_type = "Utilisateur"
            user_name = request.user.username
            transactions = Transaction.objects.filter(
                user=request.user,
                date__date__gte=date_debut,
                date__date__lte=date_fin
            ).order_by('-date')
            demandes = DemandeApprovisionnement.objects.filter(
                agent__user=request.user,
                date_demande__date__gte=date_debut,
                date_demande__date__lte=date_fin
            ).order_by('-date_demande')
            transactions_avant = Transaction.objects.filter(
                user=request.user,
                date__date__lt=date_debut
            )
        except:
            return HttpResponse("Impossible de générer le rapport. Données manquantes.", status=400)
    
    # ========== CALCUL DES TOTAUX POUR LA PÉRIODE ==========
    total_entree = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    total_sortie = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    
    # ========== CALCUL DES SOLDES ==========
    
    # 1. Calculer les soldes à HIER (avant la période)
    cash_depot_avant = transactions_avant.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_avant = transactions_avant.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_avant = cash_depot_avant - cash_retrait_avant
    
    uv_depot_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_retrait_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_credit_avant = transactions_avant.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='credit'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_uv_avant = uv_retrait_avant - uv_depot_avant - uv_credit_avant
    
    wave_depot_avant = transactions_avant.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_avant = transactions_avant.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_avant = wave_retrait_avant - wave_depot_avant
    
    # Solde à HIER (avant la période)
    solde_cash_hier = caisse.solde_cash - variation_cash_avant
    solde_uv_hier = caisse.solde_uv - variation_uv_avant
    solde_wave_hier = caisse.solde_wave - variation_wave_avant
    
    # 2. Calculer les variations PENDANT la période
    cash_depot_periode = transactions.filter(type_transaction='depot').aggregate(Sum('montant'))['montant__sum'] or 0
    cash_retrait_periode = transactions.filter(type_transaction='retrait').aggregate(Sum('montant'))['montant__sum'] or 0
    variation_cash_periode = cash_depot_periode - cash_retrait_periode
    
    uv_depot_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_retrait_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    uv_credit_periode = transactions.filter(
        operateur__in=['orange', 'malitel', 'telecel'],
        type_transaction='credit'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_uv_periode = uv_retrait_periode - uv_depot_periode - uv_credit_periode
    
    wave_depot_periode = transactions.filter(
        operateur='wave',
        type_transaction='depot'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    wave_retrait_periode = transactions.filter(
        operateur='wave',
        type_transaction='retrait'
    ).aggregate(Sum('montant'))['montant__sum'] or 0
    variation_wave_periode = wave_retrait_periode - wave_depot_periode
    
    # Solde à la FIN de la période
    solde_cash_fin = solde_cash_hier + variation_cash_periode
    solde_uv_fin = solde_uv_hier + variation_uv_periode
    solde_wave_fin = solde_wave_hier + variation_wave_periode
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        # Nom du fichier avec la date du jour
        response['Content-Disposition'] = f'attachment; filename="rapport_{today.strftime("%Y%m%d")}.csv"'
        
        # Ajouter BOM pour UTF-8
        response.write('\ufeff')
        writer = csv.writer(response)
        
        # En-tête principal (sans la ligne Période)
        writer.writerow([f"RAPPORT COMPLET - {user_name} ({user_type})"])
        writer.writerow([f"Date d'export: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"])
        writer.writerow([])
        
        # SOLDES
        writer.writerow(["=== SOLDES ==="])
        writer.writerow(["Compte", f"Solde au {date_hier.strftime('%d/%m/%Y')}", f"Solde au {date_fin.strftime('%d/%m/%Y')}", "Variation"])
        writer.writerow(["Argent Cash", f"{solde_cash_hier:,.0f} FCFA", f"{solde_cash_fin:,.0f} FCFA", f"{variation_cash_periode:+,.0f} FCFA"])
        writer.writerow(["UV Touspiont", f"{solde_uv_hier:,.0f} FCFA", f"{solde_uv_fin:,.0f} FCFA", f"{variation_uv_periode:+,.0f} FCFA"])
        writer.writerow(["UV Wave", f"{solde_wave_hier:,.0f} FCFA", f"{solde_wave_fin:,.0f} FCFA", f"{variation_wave_periode:+,.0f} FCFA"])
        writer.writerow([])
        
        # TOTAUX TRANSACTIONS
        writer.writerow(["=== TOTAUX DES TRANSACTIONS ==="])
        writer.writerow([f"Total Entrées (Dépôts)", f"{total_entree:,.0f} FCFA"])
        writer.writerow([f"Total Sorties (Retraits)", f"{total_sortie:,.0f} FCFA"])
        writer.writerow(["Nombre de transactions", transactions.count()])
        writer.writerow([])
        
        # DEMANDES
        writer.writerow(["=== DEMANDES D'APPROVISIONNEMENT ==="])
        writer.writerow(["Date", "Type", "Montant", "Statut", "Motif"])
        for d in demandes:
            writer.writerow([
                d.date_demande.strftime('%d/%m/%Y %H:%M'),
                d.get_type_echange_display(),
                f"{d.montant:,.0f} FCFA",
                d.get_statut_display(),
                d.motif or ""
            ])
        writer.writerow([])
        
        # DETAIL DES TRANSACTIONS
        writer.writerow(["=== DETAIL DES TRANSACTIONS ==="])
        writer.writerow(['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Date'])
        
        for t in transactions:
            writer.writerow([
                t.reference,
                t.get_type_transaction_display(),
                t.get_operateur_display(),
                t.numero_client,
                f"{t.montant:,.0f}",
                t.date.strftime('%d/%m/%Y %H:%M:%S')
            ])
        
        return response
    
    elif format_type == 'excel':
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        # Nom du fichier avec la date du jour
        response['Content-Disposition'] = f'attachment; filename="rapport_{today.strftime("%Y%m%d")}.xlsx"'
        
        wb = Workbook()
        
        # Styles
        title_font = Font(bold=True, size=14)
        header_font = Font(bold=True, size=12)
        center_align = Alignment(horizontal='center')
        
        # ========== FEUILLE 1: RÉCAPITULATIF ==========
        ws_summary = wb.active
        ws_summary.title = "Récapitulatif"
        
        ws_summary.merge_cells('A1:D1')
        ws_summary['A1'] = f"RAPPORT COMPLET - {user_name} ({user_type})"
        ws_summary['A1'].font = title_font
        ws_summary['A1'].alignment = center_align
        
        ws_summary['A2'] = f"Date d'export: {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}"
        
        # Soldes
        ws_summary['A4'] = "SOLDES"
        ws_summary['A4'].font = header_font
        ws_summary['A5'] = "Compte"
        ws_summary['B5'] = f"Solde au {date_hier.strftime('%d/%m/%Y')}"
        ws_summary['C5'] = f"Solde au {date_fin.strftime('%d/%m/%Y')}"
        ws_summary['D5'] = "Variation"
        
        for col in range(1, 5):
            ws_summary.cell(row=5, column=col).font = header_font
            ws_summary.cell(row=5, column=col).alignment = center_align
        
        soldes_data = [
            ["Argent Cash", f"{solde_cash_hier:,.0f} FCFA", f"{solde_cash_fin:,.0f} FCFA", f"{variation_cash_periode:+,.0f} FCFA"],
            ["UV Touspiont", f"{solde_uv_hier:,.0f} FCFA", f"{solde_uv_fin:,.0f} FCFA", f"{variation_uv_periode:+,.0f} FCFA"],
            ["UV Wave", f"{solde_wave_hier:,.0f} FCFA", f"{solde_wave_fin:,.0f} FCFA", f"{variation_wave_periode:+,.0f} FCFA"],
        ]
        
        for row, data in enumerate(soldes_data, 6):
            for col, val in enumerate(data, 1):
                ws_summary.cell(row=row, column=col, value=val)
        
        # Totaux transactions
        ws_summary['A10'] = "TOTAUX DES TRANSACTIONS"
        ws_summary['A10'].font = header_font
        ws_summary['A11'] = "Total Entrées (Dépôts)"
        ws_summary['B11'] = f"{total_entree:,.0f} FCFA"
        ws_summary['A12'] = "Total Sorties (Retraits)"
        ws_summary['B12'] = f"{total_sortie:,.0f} FCFA"
        ws_summary['A13'] = "Nombre de transactions"
        ws_summary['B13'] = transactions.count()
        
        # Stats des demandes
        ws_summary['A15'] = "STATISTIQUES DES DEMANDES"
        ws_summary['A15'].font = header_font
        ws_summary['A16'] = "En attente"
        ws_summary['B16'] = demandes.filter(statut='attente').count()
        ws_summary['A17'] = "Validées"
        ws_summary['B17'] = demandes.filter(statut='valide').count()
        ws_summary['A18'] = "Refusées"
        ws_summary['B18'] = demandes.filter(statut='refuse').count()
        
        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 25
        ws_summary.column_dimensions['C'].width = 25
        ws_summary.column_dimensions['D'].width = 20
        
        # ========== FEUILLE 2: DEMANDES ==========
        ws_demandes = wb.create_sheet("Demandes")
        
        headers_demandes = ['Date', 'Type', 'Montant', 'Statut', 'Motif']
        for col, header in enumerate(headers_demandes, 1):
            cell = ws_demandes.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, d in enumerate(demandes, 2):
            ws_demandes.cell(row=row, column=1, value=d.date_demande.strftime('%d/%m/%Y %H:%M'))
            ws_demandes.cell(row=row, column=2, value=d.get_type_echange_display())
            ws_demandes.cell(row=row, column=3, value=f"{d.montant:,.0f} FCFA")
            ws_demandes.cell(row=row, column=4, value=d.get_statut_display())
            ws_demandes.cell(row=row, column=5, value=d.motif or "")
        
        for col in range(1, 6):
            ws_demandes.column_dimensions[chr(64 + col)].width = 20
        
        # ========== FEUILLE 3: TRANSACTIONS ==========
        ws_trans = wb.create_sheet("Transactions")
        
        headers_trans = ['Référence', 'Type', 'Opérateur', 'Client', 'Montant (FCFA)', 'Date']
        for col, header in enumerate(headers_trans, 1):
            cell = ws_trans.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.alignment = center_align
        
        for row, t in enumerate(transactions, 2):
            ws_trans.cell(row=row, column=1, value=t.reference)
            ws_trans.cell(row=row, column=2, value=t.get_type_transaction_display())
            ws_trans.cell(row=row, column=3, value=t.get_operateur_display())
            ws_trans.cell(row=row, column=4, value=t.numero_client)
            ws_trans.cell(row=row, column=5, value=float(t.montant))
            ws_trans.cell(row=row, column=6, value=t.date.strftime('%d/%m/%Y %H:%M:%S'))
        
        # Format des nombres
        for row in range(2, transactions.count() + 2):
            ws_trans.cell(row=row, column=5).number_format = '#,##0'
        
        for col in range(1, 7):
            ws_trans.column_dimensions[chr(64 + col)].width = 18
        
        wb.save(response)
        return response
    
    return None