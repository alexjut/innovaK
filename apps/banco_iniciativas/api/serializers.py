"""Serializers DRF del módulo banco_iniciativas — Etapa B Plan Frontend.

3 serializers que cubren los flujos del organizador:
- `InscripcionListSerializer`: tabla resumida (lista paginada).
- `InscripcionDetailSerializer`: vista 360° con relaciones planas.
- `InscripcionEstadoUpdateSerializer`: mutación validar/rechazar.

Los M2Ms (escenarios, implementos, enfoques, etc.) se exponen como
listas planas de nombres en el detail. Esto es suficiente para Angular
sin obligar a serializar los catálogos intermedios.
"""
from rest_framework import serializers

from apps.banco_iniciativas.models.inscripcion import InscripcionBancoIniciativa


class InscripcionListSerializer(serializers.ModelSerializer):
    """Campos clave para tabla paginada (no traer todo)."""
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True)
    organizacion_nombre = serializers.CharField(source="organizacion.nombre", read_only=True)
    organizacion_nit = serializers.CharField(source="organizacion.nit", read_only=True)
    upl = serializers.CharField(source="upl.nombre", read_only=True)
    disciplina_principal = serializers.CharField(
        source="disciplina_principal.nombre", read_only=True, default=None,
    )

    class Meta:
        model = InscripcionBancoIniciativa
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento_id", "evento_nombre",
            "organizacion_id", "organizacion_nombre", "organizacion_nit",
            "rep_nombre", "rep_numero_doc",
            "upl", "disciplina_principal",
        ]


class InscripcionDetailSerializer(serializers.ModelSerializer):
    """Vista completa con FKs aplanadas + M2Ms como listas de nombres."""
    evento = serializers.SerializerMethodField()
    organizacion = serializers.SerializerMethodField()
    rep_tipo_doc = serializers.CharField(source="rep_tipo_doc.nombre", read_only=True)
    anios_experiencia = serializers.CharField(source="anios_experiencia.nombre", read_only=True)
    nivel_educativo = serializers.CharField(source="nivel_educativo.nombre", read_only=True, default=None)
    barrio = serializers.CharField(source="barrio.nombre", read_only=True, default=None)
    upl = serializers.CharField(source="upl.nombre", read_only=True, default=None)
    rango_poblacion = serializers.CharField(source="rango_poblacion.nombre", read_only=True)
    caracteristica_pob = serializers.CharField(source="caracteristica_pob.nombre", read_only=True, default=None)
    disciplina_principal = serializers.CharField(source="disciplina_principal.nombre", read_only=True, default=None)

    escenarios = serializers.SerializerMethodField()
    escenarios_actuales = serializers.SerializerMethodField()
    implementos = serializers.SerializerMethodField()
    rango_etarios = serializers.SerializerMethodField()
    enfoques = serializers.SerializerMethodField()
    beneficios_alk = serializers.SerializerMethodField()

    tiene_firma = serializers.SerializerMethodField()
    tiene_soporte_legal = serializers.SerializerMethodField()

    class Meta:
        model = InscripcionBancoIniciativa
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento", "organizacion", "proyecto_codigo",
            "rep_nombre", "rep_tipo_doc", "rep_numero_doc",
            "numero_soporte_legal", "soporte_legal_url",
            "anios_experiencia", "nivel_educativo", "titulos_obtenidos",
            "barrio", "upl", "direccion",
            "rango_poblacion", "estrato", "caracteristica_pob",
            "beneficiada_alk", "uso_beneficio",
            "impacto_politicas", "impacto_justificacion",
            "disciplina_principal",
            "escenarios", "escenarios_actuales",
            "implementos", "rango_etarios", "enfoques", "beneficios_alk",
            "tiene_firma", "tiene_soporte_legal",
        ]

    def get_evento(self, obj):
        if not obj.evento_id:
            return None
        return {"id": obj.evento_id, "nombre": obj.evento.nombre}

    def get_organizacion(self, obj):
        if not obj.organizacion_id:
            return None
        o = obj.organizacion
        return {"id": o.id, "nombre": o.nombre, "nit": o.nit}

    # M2Ms — listas planas de nombres para que Angular las consuma directo.
    def _m2m_nombres(self, qs, attr="nombre"):
        return [getattr(x, attr, str(x)) for x in qs]

    def get_escenarios(self, obj):
        return self._m2m_nombres(obj.escenarios.all())

    def get_escenarios_actuales(self, obj):
        return self._m2m_nombres(obj.escenarios_actuales.all())

    def get_implementos(self, obj):
        return self._m2m_nombres(obj.implementos.all())

    def get_rango_etarios(self, obj):
        return self._m2m_nombres(obj.rango_etarios.all())

    def get_enfoques(self, obj):
        return self._m2m_nombres(obj.enfoques.all())

    def get_beneficios_alk(self, obj):
        return self._m2m_nombres(obj.beneficios_alk.all())

    def get_tiene_firma(self, obj):
        return bool(obj.firma_mongo_id)

    def get_tiene_soporte_legal(self, obj):
        return bool(obj.soporte_legal_mongo_id) or bool(obj.soporte_legal_url)


class InscripcionEstadoUpdateSerializer(serializers.Serializer):
    """Payload para validar o rechazar una inscripción.

    `accion` debe ser 'validar' o 'rechazar'. El view se encarga de
    traducirla al estado final ('validada' / 'rechazada').
    """
    accion = serializers.ChoiceField(choices=["validar", "rechazar"])

    def validate_accion(self, value):
        if value not in {"validar", "rechazar"}:
            raise serializers.ValidationError("Acción inválida.")
        return value
