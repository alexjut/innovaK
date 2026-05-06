"""Servicios para asegurar registros en `Beneficiario` (PR-7 actividades).

`Beneficiario` es polimórfico (PERSONA / ORGANIZACION / PROVEEDOR) y es
el universo único de "atendidos" por la Alcaldía. Cada flujo de captura
(caracterizaciones, banco de iniciativas, etc.) debe poblar este modelo
para que la lista en /org/beneficiarios/ refleje todo lo capturado.

Reglas:
  - Idempotente: si ya hay Beneficiario para esa Persona/Organización,
    se reusa (no se duplica).
  - No-destructivo: si el Beneficiario existe, NO sobrescribe sus datos.
  - Tolerante: si falta info crítica (ej. tipo_documento), retorna None
    en vez de explotar — el flujo principal sigue.

Política CLAUDE.md §3 ("`to_field='codigo'` para FKs a catálogos"): el
Beneficiario.tipo_documento usa `codigo` como FK target.
"""
from __future__ import annotations

import logging
from typing import Optional

from apps.login.models.contratos import Beneficiario, Organizacion
from apps.login.models.persona import Persona
from apps.login.models.persona_documento import TipoDocumento

logger = logging.getLogger(__name__)


# Códigos de tipo_documento conocidos (lookup por nombre como respaldo).
_TIPO_DOC_NIT = 5  # NIT — para organizaciones


def _nombre_persona(p: Persona) -> str:
    parts = [p.nombre1 or "", p.nombre2 or "", p.apellido1 or "", p.apellido2 or ""]
    return " ".join(x for x in parts if x).strip() or f"Persona #{p.id}"


def asegurar_beneficiario_persona(
    persona: Persona,
    *,
    correo: Optional[str] = None,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None,
) -> Optional[Beneficiario]:
    """Idempotente: crea Beneficiario tipo PERSONA si no existe para
    `persona`. Retorna el existente si ya hay uno. None si la persona
    no tiene `persona_documento` (no se puede identificar)."""
    if persona is None:
        return None
    benef = Beneficiario.objects.filter(
        tipo="PERSONA", persona_id=persona.id,
    ).first()
    if benef is not None:
        return benef

    pd = persona.persona_documento
    if pd is None or pd.tipo_documento_id is None:
        logger.info(
            "asegurar_beneficiario_persona: persona %s sin persona_documento. Skip.",
            persona.id,
        )
        return None

    try:
        return Beneficiario.objects.create(
            tipo="PERSONA",
            persona=persona,
            tipo_documento_id=pd.tipo_documento_id,
            numero_documento=pd.numero_documento or "",
            nombre_legal=_nombre_persona(persona),
            correo=correo,
            telefono=telefono,
            direccion=direccion,
        )
    except Exception:
        logger.exception(
            "Error creando Beneficiario PERSONA para persona %s", persona.id,
        )
        return None


def asegurar_beneficiario_organizacion(
    org: Organizacion,
    *,
    correo: Optional[str] = None,
    telefono: Optional[str] = None,
    direccion: Optional[str] = None,
) -> Optional[Beneficiario]:
    """Idempotente: crea Beneficiario tipo ORGANIZACION si no existe."""
    if org is None:
        return None
    benef = Beneficiario.objects.filter(
        tipo="ORGANIZACION", organizacion_id=org.id,
    ).first()
    if benef is not None:
        return benef

    nit = (getattr(org, "nit", None) or "").strip() or f"ORG-{org.id}"
    nombre = (getattr(org, "nombre", None) or "").strip() or f"Organización #{org.id}"

    try:
        # Tipo documento NIT (codigo=5). Si no existe en BD, fallback al primero.
        tipo_doc = (
            TipoDocumento.objects.filter(codigo=_TIPO_DOC_NIT).first()
            or TipoDocumento.objects.first()
        )
        if tipo_doc is None:
            return None
        return Beneficiario.objects.create(
            tipo="ORGANIZACION",
            organizacion=org,
            tipo_documento=tipo_doc,
            numero_documento=nit,
            nombre_legal=nombre,
            correo=correo or getattr(org, "correo", None),
            telefono=telefono or getattr(org, "telefono", None),
            direccion=direccion,
        )
    except Exception:
        logger.exception(
            "Error creando Beneficiario ORGANIZACION para org %s", org.id,
        )
        return None
