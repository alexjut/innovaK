from django import forms

from ..models import Evento


class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ["name", "starts_at", "ends_at", "votos_permitidos", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "starts_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "votos_permitidos": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "max": "20",
                "step": "1",
            }),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].required = True
        self.fields["starts_at"].required = True
        self.fields["ends_at"].required = True

        self.fields["name"].error_messages = {
            "required": "Debes escribir el nombre del evento.",
        }
        self.fields["starts_at"].error_messages = {
            "required": "Debes indicar la fecha y hora de inicio.",
        }
        self.fields["ends_at"].error_messages = {
            "required": "Debes indicar la fecha y hora de finalización.",
        }

        for field_name in ("starts_at", "ends_at"):
            value = self.initial.get(field_name)
            if value:
                try:
                    self.initial[field_name] = value.strftime("%Y-%m-%dT%H:%M")
                except Exception:
                    pass

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Debes escribir el nombre del evento.")
        return name

    def clean_votos_permitidos(self):
        v = self.cleaned_data.get("votos_permitidos") or 1
        if v < 1:
            raise forms.ValidationError("Debe ser al menos 1.")
        if v > 20:
            raise forms.ValidationError("Máximo 20 votos por persona.")
        return v

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")

        if not starts_at:
            self.add_error("starts_at", "Debes indicar la fecha y hora de inicio.")

        if not ends_at:
            self.add_error("ends_at", "Debes indicar la fecha y hora de finalización.")

        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error(
                "ends_at",
                "La fecha/hora de finalización debe ser mayor que la de inicio.",
            )

        return cleaned