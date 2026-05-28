"""Serializers DRF — Votaciones (Etapa B Plan Frontend).

Contratos JSON Angular-ready para los endpoints públicos read-only:
- Listado de eventos de votación activos.
- Candidatos de un evento agrupados en Identidades/Derechos.
- Resultados (ranking + totales) — solo staff.

Mantiene los nombres de campos en inglés (modelo legacy de votaciones,
único módulo del proyecto en inglés). Las mutaciones (validate_voter,
vote) siguen en JsonResponse legacy hasta una migración separada.
"""
from rest_framework import serializers


class EventoSerializer(serializers.Serializer):
    """Cabecera de un evento de votación."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    starts_at = serializers.DateTimeField(read_only=True, allow_null=True)
    ends_at = serializers.DateTimeField(read_only=True, allow_null=True)
    is_open = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_message = serializers.CharField(read_only=True)


class CandidatoSerializer(serializers.Serializer):
    """Candidato a una curul (Identidades o Derechos)."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    genre = serializers.CharField(read_only=True, allow_blank=True)
    group = serializers.CharField(read_only=True)  # IDENTIDADES | DERECHOS
    curul = serializers.CharField(read_only=True)
    code = serializers.CharField(read_only=True, allow_blank=True)
    photo_url = serializers.CharField(read_only=True, allow_blank=True)
    bio = serializers.CharField(read_only=True, allow_blank=True)
    is_active = serializers.BooleanField(read_only=True)
    event_id = serializers.IntegerField(read_only=True)


class CandidatosPorEventoSerializer(serializers.Serializer):
    """Respuesta agrupada del endpoint de candidatos de un evento."""
    event = EventoSerializer(read_only=True)
    identidades = CandidatoSerializer(many=True, read_only=True)
    derechos = CandidatoSerializer(many=True, read_only=True)
    count_identidades = serializers.IntegerField(read_only=True)
    count_derechos = serializers.IntegerField(read_only=True)


class RankingItemSerializer(serializers.Serializer):
    """Item del ranking por curul."""
    candidate_id = serializers.IntegerField(read_only=True, allow_null=True)
    candidate_name = serializers.CharField(read_only=True)
    photo_url = serializers.CharField(read_only=True, allow_blank=True)
    curul = serializers.CharField(read_only=True)
    votes = serializers.IntegerField(read_only=True)
    percentage = serializers.FloatField(read_only=True)


class ResultadosSerializer(serializers.Serializer):
    """Resultados de una votación (solo staff)."""
    event = serializers.DictField(read_only=True, allow_null=True)
    total_votes = serializers.IntegerField(read_only=True)
    unique_voters = serializers.IntegerField(read_only=True)
    ranking_identidades = RankingItemSerializer(many=True, read_only=True)
    ranking_derechos = RankingItemSerializer(many=True, read_only=True)
    total_identidades_votes = serializers.IntegerField(read_only=True)
    total_derechos_votes = serializers.IntegerField(read_only=True)


# ─────────────────────────────────────────────────────────────────────
# Cierre Etapa C #2 — Mutación pública DRF (validate + vote)
# ─────────────────────────────────────────────────────────────────────


class ValidateVoterRequestSerializer(serializers.Serializer):
    """Entrada: cédula a validar contra PersonaDocumento."""
    document_number = serializers.CharField(max_length=30, min_length=1)


class ValidateVoterResponseSerializer(serializers.Serializer):
    """Respuesta: si la cédula existe + nombre completo."""
    exists = serializers.BooleanField()
    document_number = serializers.CharField()
    full_name = serializers.CharField(allow_blank=True)
    persona_id = serializers.IntegerField(required=False, allow_null=True)


class VoteRequestSerializer(serializers.Serializer):
    """Entrada para registrar un voto.

    candidate_*_id = 0 → voto en blanco para ese grupo.
    consent_accepted requerido por consentimiento informado.
    """
    event_id = serializers.IntegerField(min_value=1)
    candidate_identidades_id = serializers.IntegerField(min_value=0, default=0)
    candidate_derechos_id = serializers.IntegerField(min_value=0, default=0)
    document_number = serializers.CharField(max_length=30, min_length=1)
    consent_accepted = serializers.BooleanField()


class VoteResponseSerializer(serializers.Serializer):
    """Resultado de un voto registrado o ya emitido."""
    already_voted = serializers.BooleanField()
    vote_id = serializers.IntegerField(allow_null=True)
    voter_full_name = serializers.CharField(allow_blank=True)
    vote_in_blank_identidades = serializers.BooleanField()
    vote_in_blank_derechos = serializers.BooleanField()
