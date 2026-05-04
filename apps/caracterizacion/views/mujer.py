"""Wizard público sector Mujer (PR-N12-3).

Atómico: 1 transacción que escribe a 2 tablas.

  1. Resuelve/crea la `Persona` (vía `obtener_o_crear_persona`).
  2. Resuelve/crea la `InformacionHogar` para esa persona:
       - Si la persona ya tenía hogar registrado → reusar (actualizando
         los campos del form).
       - Si no → crear nuevo.
  3. Crea/actualiza `CaracterizacionMujer` con:
       - `informacion_hogar_id` = id del hogar resuelto (UNIQUE).
       - `evento_id` = id del evento del QR.
       - `persona_id`.
       - Campos del wizard.

Si cualquier paso falla, la transacción hace rollback de todo.
"""
import logging

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.mujer import MujerForm
from apps.caracterizacion.models import CaracterizacionMujer, InformacionHogar
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona

logger = logging.getLogger(__name__)


def _obtener_o_crear_hogar(persona_id: int, datos: dict) -> InformacionHogar:
    """Reusa la fila de hogar existente para la persona o crea una nueva.

    Política N12 (sección Mujer): una persona tiene a lo sumo una
    InformacionHogar lógica. Si ya existe, actualizamos los campos
    enviados — la mujer puede haber cambiado de estado civil, hijos, etc.
    """
    hogar = InformacionHogar.objects.filter(persona_id=persona_id).order_by("id").first()
    if hogar is None:
        hogar = InformacionHogar(persona_id=persona_id)
    for k, v in datos.items():
        setattr(hogar, k, v)
    hogar.save()
    return hogar


def caracterizacion_mujer(request: HttpRequest, evento) -> HttpResponse:
    if request.method == "POST":
        form = MujerForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                with transaction.atomic():
                    persona, _ = obtener_o_crear_persona(
                        tipo_documento_codigo=cd["tipo_documento"].codigo,
                        numero_documento=cd["numero_documento"],
                        nombre1=cd["nombre1"],
                        apellido1=cd["apellido1"],
                        nombre2=cd.get("nombre2"),
                        apellido2=cd.get("apellido2"),
                    )

                    hogar = _obtener_o_crear_hogar(persona.id, {
                        "estado_civil_jefe_hogar_codigo": (
                            cd["estado_civil"].id if cd.get("estado_civil") else None
                        ),
                        "personas_hogar": cd.get("personas_hogar"),
                        "dependientes_economicos": cd.get("dependientes_economicos"),
                        "menores_cargo": cd.get("menores_cargo"),
                        "mayores_cargo": cd.get("mayores_cargo"),
                        "tiene_hijos": cd.get("tiene_hijos"),
                        "es_jefe": cd.get("es_jefe"),
                    })

                    CaracterizacionMujer.objects.create(
                        evento_id=evento.id,
                        persona_id=persona.id,
                        informacion_hogar_id=hogar.id,
                        sabe_leer_escribir=cd["sabe_leer_escribir"],
                        interes_formacion=cd["interes_formacion"],
                        formacion_esperada=(cd.get("formacion_esperada") or "").strip() or None,
                    )

                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento, "sector_label": "Mujer",
                })
            except Exception:
                logger.exception("Error guardando caracterización Mujer")
                messages.error(
                    request,
                    "Ocurrió un error al guardar tu información. Intenta de nuevo.",
                )
    else:
        form = MujerForm()

    return render(request, "caracterizacion/mujer.html", {
        "evento": evento, "form": form, "sector_label": "Mujer",
    })
