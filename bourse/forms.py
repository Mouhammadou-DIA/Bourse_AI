from django import forms
from .models import Alerte, Transaction, Action, UserProfile
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class AlerteForm(forms.ModelForm):
    class Meta:
        model   = Alerte
        fields  = ['action', 'type_alerte', 'seuil', 'notif_telegram',
                   'notif_email', 'desactiver_apres', 'message_perso']
        widgets = {
            'action':         forms.Select(attrs={'class': 'form-input'}),
            'type_alerte':    forms.Select(attrs={'class': 'form-input'}),
            'seuil':          forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'message_perso':  forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Message personnalisé (optionnel)'}),
            'notif_telegram': forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'notif_email':    forms.CheckboxInput(attrs={'class': 'toggle-input'}),
            'desactiver_apres':forms.CheckboxInput(attrs={'class': 'toggle-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action'].queryset = Action.objects.filter(actif=True).order_by('symbole')
        self.fields['seuil'].required  = False


class TransactionForm(forms.ModelForm):
    class Meta:
        model  = Transaction
        fields = ['action', 'type_op', 'quantite', 'prix_unitaire', 'frais']
        widgets = {
            'action':        forms.Select(attrs={
                'class': 'form-input',
                'style': 'appearance:none;cursor:pointer;'
            }),
            'type_op':       forms.Select(attrs={
                'class': 'form-input',
                'style': 'appearance:none;cursor:pointer;'
            }),
            'quantite':      forms.NumberInput(attrs={
                'class':       'form-input',
                'step':        '0.0001',
                'min':         '0',
                'placeholder': 'ex: 1.5',
            }),
            'prix_unitaire': forms.NumberInput(attrs={
                'class':       'form-input',
                'step':        '0.01',
                'min':         '0',
                'placeholder': 'ex: 247.99',
            }),
            'frais':         forms.NumberInput(attrs={
                'class':       'form-input',
                'step':        '0.01',
                'min':         '0',
                'value':       '0',
                'placeholder': '0.00',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action'].queryset  = Action.objects.filter(actif=True).order_by('symbole')
        self.fields['action'].empty_label = '-- Choisir une action --'
        self.fields['frais'].required   = False
        self.fields['frais'].initial    = 0

class ActionRechercheForm(forms.Form):
    symbole = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'ex: AAPL, GOOGL, BTC-USD',
            'autocomplete': 'off',
        })
    )

    def clean_symbole(self):
        return self.cleaned_data['symbole'].upper().strip()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model  = UserProfile
        fields = ['devise_affichage', 'theme_pref', 'bio', 'photo']
        widgets = {
            'devise_affichage': forms.Select(
                choices=[('USD','USD'), ('EUR','EUR'), ('XOF','XOF')],
                attrs={'class': 'form-input'}
            ),
            'theme_pref': forms.Select(
                choices=[('dark','Mode Sombre'), ('light','Mode Clair')],
                attrs={'class': 'form-input'}
            ),
            'bio':   forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'photo': forms.FileInput(attrs={'class': 'form-input'}),
        }


class TelegramLiaisonForm(forms.Form):
    chat_id = forms.CharField(
        max_length=50,
        label='Votre Telegram Chat ID',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Envoyer /start à @BourseAIBot pour obtenir votre ID',
        })
    )

class InscriptionForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'votre@email.com',
        })
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nom d\'utilisateur',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Mot de passe',
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirmer le mot de passe',
        })
        # Supprimer les messages d'aide par défaut
        self.fields['username'].help_text  = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''