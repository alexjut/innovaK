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
