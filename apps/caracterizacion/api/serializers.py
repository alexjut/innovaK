"""Serializers DRF — caracterización (Etapa B Plan Frontend).

Read-only para los 6 sectores de caracterización (Cultura, Deporte,
Mujer, Salud, Poblacional, Participación Ciudadana). Las wizards
públicas (POST captura) siguen siendo vistas HTML — esta API REST
es solo para consulta agregada de un dashboard externo.

Notas críticas:
- `_CaracterizacionBase.evento_id` es `IntegerField`, no FK. Las views
  precomputan `evento_nombres = {id: nombre}` para hacer el join
  manual y evitar N+1. Los serializers leen del `context`.
- `CaracterizacionSalud.firma_mongo_id` NO se expone — solo el flag
  derivado `tiene_firma`. La firma cifrada (AES-256-GCM) vive en
  Mongo, su ID es secreto.
- `CaracterizacionMujer` opcionalmente incluye `hogar` anidado con
  todos los campos de `InformacionHogar` cuando el FK lógico apunta
  a una fila existente.
"""
from rest_framework import serializers

from apps.caracterizacion.models.caracterizaciones import (
    CaracterizacionCultura,
    CaracterizacionDeporte,
    CaracterizacionMujer,
    CaracterizacionParticipacionCiudadana,
    CaracterizacionPoblacional,
    CaracterizacionSalud,
    InformacionHogar,
)


class InformacionHogarSerializer(serializers.ModelSerializer):
    class Meta:
        model = InformacionHogar
        fields = [
            "id", "persona_id",
            "estado_civil_jefe_hogar_codigo",
            "personas_hogar", "dependientes_economicos",
            "menores_cargo", "mayores_cargo",
            "tiene_hijos", "es_jefe",
        ]


# ─────────────────────────────────────────────────────────────────────
# Mixin: campos comunes resueltos desde context (evita N+1)
# ─────────────────────────────────────────────────────────────────────

class _CaracterizacionListMixin(serializers.Serializer):
    """Resuelve evento_nombre y persona_nombre desde diccionarios pre-
    computados que la view pasa en `context`. Evita N+1.

    Context esperado:
        evento_nombres   {id: nombre}
        persona_nombres  {id: "Nombre Apellido"}
    """
    evento_nombre = serializers.SerializerMethodField()
    persona_nombre = serializers.SerializerMethodField()

    def get_evento_nombre(self, obj):
        mapa = self.context.get("evento_nombres", {})
        return mapa.get(obj.evento_id)

    def get_persona_nombre(self, obj):
        mapa = self.context.get("persona_nombres", {})
        return mapa.get(obj.persona_id)


# ─────────────────────────────────────────────────────────────────────
# CULTURA
# ─────────────────────────────────────────────────────────────────────

class CulturaListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    class Meta:
        model = CaracterizacionCultura
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "nivel_educativo_codigo",
            "documentacion_soporte",
        ]


class CulturaDetailSerializer(CulturaListSerializer):
    class Meta(CulturaListSerializer.Meta):
        fields = CulturaListSerializer.Meta.fields + ["motivacion_personal"]


# ─────────────────────────────────────────────────────────────────────
# DEPORTE
# ─────────────────────────────────────────────────────────────────────

class DeporteListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    class Meta:
        model = CaracterizacionDeporte
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "nivel_educativo_codigo",
            "documentacion_soporte",
            "lugar_incidencia_id",
        ]


class DeporteDetailSerializer(DeporteListSerializer):
    class Meta(DeporteListSerializer.Meta):
        fields = DeporteListSerializer.Meta.fields + ["motivacion_personal"]


# ─────────────────────────────────────────────────────────────────────
# MUJER
# ─────────────────────────────────────────────────────────────────────

class MujerListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    class Meta:
        model = CaracterizacionMujer
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "informacion_hogar_id",
            "sabe_leer_escribir",
            "interes_formacion",
        ]


class MujerDetailSerializer(MujerListSerializer):
    """Incluye el hogar anidado cuando el FK lógico apunta a uno."""
    hogar = serializers.SerializerMethodField()

    class Meta(MujerListSerializer.Meta):
        fields = MujerListSerializer.Meta.fields + ["formacion_esperada", "hogar"]

    def get_hogar(self, obj):
        if not obj.informacion_hogar_id:
            return None
        hogar = InformacionHogar.objects.filter(pk=obj.informacion_hogar_id).first()
        return InformacionHogarSerializer(hogar).data if hogar else None


# ─────────────────────────────────────────────────────────────────────
# SALUD
# ─────────────────────────────────────────────────────────────────────

class SaludListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    """`firma_mongo_id` NO se expone. Solo el flag `tiene_firma`."""
    tiene_firma = serializers.SerializerMethodField()

    class Meta:
        model = CaracterizacionSalud
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "presenta_discapacidad",
            "tiene_certificado_discapacidad",
            "tiene_cuidador",
            "tiene_firma",
        ]

    def get_tiene_firma(self, obj):
        return bool(obj.firma_mongo_id)


class SaludDetailSerializer(SaludListSerializer):
    """Detail expone todos los campos médicos. `firma_mongo_id` sigue oculto."""

    class Meta(SaludListSerializer.Meta):
        fields = SaludListSerializer.Meta.fields + [
            "estado_salud", "condiciones_salud",
            "requiere_apoyo",
            "usted_es_cuidador",
            "pertenece_organizacion_inclusiva",
            "tipo_poblacion_atendida",
            "firma_digital",  # bool de consentimiento — NO la firma cifrada.
        ]


# ─────────────────────────────────────────────────────────────────────
# POBLACIONAL
# ─────────────────────────────────────────────────────────────────────

class PoblacionalListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    class Meta:
        model = CaracterizacionPoblacional
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "pertenencia_lgbti", "victima_conflicto", "habitante_calle",
            "trabajador_sexual", "madre_cabeza_hogar",
            "grupo_etareo", "enfoque_diferencial",
        ]


class PoblacionalDetailSerializer(PoblacionalListSerializer):
    class Meta(PoblacionalListSerializer.Meta):
        fields = PoblacionalListSerializer.Meta.fields  # mismo set


# ─────────────────────────────────────────────────────────────────────
# PARTICIPACIÓN CIUDADANA
# ─────────────────────────────────────────────────────────────────────

class ParticipacionListSerializer(_CaracterizacionListMixin, serializers.ModelSerializer):
    class Meta:
        model = CaracterizacionParticipacionCiudadana
        fields = [
            "id", "evento_id", "evento_nombre",
            "persona_id", "persona_nombre",
            "funcionario_id",
            "pertenece_organizacion", "tipo_organizacion", "es_funcionario",
        ]


class ParticipacionDetailSerializer(ParticipacionListSerializer):
    class Meta(ParticipacionListSerializer.Meta):
        fields = ParticipacionListSerializer.Meta.fields + ["condicion_poblacional"]
