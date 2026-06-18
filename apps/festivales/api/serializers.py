from rest_framework import serializers

from apps.festivales.models import Festival, TipoFestival


class TipoFestivalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoFestival
        fields = ["codigo", "nombre"]


class FestivalSerializer(serializers.ModelSerializer):
    tipo_festival_nombre = serializers.CharField(
        source="tipo_festival.nombre", read_only=True, default=None,
    )
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    n_eventos = serializers.SerializerMethodField()

    class Meta:
        model = Festival
        fields = [
            "id", "nombre", "tipo_festival", "tipo_festival_nombre",
            "vigencia", "numero_edicion", "estado", "estado_display",
            "subgrupo_id", "fecha_inicio", "fecha_fin", "lugar_texto",
            "descripcion", "documentado", "publicado", "publicado_en", "slug",
            "n_eventos", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "documentado", "publicado", "publicado_en", "slug",
            "created_at", "updated_at",
        ]

    def get_n_eventos(self, obj) -> int:
        # Cuenta de actos (eventos) agrupados bajo este festival.
        return obj.eventos.count()

    def validate(self, attrs):
        # Regla módulo 1: máx. 15 festivales activos (no cerrados) por vigencia.
        # Solo aplica al crear o al reactivar (estado != cerrado).
        estado = attrs.get("estado", getattr(self.instance, "estado", Festival.PLANEADO))
        vigencia = attrs.get("vigencia", getattr(self.instance, "vigencia", None))
        if estado != Festival.CERRADO and vigencia is not None:
            qs = Festival.objects.filter(vigencia=vigencia).exclude(estado=Festival.CERRADO)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.count() >= 15:
                raise serializers.ValidationError(
                    f"Ya hay 15 festivales activos en la vigencia {vigencia} "
                    f"(tope de la meta anual). Cierra alguno antes de crear otro."
                )
        return attrs
