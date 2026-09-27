# transactions/forms.py
from urllib.parse import urlparse

from django import forms

from .models import Agent, Transaction, DemandeApprovisionnement


class TransactionForm(forms.ModelForm):
    """
    Formulaire de base pour les transactions
    """
    class Meta:
        model = Transaction
        fields = ['type_transaction', 'operateur', 'numero_client', 'nom_client', 'wave_qr_url', 'montant', 'notes']
        widgets = {
            'type_transaction': forms.HiddenInput(),
            'operateur': forms.HiddenInput(),
            'numero_client': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 70 00 00 00',
                'required': True
            }),
            'nom_client': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du client (optionnel)'
            }),
            'wave_qr_url': forms.HiddenInput(),
            'montant': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en FCFA',
                'min': 100,
                'step': 100,
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notes (optionnel)'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero_client'].required = True
    
    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant < 100:
            raise forms.ValidationError("Le montant minimum est de 100 FCFA")
        if montant > 1000000:
            raise forms.ValidationError("Le montant maximum est de 1 000 000 FCFA")
        return montant
    
    def clean_numero_client(self):
        numero = self.cleaned_data.get('numero_client')
        if numero:
            numero = ''.join(filter(str.isdigit, numero))
            if len(numero) < 8:
                raise forms.ValidationError("Numéro client invalide (minimum 8 chiffres)")
        return numero


class OrangeTransactionForm(TransactionForm):
    """
    Formulaire spécifique pour Orange Money
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operateur'].initial = 'orange'
        self.fields['type_transaction'].widget = forms.HiddenInput()


class WaveTransactionForm(TransactionForm):
    """
    Formulaire spécifique pour Wave
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operateur'].initial = 'wave'
        self.fields['type_transaction'].widget = forms.HiddenInput()
        self.fields['numero_client'].required = False

    def clean_wave_qr_url(self):
        qr_url = self.cleaned_data.get('wave_qr_url', '').strip()
        if not qr_url:
            return ''

        try:
            parsed = urlparse(qr_url)
            is_valid = (
                parsed.scheme == 'https'
                and parsed.hostname == 'qr.wave.com'
                and parsed.port is None
                and not parsed.username
                and not parsed.password
                and parsed.path not in ('', '/')
            )
        except ValueError:
            is_valid = False

        if not is_valid:
            raise forms.ValidationError("Le QR scanné n'est pas un lien Wave valide.")
        return qr_url

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('numero_client') and not cleaned_data.get('wave_qr_url'):
            raise forms.ValidationError("Scannez un QR Wave ou saisissez un numéro client.")
        return cleaned_data


class MalitelTransactionForm(TransactionForm):
    """
    Formulaire spécifique pour Malitel
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operateur'].initial = 'malitel'
        self.fields['type_transaction'].widget = forms.HiddenInput()


class TelecelTransactionForm(TransactionForm):
    """
    Formulaire spécifique pour Telecel
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operateur'].initial = 'telecel'
        self.fields['type_transaction'].widget = forms.HiddenInput()


class DemandeApprovisionnementForm(forms.ModelForm):
    """
    Formulaire pour les demandes d'approvisionnement (4 types d'échanges)
    """
    TYPE_ECHANGE_CHOICES = (
        ('uv_to_cash', '📱 UV → Cash (Échanger UV contre Cash)'),
        ('wave_to_cash', '💳 Wave → Cash (Échanger Wave contre Cash)'),
        ('cash_to_uv', '💰 Cash → UV (Acheter des UV avec Cash)'),
        ('cash_to_wave', '💰 Cash → Wave (Acheter du Wave avec Cash)'),
    )
    
    type_echange = forms.ChoiceField(
        choices=TYPE_ECHANGE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Type d'échange"
    )
    
    montant = forms.DecimalField(
        min_value=1000,
        max_value=1000000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 50000',
            'step': 1000,
            'min': 1000,
            'required': True
        }),
        label="Montant (FCFA)",
        help_text="Minimum: 1 000 FCFA"
    )
    
    motif = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Motif de la demande (optionnel)'
        }),
        label="Motif"
    )
    
    class Meta:
        model = DemandeApprovisionnement
        fields = ['type_echange', 'montant', 'motif']
    
    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant < 1000:
            raise forms.ValidationError("Le montant minimum est de 1 000 FCFA")
        if montant > 1000000:
            raise forms.ValidationError("Le montant maximum est de 1 000 000 FCFA")
        return montant
    
    def clean_type_echange(self):
        type_echange = self.cleaned_data.get('type_echange')
        valid_types = ['uv_to_cash', 'wave_to_cash', 'cash_to_uv', 'cash_to_wave']
        if type_echange not in valid_types:
            raise forms.ValidationError("Type d'échange invalide")
        return type_echange


class ApprovisionnementDirectForm(forms.Form):
    """
    Formulaire pour l'approvisionnement direct ADMIN → AGENT
    """
    TYPE_CHOICES = (
        ('cash', '💰 Cash'),
        ('uv', '📱 UV Touspiont'),
        ('wave', '💳 Wave'),
    )
    
    agent = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Agent"
    )
    
    type_approvisionnement = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Type d'approvisionnement"
    )
    
    montant = forms.DecimalField(
        min_value=1000,
        max_value=1000000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 50000',
            'step': 1000,
            'required': True
        }),
        label="Montant (FCFA)"
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Notes (optionnel)'
        }),
        label="Notes"
    )
    
    def __init__(self, *args, **kwargs):
        # Récupérer tous les agents actifs
        super().__init__(*args, **kwargs)
        self.fields['agent'].queryset = Agent.objects.filter(est_actif=True)
    
    def clean_montant(self):
        montant = self.cleaned_data.get('montant')
        if montant < 1000:
            raise forms.ValidationError("Le montant minimum est de 1 000 FCFA")
        return montant


class RapportForm(forms.Form):
    """
    Formulaire pour les rapports
    """
    PERIODE_CHOICES = (
        ('jour', 'Aujourd\'hui'),
        ('semaine', 'Cette semaine'),
        ('mois', 'Ce mois'),
        ('personnalise', 'Personnalisé'),
    )
    
    periode = forms.ChoiceField(
        choices=PERIODE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Période"
    )
    
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date début"
    )
    
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Date fin"
    )
    
    operateur = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Transaction.OPERATEUR_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Opérateur"
    )
    
    type_transaction = forms.ChoiceField(
        choices=[('', 'Tous')] + list(Transaction.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Type de transaction"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        periode = cleaned_data.get('periode')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if periode == 'personnalise' and (not date_debut or not date_fin):
            raise forms.ValidationError("Veuillez sélectionner une date de début et de fin")
        
        if date_debut and date_fin and date_debut > date_fin:
            raise forms.ValidationError("La date de début doit être antérieure à la date de fin")
        
        return cleaned_data