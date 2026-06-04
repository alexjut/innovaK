"""Introspección de Django Forms → esquema JSON Angular-ready.

Recorre `form.fields` de cualquier `forms.Form` y produce una lista de
descriptores de campo neutrales al backend, para que UN wizard Angular
dinámico renderice los 6 sectores de caracterización sin hardcodear
nada por sector.

NO toca los forms — solo los introspecta. Si un form cambia (campo
nuevo, label distinto), el schema se actualiza solo.
"""
from __future__ import annotations

from django import forms


def _tipo_y_hint(field: forms.Field) -> tuple[str, str]:
    """Mapea (clase de field, widget) → (type, widget_hint) para Angular.

    `type` es el tipo lógico del control. `widget_hint` da una pista
    extra del widget Django (radio, textarea, etc.) por si el front
    quiere refinar el render.
    """
    widget = field.widget

    # Selects / opciones múltiples primero (ModelChoice hereda de ChoiceField).
    if isinstance(field, (forms.ModelMultipleChoiceField, forms.MultipleChoiceField)):
        return "multiselect", widget.__class__.__name__
    if isinstance(field, (forms.ModelChoiceField, forms.TypedChoiceField, forms.ChoiceField)):
        # TypedChoiceField con RadioSelect de 2 opciones es un bool sí/no,
        # pero lo exponemos como select con sus opciones reales para que
        # Angular decida si lo pinta radio o dropdown (widget_hint lo dice).
        return "select", widget.__class__.__name__

    if isinstance(field, (forms.ImageField, forms.FileField)):
        return "file", widget.__class__.__name__
    if isinstance(field, forms.BooleanField):
        return "checkbox", widget.__class__.__name__
    if isinstance(field, forms.EmailField):
        return "email", widget.__class__.__name__
    if isinstance(field, (forms.IntegerField, forms.DecimalField, forms.FloatField)):
        return "number", widget.__class__.__name__
    if isinstance(field, (forms.DateTimeField,)):
        return "datetime", widget.__class__.__name__
    if isinstance(field, (forms.DateField,)):
        return "date", widget.__class__.__name__

    # CharField y derivados: textarea si el widget lo es, si no text.
    if isinstance(widget, forms.Textarea):
        return "textarea", widget.__class__.__name__
    return "text", widget.__class__.__name__


def _opciones(field: forms.Field) -> list[dict] | None:
    """Devuelve [{value, label}] para selects/multiselects, o None."""
    choices = getattr(field, "choices", None)
    if choices is None:
        return None
    opciones = []
    for value, label in choices:
        # Saltar el placeholder vacío ("— Seleccionar —") — el front
        # lo agrega como prompt; aquí solo van opciones reales.
        if value == "" or value is None:
            continue
        opciones.append({"value": str(value), "label": str(label)})
    return opciones


def schema_de_form(form: forms.Form) -> list[dict]:
    """Recorre form.fields y devuelve la lista de descriptores de campo."""
    out = []
    for name, field in form.fields.items():
        tipo, widget_hint = _tipo_y_hint(field)
        descriptor = {
            "name": name,
            "label": str(field.label) if field.label else name,
            "type": tipo,
            "required": bool(field.required),
            "help_text": str(field.help_text) if field.help_text else "",
            "max_length": getattr(field, "max_length", None),
            "widget_hint": widget_hint,
        }
        if tipo in ("select", "multiselect"):
            descriptor["multiple"] = tipo == "multiselect"
            descriptor["options"] = _opciones(field) or []
        else:
            descriptor["multiple"] = False
        out.append(descriptor)
    return out
