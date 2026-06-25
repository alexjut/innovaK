from rest_framework import serializers

from apps.festivales.models import Festival, FestivalArchivo, FestivalDia, TipoFestival


class TipoFestivalSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoFestival
        fields = ["codigo", "nombre"]


class FestivalEventoSerializer(serializers.Serializer):
    """Acto (Evento) asociado a un festival, para la vista de detalle."""

    id = serializers.IntegerField()
    nombre = serializers.CharField()
    fecha_inicio = serializers.DateField(default=None)
    fecha_fin = serializers.DateField(default=None)
    tipo_evento_nombre = serializers.CharField(source="tipo_evento.nombre", default=None)
    subgrupo_nombre = serializers.CharField(source="subgrupo.nombre", default=None)
    funcionario_nombre = serializers.CharField(source="funcionario.persona.nombre1", default=None)
    festival_dia_id = serializers.IntegerField(default=None)
    aforo_proyectado = serializers.IntegerField(default=None)
    aforo = serializers.SerializerMethodField()

    def get_aforo(self, obj) -> int:
        from apps.festivales.models import FestivalAsistencia
        return FestivalAsistencia.objects.filter(evento_id=obj.id).count()


class FestivalDiaSerializer(serializers.ModelSerializer):
    """Día del festival con su metadata (PR-A programación multi-día)."""

    responsable_nombre = serializers.SerializerMethodField()
    n_actos = serializers.SerializerMethodField()

    class Meta:
        model = FestivalDia
        fields = [
            "id", "festival", "fecha", "nombre", "escenario_texto",
            "responsable", "responsable_nombre", "orden", "descripcion",
            "n_actos", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_responsable_nombre(self, obj):
        if obj.responsable_id and obj.responsable and obj.responsable.persona:
            p = obj.responsable.persona
            return " ".join(filter(None, [p.nombre1, p.apellido1])).strip() or None
        return None

    def get_n_actos(self, obj) -> int:
        return obj.actos.count()

    def validate(self, attrs):
        # Un día no puede salirse del rango de fechas del festival (si está fijado).
        festival = attrs.get("festival", getattr(self.instance, "festival", None))
        fecha = attrs.get("fecha", getattr(self.instance, "fecha", None))
        if festival and fecha:
            if festival.fecha_inicio and fecha < festival.fecha_inicio:
                raise serializers.ValidationError(
                    {"fecha": f"El día no puede ser anterior al inicio del festival "
                              f"({festival.fecha_inicio})."}
                )
            if festival.fecha_fin and fecha > festival.fecha_fin:
                raise serializers.ValidationError(
                    {"fecha": f"El día no puede ser posterior al fin del festival "
                              f"({festival.fecha_fin})."}
                )
        return attrs


class FestivalDiaConActosSerializer(FestivalDiaSerializer):
    """Día + sus actos embebidos, para la agenda del detalle."""

    actos = serializers.SerializerMethodField()

    class Meta(FestivalDiaSerializer.Meta):
        fields = FestivalDiaSerializer.Meta.fields + ["actos"]

    def get_actos(self, obj):
        actos = (
            obj.actos
            .select_related("tipo_evento", "subgrupo", "funcionario__persona")
            .order_by("fecha_inicio", "id")
        )
        return FestivalEventoSerializer(actos, many=True).data


class FestivalArchivoSerializer(serializers.ModelSerializer):
    """Evidencia de la biblioteca (metadata + URL de descarga autenticada)."""

    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    es_imagen = serializers.BooleanField(read_only=True)
    archivo_url = serializers.SerializerMethodField()
    subido_por_nombre = serializers.SerializerMethodField()
    dia_fecha = serializers.DateField(source="festival_dia.fecha", read_only=True, default=None)

    class Meta:
        model = FestivalArchivo
        fields = [
            "id", "festival", "festival_dia", "dia_fecha", "tipo", "tipo_display",
            "nombre_archivo", "mime", "tamano_bytes", "descripcion", "es_imagen",
            "archivo_url", "subido_por_nombre", "created_at",
        ]
        read_only_fields = fields

    def get_archivo_url(self, obj) -> str:
        return f"/festivales/api/biblioteca/{obj.id}/archivo/"

    def get_subido_por_nombre(self, obj):
        if obj.subido_por_id and obj.subido_por and obj.subido_por.persona:
            p = obj.subido_por.persona
            return " ".join(filter(None, [p.nombre1, p.apellido1])).strip() or None
        return None


class FestivalSerializer(serializers.ModelSerializer):
    tipo_festival_nombre = serializers.CharField(
        source="tipo_festival.nombre", read_only=True, default=None,
    )
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    responsable_nombre = serializers.SerializerMethodField()
    n_eventos = serializers.SerializerMethodField()
    n_dias = serializers.SerializerMethodField()
    n_archivos = serializers.SerializerMethodField()

    class Meta:
        model = Festival
        fields = [
            "id", "nombre", "tipo_festival", "tipo_festival_nombre",
            "vigencia", "numero_edicion", "estado", "estado_display",
            "subgrupo_id", "responsable", "responsable_nombre",
            "fecha_inicio", "fecha_fin", "lugar_texto",
            "upl_codigo", "latitud", "longitud",
            "descripcion", "documentado", "publicado", "publicado_en", "slug",
            "n_eventos", "n_dias", "n_archivos", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "documentado", "publicado", "publicado_en", "slug",
            "created_at", "updated_at",
        ]

    def get_responsable_nombre(self, obj):
        if obj.responsable_id and obj.responsable and obj.responsable.persona:
            p = obj.responsable.persona
            return " ".join(filter(None, [p.nombre1, p.apellido1])).strip() or None
        return None

    def get_n_eventos(self, obj) -> int:
        # Cuenta de actos (eventos) agrupados bajo este festival.
        return obj.eventos.count()

    def get_n_dias(self, obj) -> int:
        return obj.dias.count()

    def get_n_archivos(self, obj) -> int:
        return obj.archivos.count()

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


class FestivalDetailSerializer(FestivalSerializer):
    """Detalle del festival: agenda por día + actos sin ubicar en la agenda."""

    dias = serializers.SerializerMethodField()
    eventos = serializers.SerializerMethodField()
    actos_sin_dia = serializers.SerializerMethodField()

    class Meta(FestivalSerializer.Meta):
        fields = FestivalSerializer.Meta.fields + ["dias", "eventos", "actos_sin_dia"]

    def get_dias(self, obj):
        dias = obj.dias.select_related("responsable__persona").all()
        return FestivalDiaConActosSerializer(dias, many=True).data

    def get_eventos(self, obj):
        # Compat: lista plana de todos los actos (la usa la UI heredada).
        actos = (
            obj.eventos
            .select_related("tipo_evento", "subgrupo", "funcionario__persona")
            .order_by("-fecha_inicio", "-id")
        )
        return FestivalEventoSerializer(actos, many=True).data

    def get_actos_sin_dia(self, obj):
        actos = (
            obj.eventos.filter(festival_dia__isnull=True)
            .select_related("tipo_evento", "subgrupo", "funcionario__persona")
            .order_by("fecha_inicio", "id")
        )
        return FestivalEventoSerializer(actos, many=True).data
