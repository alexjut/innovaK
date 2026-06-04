"""Serializers DRF — Entregas de insumos / utensilios.

3 serializers para el flujo del organizador:
- EntregaInsumoListSerializer: tabla resumida.
- EntregaInsumoDetailSerializer: vista 360° con insumos entregados.
- EntregaEstadoUpdateSerializer: validar/rechazar.
"""
from rest_framework import serializers

from apps.entregas.models import EntregaInsumo


class EntregaInsumoListSerializer(serializers.ModelSerializer):
    """Campos clave para tabla paginada."""
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = EntregaInsumo
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento_id", "evento_nombre",
            "tipo_doc_codigo", "numero_documento", "nombre_completo",
        ]

    def get_nombre_completo(self, obj):
        partes = filter(None, [obj.nombre1, obj.nombre2, obj.apellido1, obj.apellido2])
        return " ".join(partes)


class EntregaInsumoDetailSerializer(serializers.ModelSerializer):
    """Vista 360° con insumos entregados (con cantidad)."""
    evento = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    elementos = serializers.SerializerMethodField()
    upl_nombre = serializers.SerializerMethodField()
    barrio_nombre = serializers.SerializerMethodField()
    tiene_firma = serializers.SerializerMethodField()

    class Meta:
        model = EntregaInsumo
        fields = [
            "id", "estado", "created_at", "updated_at",
            "evento",
            "tipo_doc_codigo", "numero_documento", "nombre_completo",
            "nombre1", "nombre2", "apellido1", "apellido2",
            "telefono", "correo",
            "direccion", "barrio_codigo", "barrio_nombre",
            "upl_codigo", "upl_nombre",
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

    def get_elementos(self, obj):
        return [
            {
                "codigo": rel.implemento.codigo if rel.implemento_id else None,
                "nombre": rel.implemento.nombre if rel.implemento_id else None,
                "categoria": rel.implemento.categoria if rel.implemento_id else None,
                "cantidad": rel.cantidad,
            }
            for rel in obj.rel_elementos.select_related("implemento")
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
