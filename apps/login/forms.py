from django import forms
from django.contrib.auth.models import Group
from apps.login.models.usuario import Usuario
from .models.sisben import Sisben

class SisbenForm(forms.ModelForm):
    class Meta:
        model = Sisben
        fields = ['tiene_sisben', 'nivel', 'puntaje']
        widgets = {
            'nivel': forms.TextInput(attrs={'class': 'form-control'}),
            'puntaje': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class UsuarioRegistroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")
    grupo = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, label="Grupo o Rol")

    class Meta:
        model = Usuario
        fields = ['username', 'password', 'grupo']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
