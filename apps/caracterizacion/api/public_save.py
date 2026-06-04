"""Dispatcher de guardado para los wizards públicos de caracterización.

La API pública (POST) NO puede llamar a las views HTML legacy porque
estas renderizan templates. Por eso aquí vive un guardado por sector
que reproduce el bloque `with transaction.atomic(): ... .create(...)`
de cada `views/<sector>.py`. La cadena Persona→Beneficiario y los
servicios (`obtener_o_crear_persona`, `funcionario_actual_o_none`,
`mongo_storage`) son EXACTAMENTE los mismos que usan las views — no se
duplica lógica de negocio, solo el ensamblado del `.create()`.

Cada función recibe `(form_cleaned_data, evento_id, request)` y devuelve
el id de la fila creada.
"""
from __future__ import annotations

from django.db import transaction

from apps.caracterizacion.models import (
    CaracterizacionCultura,
    CaracterizacionDeporte,
    CaracterizacionMujer,
    CaracterizacionParticipacionCiudadana,
    CaracterizacionPoblacional,
    CaracterizacionSalud,
    InformacionHogar,
)
from apps.caracterizacion.services.funcionario_lookup import funcionario_actual_o_none
from apps.caracterizacion.services.persona_lookup import obtener_o_crear_persona
from apps.login.services.beneficiario_helpers import asegurar_beneficiario_persona


def _resolver_persona(cd, request):
    persona, _ = obtener_o_crear_persona(
        tipo_documento_codigo=cd["tipo_documento"].codigo,
        numero_documento=cd["numero_documento"],
        nombre1=cd["nombre1"],
        apellido1=cd["apellido1"],
        nombre2=cd.get("nombre2"),
        apellido2=cd.get("apellido2"),
    )
    asegurar_beneficiario_persona(persona)
    return persona, funcionario_actual_o_none(request)


def guardar_cultura(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
        nivel = cd.get("nivel_educativo")
        obj = CaracterizacionCultura.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
            persona_id=persona.id,
            nivel_educativo_codigo=nivel.codigo if nivel else None,
            documentacion_soporte=cd["documentacion_soporte"],
            motivacion_personal=(cd.get("motivacion_personal") or "").strip() or None,
        )
    return obj.id


def guardar_deporte(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
        nivel = cd.get("nivel_educativo")
        lugar = cd.get("lugar_incidencia")
        obj = CaracterizacionDeporte.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
            persona_id=persona.id,
            nivel_educativo_codigo=nivel.codigo if nivel else None,
            documentacion_soporte=cd["documentacion_soporte"],
            motivacion_personal=(cd.get("motivacion_personal") or "").strip() or None,
            lugar_incidencia_id=lugar.id if lugar else None,
        )
    return obj.id


def _obtener_o_crear_hogar(persona_id: int, datos: dict) -> InformacionHogar:
    hogar = InformacionHogar.objects.filter(persona_id=persona_id).order_by("id").first()
    if hogar is None:
        hogar = InformacionHogar(persona_id=persona_id)
    for k, v in datos.items():
        setattr(hogar, k, v)
    hogar.save()
    return hogar


def guardar_mujer(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
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
        obj = CaracterizacionMujer.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
            persona_id=persona.id,
            informacion_hogar_id=hogar.id,
            sabe_leer_escribir=cd["sabe_leer_escribir"],
            interes_formacion=cd["interes_formacion"],
            formacion_esperada=(cd.get("formacion_esperada") or "").strip() or None,
        )
    return obj.id


def guardar_poblacional(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
        obj = CaracterizacionPoblacional.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
            persona_id=persona.id,
            pertenencia_lgbti=cd["pertenencia_lgbti"],
            victima_conflicto=cd["victima_conflicto"],
            habitante_calle=cd["habitante_calle"],
            trabajador_sexual=cd["trabajador_sexual"],
            madre_cabeza_hogar=cd["madre_cabeza_hogar"],
            grupo_etareo=cd.get("grupo_etareo") or None,
            enfoque_diferencial=cd.get("enfoque_diferencial") or None,
        )
    return obj.id


def guardar_participacion(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
        obj = CaracterizacionParticipacionCiudadana.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
            persona_id=persona.id,
            condicion_poblacional=(cd.get("condicion_poblacional") or "").strip() or None,
            pertenece_organizacion=cd["pertenece_organizacion"],
            tipo_organizacion=(cd.get("tipo_organizacion") or "").strip() or None,
            es_funcionario=cd["es_funcionario"],
        )
    return obj.id


def guardar_salud(cd, evento_id, request) -> int:
    with transaction.atomic():
        persona, funcionario_id = _resolver_persona(cd, request)
        carac = CaracterizacionSalud.objects.create(
            evento_id=evento_id,
            funcionario_id=funcionario_id,
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
    return carac.id
