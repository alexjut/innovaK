"""
Serializers DRF del módulo georeferenciacion.

Primer piloto de Etapa B (Plan Frontend §3): exponer datos como
componentes reusables que un futuro cliente Angular consuma sin tocar
el backend. Hoy el FeatureCollection lo arma una vista función a mano;
con DRF queda como serializer, paginación y autenticación de fábrica.
"""
from rest_framework import serializers

from apps.login.models.evento import Evento


class EventoGeoFeatureSerializer(serializers.ModelSerializer):
    """Serializa un Evento en formato GeoJSON Feature.

    El response es {type: "Feature", geometry: {...}, properties: {...}}
    — compatible 1:1 con el formato que consume `mapa_kennedy.js` hoy
    (cuando se migre el front, Angular consume el MISMO contrato).

    Eventos sin geo (lugar_incidencia o coordenadas nulas) deben filtrarse
    en la view ANTES de pasarlos al serializer.
    """
    type = serializers.SerializerMethodField()
    geometry = serializers.SerializerMethodField()
    properties = serializers.SerializerMethodField()

    class Meta:
        model = Evento
        fields = ['type', 'geometry', 'properties']

    def get_type(self, obj):
        return 'Feature'

    def get_geometry(self, obj):
        geo = obj.lugar_incidencia.geo_referenciacion
        return {
            'type': 'Point',
            'coordinates': [float(geo.longitud), float(geo.latitud)],
        }

    def get_properties(self, obj):
        geo = obj.lugar_incidencia.geo_referenciacion
        func_nombre = ''
        if obj.funcionario_id and obj.funcionario and obj.funcionario.persona:
            p = obj.funcionario.persona
            func_nombre = f"{p.nombre1 or ''} {p.apellido1 or ''}".strip()

        props = {
            'id': obj.id,
            'nombre': obj.nombre,
            'descripcion': obj.descripcion or '',
            'fecha_inicio': obj.fecha_inicio.isoformat() if obj.fecha_inicio else None,
            'fecha_fin': obj.fecha_fin.isoformat() if obj.fecha_fin else None,
            'tipo_evento_codigo': obj.tipo_evento.codigo if obj.tipo_evento_id else None,
            'tipo_evento_nombre': obj.tipo_evento.nombre if obj.tipo_evento_id else None,
            'dependencia': obj.dependencia.nombre if obj.dependencia_id else None,
            'dependencia_id': obj.dependencia_id,
            'subgrupo': obj.subgrupo.nombre if obj.subgrupo_id else None,
            'subgrupo_id': obj.subgrupo_id,
            'funcionario': func_nombre,
            'indicador': obj.indicador.nombre if obj.indicador_id else None,
            'indicador_id': obj.indicador_id,
            'magnitud_aportada': float(obj.magnitud_aportada) if obj.magnitud_aportada is not None else None,
            'direccion': geo.direccion_texto or '',
            'activo': obj.activo,
            # True = el evento NO tiene coordenada propia; está en la sede de la
            # Alcaldía porque es la ubicación de respaldo. El mapa lo pinta
            # distinto y lo advierte en el popup en vez de hacerlo pasar por un
            # hecho ocurrido ahí. Ver EventoGeoJSONView.
            'ubicacion_aproximada': (
                self.context.get('lugar_default_id') is not None
                and obj.lugar_incidencia_id == self.context['lugar_default_id']
            ),
        }

        # Para eventos CARACTERIZACION, incluir el conteo de caracterizaciones
        # ya registradas en este punto (precomputado en la view para evitar N+1).
        if obj.tipo_evento_id == "CARACTERIZACION":
            carac_counts = self.context.get("carac_counts", {})
            props["caracterizaciones"] = carac_counts.get(
                obj.id, {"total": 0, "sector": obj.sector_caracterizacion}
            )

        return props
