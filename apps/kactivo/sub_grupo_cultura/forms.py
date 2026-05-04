from django import forms
from apps.login.models.funcionario import Subgrupo, Dependencia  # M1: ya no duplicados en kactivo

CULTURA_NOMBRE = "Cultura"  # si cambia el nombre en DB, ajusta aquí

class SubgrupoCulturaForm(forms.ModelForm):
    class Meta:
        model = Subgrupo
        fields = ["nombre"]  # dependencia se fija a Cultura en la view

    def save(self, commit=True, *args, **kwargs):
        # fuerza la dependencia “Cultura”
        obj = super().save(commit=False, *args, **kwargs)
        try:
            dep = Dependencia.objects.get(nombre__iexact=CULTURA_NOMBRE)
        except Dependencia.DoesNotExist:
            raise forms.ValidationError(
                f"No existe la dependencia '{CULTURA_NOMBRE}' en la base de datos."
            )
        obj.dependencia = dep
        if commit:
            obj.save()
        return obj
