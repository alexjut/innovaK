from django import forms

from ..models import Candidato


CURUL_CHOICES = [
    ("", "Seleccione una curul"),

    # IDENTIDADES
    ("IDENTIDADES|LESBIANAS", "Identidades — Representante sector LESBIANAS"),
    ("IDENTIDADES|HOMBRES_GAY", "Identidades — Representante sector HOMBRES GAY"),
    ("IDENTIDADES|BISEXUALES", "Identidades — Representante sector BISEXUALES"),
    (
        "IDENTIDADES|TRANS",
        "Identidades — Representante sector TRANSGÉNERO / TRANSFORMISTA / TRAVESTI / TRANSEXUAL",
    ),
    ("IDENTIDADES|INTERSEXUAL", "Identidades — Representante sector INTERSEXUAL"),
    (
        "IDENTIDADES|IDENTIDADES_DIVERSAS",
        "Identidades — Representante sector PERSONAS CON ORIENTACIÓN SEXUAL E IDENTIDADES DIVERSAS",
    ),
    ("IDENTIDADES|BLANCO", "Identidades — VOTO EN BLANCO"),

    # DERECHOS
    ("DERECHOS|CULTURA_EDUCACION", "Derechos — Representante derecho Cultura y Educación"),
    ("DERECHOS|SALUD_TRABAJO", "Derechos — Representante derecho Salud y Trabajo"),
    ("DERECHOS|SEGURIDAD", "Derechos — Representante derecho Seguridad"),
    (
        "DERECHOS|RECREACION_INTEGRACION",
        "Derechos — Representante derecho Recreación e integración social",
    ),
    (
        "DERECHOS|AMBIENTE_ESPACIO_PUBLICO",
        "Derechos — Representante derecho Ambiente y Espacio Público",
    ),
    ("DERECHOS|BLANCO", "Derechos — VOTO EN BLANCO"),
]


class CandidatoForm(forms.ModelForm):
    genre = forms.ChoiceField(
        choices=CURUL_CHOICES,
        label="Curul",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Candidato
        fields = [
            "evento",
            "name",
            "genre",
            "photo",
            "bio",
            "is_active",
        ]
        widgets = {
            "evento": forms.Select(attrs={"class": "form-select"}),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre identitario",
                }
            ),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Perfil o propuesta (opcional)",
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "evento": "Votación",
            "name": "Nombre identitario",
            "photo": "Foto",
            "bio": "Perfil o propuesta",
            "is_active": "Candidatura activa",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Campo opcional
        self.fields["bio"].required = False

        # Orden amigable
        self.fields["evento"].queryset = self.fields["evento"].queryset.order_by("-created_at")

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("El nombre identitario es obligatorio.")
        return name

    def clean_genre(self):
        value = (self.cleaned_data.get("genre") or "").strip()
        if not value:
            raise forms.ValidationError("Debes seleccionar una curul.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        evento = cleaned_data.get("evento")
        curul = (cleaned_data.get("genre") or "").strip()

        if evento and curul:
            qs = Candidato.objects.filter(evento=evento, genre=curul)

            # excluir el mismo registro cuando se edita
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                self.add_error(
                    "genre",
                    "Ya existe una candidatura registrada para esta curul en esta votación."
                )

        return cleaned_data