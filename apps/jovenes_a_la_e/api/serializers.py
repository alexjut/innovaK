"""Serializers DRF — Jóvenes a la E (Etapa B Plan Frontend).

3 serializers para el flujo del organizador:
- EntregaBecaListSerializer: tabla resumida.
- EntregaBecaDetailSerializer: vista 360° con elementos entregados.
- EntregaEstadoUpdateSerializer: validar/rechazar.
"""
from rest_framework import serializers

from apps.jovenes_a_la_e.models import EntregaBeca


class EntregaBecaListSerializer(serializers.ModelSerializer):
    """Campos clave para tabla paginada."""
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = EntregaBeca
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento_id", "evento_nombre",
            "tipo_doc_codigo", "numero_documento", "nombre_completo",
            "cumplimiento_acceso", "cumplimiento_permanencia",
            "nivel_formacion", "convenio_codigo",
        ]

    def get_nombre_completo(self, obj):
        partes = filter(None, [obj.nombre1, obj.nombre2, obj.apellido1, obj.apellido2])
        return " ".join(partes)


class EntregaBecaDetailSerializer(serializers.ModelSerializer):
    """Vista 360° con elementos entregados + flags de cumplimiento."""
    evento = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    nivel_formacion_label = serializers.SerializerMethodField()
    elementos = serializers.SerializerMethodField()
    upl_nombre = serializers.SerializerMethodField()
    barrio_nombre = serializers.SerializerMethodField()
    tiene_firma = serializers.SerializerMethodField()
    metas_cumplidas = serializers.SerializerMethodField()

    class Meta:
        model = EntregaBeca
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento", "convenio_codigo", "proyecto_codigo", "metas_codigos",
            "tipo_doc_codigo", "numero_documento", "nombre_completo",
            "nombre1", "nombre2", "apellido1", "apellido2",
            "telefono", "correo",
            "direccion", "barrio_codigo", "barrio_nombre", "upz_codigo",
            "upl_codigo", "upl_nombre",
            "cumplimiento_acceso", "cumplimiento_permanencia", "metas_cumplidas",
            "nivel_formacion", "nivel_formacion_label",
            "institucion", "programa_academico", "periodo_academico",
            "tiene_firma", "firma_fecha",
            "observaciones", "elementos",
        ]

    def get_evento(self, obj):
        if not obj.evento_id:
            return None
        return {"id": obj.evento_id, "nombre": obj.evento.nombre}

    def get_nombre_completo(self, obj):
        partes = filter(None, [obj.nombre1, obj.nombre2, obj.apellido1, obj.apellido2])
        return " ".join(partes)

    def get_nivel_formacion_label(self, obj):
        return dict(EntregaBeca.NIVEL_CHOICES).get(obj.nivel_formacion, obj.nivel_formacion)

    def get_elementos(self, obj):
        return [
            {
                "codigo": rel.elemento.codigo if rel.elemento_id else None,
                "nombre": rel.elemento.nombre if rel.elemento_id else None,
                "cantidad": rel.cantidad,
            }
            for rel in obj.rel_elementos.select_related("elemento")
        ]

    def get_upl_nombre(self, obj):
        if not obj.upl_codigo:
            return None
        from apps.banco_iniciativas.models.catalogos import Upl
        u = Upl.objects.filter(codigo=obj.upl_codigo).first()
        return u.nombre if u else f"UPL {obj.upl_codigo}"

    def get_barrio_nombre(self, obj):
        if not obj.barrio_codigo:
            return None
        from apps.georeferenciacion.models.models_localizacion import Barrio
        b = Barrio.objects.filter(codigo=obj.barrio_codigo).first()
        return b.nombre if b else None

    def get_tiene_firma(self, obj):
        return bool(obj.firma_mongo_id)

    def get_metas_cumplidas(self, obj):
        """Lista de códigos de meta que la entrega satisface según los flags."""
        cods = []
        if obj.cumplimiento_acceso:
            cods.append("23771")
        if obj.cumplimiento_permanencia:
            cods.append("23772")
        return cods


class EntregaEstadoUpdateSerializer(serializers.Serializer):
    """Payload para validar o rechazar una entrega.

    Validar: opcionalmente puede incluir `observaciones`.
    Rechazar: requiere `observaciones` no vacío (motivo obligatorio).
    """
    accion = serializers.ChoiceField(choices=["validar", "rechazar"])
    observaciones = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, data):
        if data["accion"] == "rechazar" and not (data.get("observaciones") or "").strip():
            raise serializers.ValidationError({
                "observaciones": "Debes ingresar un motivo de rechazo.",
            })
        return data
