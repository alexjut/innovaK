"""Resolución de Persona en formularios públicos.

Política acordada en N12 (opción A): si una Persona ya existe en BD,
se reusa tal cual — los datos del form (nombre/apellido) NO sobreescriben
los registrados. Esto evita data drift por captura repetida con datos
ligeramente distintos (typos, mayúsculas, segundo apellido en blanco).

Si la Persona no existe, se crea con los datos mínimos del form en una
única transacción que también crea su PersonaDocumento.
"""
from typing import Optional

from django.db import transaction

from apps.login.models import Persona
from apps.login.models.persona_documento import PersonaDocumento, TipoDocumento


def buscar_persona_por_documento(numero_documento: str) -> Optional[Persona]:
    """Devuelve la Persona ya registrada para `numero_documento`, o None."""
    if not numero_documento:
        return None
    return (
        Persona.objects
        .filter(persona_documento__numero_documento=numero_documento)
        .first()
    )


@transaction.atomic
def obtener_o_crear_persona(
    *,
    tipo_documento_codigo: int,
    numero_documento: str,
    nombre1: str,
    apellido1: str,
    nombre2: Optional[str] = None,
    apellido2: Optional[str] = None,
) -> tuple[Persona, bool]:
    """Get-or-create idempotente.

    Política (a): si la Persona ya existe (vía PersonaDocumento.numero_documento),
    se devuelve sin tocar nombre1/apellido1. El form puede traer los datos pero
    se ignoran — la BD manda.

    Si no existe: crea PersonaDocumento si hace falta + Persona mínima.

    Devuelve (persona, fue_creada).
    """
    numero_documento = (numero_documento or "").strip()
    if not numero_documento:
        raise ValueError("numero_documento es obligatorio")

    persona_existente = buscar_persona_por_documento(numero_documento)
    if persona_existente is not None:
        return persona_existente, False

    persona_doc = PersonaDocumento.objects.filter(
        numero_documento=numero_documento
    ).first()
    if persona_doc is None:
        tipo_doc = (
            TipoDocumento.objects.filter(codigo=tipo_documento_codigo).first()
            or TipoDocumento.objects.first()
        )
        persona_doc = PersonaDocumento.objects.create(
            tipo_documento=tipo_doc,
            numero_documento=numero_documento,
        )

    persona = Persona.objects.create(
        persona_documento=persona_doc,
        nombre1=nombre1.strip(),
        apellido1=apellido1.strip(),
        nombre2=(nombre2 or "").strip() or None,
        apellido2=(apellido2 or "").strip() or None,
    )
    return persona, True
