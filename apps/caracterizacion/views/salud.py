"""Wizard público sector Salud (PR-N12-4) — último de los 6 wizards N12.

Atómico con firma cifrada en Mongo:

  1. Resuelve/crea Persona (vía obtener_o_crear_persona).
  2. Crea CaracterizacionSalud (sin firma_mongo_id aún).
  3. Sube la imagen de firma a Mongo cifrada usando
     `apps.documentos.services.mongo_storage.guardar()` con owner
     `{"tipo": "caracterizacion_salud", "caracterizacion_id": <id>, "campo": "firma"}`.
  4. UPDATE de la fila SQL con el `mongo_id` devuelto.

Si cualquier paso falla, la transacción hace rollback y la firma
queda huérfana en Mongo (best effort: documentado para limpieza
batch — patrón ya conocido de N16).

NOTA: el patrón es idéntico al usado en
`apps/banco_iniciativas/forms/inscripcion.py:435` (PR del Banco).
"""
import logging

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.caracterizacion.forms.salud import SaludForm
from apps.caracterizacion.models import CaracterizacionSalud
from apps.caracterizacion.services.funcionario_lookup import funcionario_actual_o_none
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona

logger = logging.getLogger(__name__)


def caracterizacion_salud(request: HttpRequest, evento=None) -> HttpResponse:
    if request.method == "POST":
        form = SaludForm(request.POST, request.FILES)
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
                    asegurar_beneficiario_persona(persona)  # PR-7

                    carac = CaracterizacionSalud.objects.create(
                        evento_id=evento.id if evento else None,
                        funcionario_id=funcionario_actual_o_none(request),
                        persona_id=persona.id,
                        estado_salud=(cd.get("estado_salud") or "").strip() or None,
                        condiciones_salud=(cd.get("condiciones_salud") or "").strip() or None,
                        requiere_apoyo=cd.get("requiere_apoyo"),
                        presenta_discapacidad=cd.get("presenta_discapacidad"),
                        tiene_certificado_discapacidad=cd.get("tiene_certificado_discapacidad"),
                        tiene_cuidador=cd.get("tiene_cuidador"),
                        usted_es_cuidador=cd.get("usted_es_cuidador"),
                        pertenece_organizacion_inclusiva=cd.get("pertenece_organizacion_inclusiva"),
                        tipo_poblacion_atendida=(cd.get("tipo_poblacion_atendida") or "").strip() or None,
                        firma_digital=bool(cd.get("firma_digital")),
                    )

                    # Subida de firma a Mongo (cifrada). Patrón Banco.
                    firma_archivo = cd.get("firma_imagen")
                    if firma_archivo:
                        from apps.documentos.services import mongo_storage
                        firma_archivo.seek(0)
                        blob = firma_archivo.read()
                        mongo_id = mongo_storage.guardar(
                            plaintext=blob,
                            mime=firma_archivo.content_type or "image/png",
                            owner={
                                "tipo": "caracterizacion_salud",
                                "caracterizacion_id": carac.id,
                                "campo": "firma",
                            },
                        )
                        carac.firma_mongo_id = mongo_id
                        carac.save(update_fields=["firma_mongo_id"])

                return render(request, "caracterizacion/exitoso.html", {
                    "evento": evento, "sector_label": "Salud",
                })
            except Exception:
                logger.exception("Error guardando caracterización Salud")
                messages.error(
                    request,
                    "Ocurrió un error al guardar tu información. Intenta de nuevo.",
                )
    else:
        form = SaludForm()

    return render(request, "caracterizacion/salud.html", {
        "evento": evento, "form": form, "sector_label": "Salud",
    })
