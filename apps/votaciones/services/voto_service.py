from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.login.models.persona import Persona
from apps.login.models.persona_documento import PersonaDocumento

from ..models import Candidato, Evento, Voto


@dataclass
class ResultadoVoto:
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


def _candidato_group(candidato: Candidato) -> str:
    """
    Extrae el grupo desde genre.
    Formato esperado:
      IDENTIDADES|LESBIANAS
      DERECHOS|SEGURIDAD
    """
    value = (candidato.genre or "").strip()
    if "|" in value:
        return value.split("|", 1)[0].strip().upper()
    return value.upper()


def registrar_voto(
    *,
    event_id: int,
    candidate_identidades_id: int,
    candidate_derechos_id: int,
    document_number: str,
    consent_accepted: bool = False,
    ip: str = "",
    user_agent: str = "",
) -> ResultadoVoto:
    """
    Registra un voto público.
    Regla:
      - hasta `evento.votos_permitidos` votos por cédula por votación
        (default = 1, voto único)
      - 1 selección en Identidades o voto en blanco
      - 1 selección en Derechos o voto en blanco
      - voto en blanco = id 0
      - solo permite votar dentro del rango starts_at / ends_at
    """

    document_number = (document_number or "").strip()
    ip = (ip or "").strip()
    user_agent = (user_agent or "").strip()

    if not document_number:
        return ResultadoVoto(ok=False, error="La cédula es obligatoria.")

    if not consent_accepted:
        return ResultadoVoto(ok=False, error="Debes aceptar la política de datos.")

    if event_id <= 0:
        return ResultadoVoto(ok=False, error="La votación es obligatoria.")

    if candidate_identidades_id < 0 or candidate_derechos_id < 0:
        return ResultadoVoto(ok=False, error="Los ids de candidatura no pueden ser negativos.")

    try:
        with transaction.atomic():
            evento = Evento.objects.select_for_update().filter(id=event_id).first()
            if not evento:
                return ResultadoVoto(ok=False, error="La votación no existe.")

            if not evento.is_active:
                return ResultadoVoto(ok=False, error="La votación está inactiva.")

            now = timezone.now()

            if evento.starts_at and now < evento.starts_at:
                return ResultadoVoto(ok=False, error="La votación aún no ha iniciado.")

            if evento.ends_at and now > evento.ends_at:
                return ResultadoVoto(ok=False, error="La votación ya finalizó.")

            documento = (
                PersonaDocumento.objects.select_for_update()
                .filter(numero_documento=document_number)
                .first()
            )
            if not documento:
                return ResultadoVoto(
                    ok=False,
                    error="La cédula no se encuentra habilitada para votar.",
                )

            persona = (
                Persona.objects.select_related("persona_documento")
                .filter(persona_documento=documento)
                .first()
            )
            if not persona:
                return ResultadoVoto(
                    ok=False,
                    error="No se encontró una persona asociada a esta cédula.",
                )

            voter_full_name = _build_full_name(persona)
            if not voter_full_name:
                voter_full_name = f"Cédula {document_number}"

            votos_permitidos = max(1, int(getattr(evento, "votos_permitidos", 1) or 1))

            votos_previos_qs = Voto.objects.filter(
                evento_id=evento.id,
                document_number=document_number,
            )
            votos_previos = votos_previos_qs.count()

            if votos_previos >= votos_permitidos:
                ultimo = votos_previos_qs.order_by("-id").first()
                if votos_permitidos == 1:
                    msg = "Esta cédula ya registró un voto en esta votación."
                else:
                    msg = (
                        f"Esta cédula ya registró {votos_previos} de "
                        f"{votos_permitidos} votos permitidos en esta votación."
                    )
                return ResultadoVoto(
                    ok=False,
                    error=msg,
                    already_voted=True,
                    vote_id=ultimo.id if ultimo else None,
                    voter_full_name=voter_full_name,
                )

            candidato_identidades = None
            if candidate_identidades_id != 0:
                candidato_identidades = (
                    Candidato.objects.select_for_update()
                    .filter(id=candidate_identidades_id)
                    .first()
                )

                if not candidato_identidades:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Identidades no existe.",
                    )

                if not candidato_identidades.is_active:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Identidades está inactiva.",
                    )

                if candidato_identidades.evento_id != evento.id:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Identidades no pertenece a esta votación.",
                    )

                if _candidato_group(candidato_identidades) != "IDENTIDADES":
                    return ResultadoVoto(
                        ok=False,
                        error="La selección de Identidades no pertenece al grupo Identidades.",
                    )

            candidato_derechos = None
            if candidate_derechos_id != 0:
                candidato_derechos = (
                    Candidato.objects.select_for_update()
                    .filter(id=candidate_derechos_id)
                    .first()
                )

                if not candidato_derechos:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Derechos no existe.",
                    )

                if not candidato_derechos.is_active:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Derechos está inactiva.",
                    )

                if candidato_derechos.evento_id != evento.id:
                    return ResultadoVoto(
                        ok=False,
                        error="La candidatura de Derechos no pertenece a esta votación.",
                    )

                if _candidato_group(candidato_derechos) != "DERECHOS":
                    return ResultadoVoto(
                        ok=False,
                        error="La selección de Derechos no pertenece al grupo Derechos.",
                    )

            voto = Voto.objects.create(
                evento_id=evento.id,
                candidato_identidades=candidato_identidades,
                candidato_derechos=candidato_derechos,
                document_number=document_number,
                voter_full_name=voter_full_name,
                consent_accepted=True,
                consent_accepted_at=timezone.now(),
                ip_address=ip or None,
                user_agent=user_agent,
                votante_legacy=persona.id,
                candidato_legacy=0,
            )

            return ResultadoVoto(
                ok=True,
                already_voted=False,
                vote_id=voto.id,
                voter_full_name=voter_full_name,
            )

    except IntegrityError:
        existing = Voto.objects.filter(
            evento_id=event_id,
            document_number=document_number,
        ).first()

        if existing:
            return ResultadoVoto(
                ok=False,
                error="Esta cédula ya registró un voto en esta votación.",
                already_voted=True,
                vote_id=existing.id,
                voter_full_name=getattr(existing, "voter_full_name", ""),
            )

        return ResultadoVoto(ok=False, error="Conflicto de integridad al registrar el voto.")

    except Exception as e:
        return ResultadoVoto(ok=False, error=f"Error registrando voto: {e}")
