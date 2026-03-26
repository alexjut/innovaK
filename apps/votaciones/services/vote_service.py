from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.login.models.persona import Persona
from apps.login.models.persona_documento import PersonaDocumento

from ..models import Candidate, Event, Vote


@dataclass
class VoteResult:
    ok: bool
    error: Optional[str] = None
    already_voted: bool = False
    vote_id: Optional[int] = None
    voter_full_name: Optional[str] = None


def _build_full_name(persona: Persona) -> str:
    parts = [
        (persona.nombre1 or "").strip(),
        (persona.nombre2 or "").strip(),
        (persona.apellido1 or "").strip(),
        (persona.apellido2 or "").strip(),
    ]
    return " ".join(p for p in parts if p).strip()


def _candidate_group(candidate: Candidate) -> str:
    """
    Extrae el grupo desde genre.
    Formato esperado:
      IDENTIDADES|LESBIANAS
      DERECHOS|SEGURIDAD
    """
    value = (candidate.genre or "").strip()
    if "|" in value:
        return value.split("|", 1)[0].strip().upper()
    return value.upper()


def register_vote(
    *,
    event_id: int,
    candidate_identidades_id: int,
    candidate_derechos_id: int,
    document_number: str,
    consent_accepted: bool = False,
    ip: str = "",
    user_agent: str = "",
) -> VoteResult:
    """
    Registra un voto público.
    Regla:
      - 1 voto por cédula por votación
      - 1 selección en Identidades o voto en blanco
      - 1 selección en Derechos o voto en blanco
      - voto en blanco = id 0
      - solo permite votar dentro del rango starts_at / ends_at
    """

    document_number = (document_number or "").strip()
    ip = (ip or "").strip()
    user_agent = (user_agent or "").strip()

    if not document_number:
        return VoteResult(ok=False, error="La cédula es obligatoria.")

    if not consent_accepted:
        return VoteResult(ok=False, error="Debes aceptar la política de datos.")

    if event_id <= 0:
        return VoteResult(ok=False, error="La votación es obligatoria.")

    if candidate_identidades_id < 0 or candidate_derechos_id < 0:
        return VoteResult(ok=False, error="Los ids de candidatura no pueden ser negativos.")

    try:
        with transaction.atomic():
            event = Event.objects.select_for_update().filter(id=event_id).first()
            if not event:
                return VoteResult(ok=False, error="La votación no existe.")

            if not event.is_active:
                return VoteResult(ok=False, error="La votación está inactiva.")

            now = timezone.now()

            if event.starts_at and now < event.starts_at:
                return VoteResult(ok=False, error="La votación aún no ha iniciado.")

            if event.ends_at and now > event.ends_at:
                return VoteResult(ok=False, error="La votación ya finalizó.")

            documento = (
                PersonaDocumento.objects.select_for_update()
                .filter(numero_documento=document_number)
                .first()
            )
            if not documento:
                return VoteResult(
                    ok=False,
                    error="La cédula no se encuentra habilitada para votar.",
                )

            persona = (
                Persona.objects.select_related("persona_documento")
                .filter(persona_documento=documento)
                .first()
            )
            if not persona:
                return VoteResult(
                    ok=False,
                    error="No se encontró una persona asociada a esta cédula.",
                )

            voter_full_name = _build_full_name(persona)
            if not voter_full_name:
                voter_full_name = f"Cédula {document_number}"

            already = Vote.objects.filter(
                event_id=event.id,
                document_number=document_number,
            ).first()

            if already:
                return VoteResult(
                    ok=False,
                    error="Esta cédula ya registró un voto en esta votación.",
                    already_voted=True,
                    vote_id=already.id,
                    voter_full_name=voter_full_name,
                )

            candidate_identidades = None
            if candidate_identidades_id != 0:
                candidate_identidades = (
                    Candidate.objects.select_for_update()
                    .filter(id=candidate_identidades_id)
                    .first()
                )

                if not candidate_identidades:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Identidades no existe.",
                    )

                if not candidate_identidades.is_active:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Identidades está inactiva.",
                    )

                if candidate_identidades.event_id != event.id:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Identidades no pertenece a esta votación.",
                    )

                if _candidate_group(candidate_identidades) != "IDENTIDADES":
                    return VoteResult(
                        ok=False,
                        error="La selección de Identidades no pertenece al grupo Identidades.",
                    )

            candidate_derechos = None
            if candidate_derechos_id != 0:
                candidate_derechos = (
                    Candidate.objects.select_for_update()
                    .filter(id=candidate_derechos_id)
                    .first()
                )

                if not candidate_derechos:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Derechos no existe.",
                    )

                if not candidate_derechos.is_active:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Derechos está inactiva.",
                    )

                if candidate_derechos.event_id != event.id:
                    return VoteResult(
                        ok=False,
                        error="La candidatura de Derechos no pertenece a esta votación.",
                    )

                if _candidate_group(candidate_derechos) != "DERECHOS":
                    return VoteResult(
                        ok=False,
                        error="La selección de Derechos no pertenece al grupo Derechos.",
                    )

            vote = Vote.objects.create(
                event_id=event.id,
                candidate_identidades=candidate_identidades,
                candidate_derechos=candidate_derechos,
                document_number=document_number,
                voter_full_name=voter_full_name,
                consent_accepted=True,
                consent_accepted_at=timezone.now(),
                ip_address=ip or None,
                user_agent=user_agent,
                voter_legacy=persona.id,   # ← era voter_id
                candidate_legacy=0,        # ← era candidate_id
            )

            return VoteResult(
                ok=True,
                already_voted=False,
                vote_id=vote.id,
                voter_full_name=voter_full_name,
            )

    except IntegrityError:
        existing = Vote.objects.filter(
            event_id=event_id,
            document_number=document_number,
        ).first()

        if existing:
            return VoteResult(
                ok=False,
                error="Esta cédula ya registró un voto en esta votación.",
                already_voted=True,
                vote_id=existing.id,
                voter_full_name=getattr(existing, "voter_full_name", ""),
            )

        return VoteResult(ok=False, error="Conflicto de integridad al registrar el voto.")

    except Exception as e:
        return VoteResult(ok=False, error=f"Error registrando voto: {e}")