"""Serializers DRF — apps.login (Etapa B Plan Frontend).

Contratos JSON estables para clientes Angular. Mantener compatibilidad
hacia atrás al cambiar campos (sumar OK, renombrar/quitar requiere bump
de versión del endpoint).
"""
from rest_framework import serializers


class InscripcionPublicaSerializer(serializers.Serializer):
    """Inscripción pública a un evento (QR escaneado por participante).

    Contrato del endpoint `POST /api/eventos/<id>/inscripciones/`. Se
    mapea 1:1 al service `apps.login.services.inscripcion_evento.
    inscribir_persona` que ejecuta los 3 INSERTs atómicos
    (persona → participante → participante_evento).

    Los campos opcionales se aceptan vacíos y se normalizan a `None`
    antes de pasar al service. Las normalizaciones JSON-friendly viven
    en el método `validated()` que devuelve el dict listo para el
    service.
    """

    # Obligatorios
    nombre1 = serializers.CharField(max_length=120)
    apellido1 = serializers.CharField(max_length=120)

    # Datos personales opcionales
    nombre2 = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    apellido2 = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    fecha_nacimiento = serializers.DateField(required=False, allow_null=True)
    sexo_biologico = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    identidad_genero = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    orientacion_sexual = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    grupo_etnico = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    discapacidad = serializers.BooleanField(required=False, default=False)

    # Contacto / ubicación
    documento = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    telefono = serializers.CharField(max_length=30, required=False, allow_blank=True, allow_null=True)
    correo = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    upz = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    barrio = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)

    def to_service_kwargs(self) -> dict:
        """Convierte validated_data al dict que espera el service.

        Strings vacíos → None (excepto nombre2/apellido2 que el service
        normaliza a '' por DDL no-null).
        """
        data = self.validated_data
        normalizados = {
            'nombre1': data['nombre1'],
            'nombre2': data.get('nombre2', '') or '',
            'apellido1': data['apellido1'],
            'apellido2': data.get('apellido2', '') or '',
            'fecha_nacimiento': data.get('fecha_nacimiento'),
            'sexo_biologico': data.get('sexo_biologico') or None,
            'identidad_genero': data.get('identidad_genero') or None,
            'orientacion_sexual': data.get('orientacion_sexual') or None,
            'grupo_etnico': data.get('grupo_etnico') or None,
            'discapacidad': bool(data.get('discapacidad', False)),
            'documento': (data.get('documento') or '').strip() or None,
            'telefono': (data.get('telefono') or '').strip() or None,
            'correo': (data.get('correo') or '').strip() or None,
            'upz': (data.get('upz') or '').strip() or None,
            'barrio': (data.get('barrio') or '').strip() or None,
        }
        return normalizados


class InscripcionResultadoSerializer(serializers.Serializer):
    """Respuesta del endpoint de inscripción pública.

    Devuelve los 3 ids creados. El cliente puede confirmar la
    inscripción contra cualquiera de ellos.
    """
    persona_id = serializers.IntegerField()
    participante_id = serializers.IntegerField()
    participante_evento_id = serializers.IntegerField()


# ─────────────────────────────────────────────────────────────────────────
# PR-B Curso Docente — sesiones + asistencia
# ─────────────────────────────────────────────────────────────────────────


class ClaseSerializer(serializers.Serializer):
    """Contrato JSON de una sesión del curso."""
    id = serializers.IntegerField(read_only=True)
    evento_id = serializers.IntegerField(read_only=True)
    fecha = serializers.DateField()
    hora_inicio = serializers.TimeField(required=False, allow_null=True)
    hora_fin = serializers.TimeField(required=False, allow_null=True)
    lugar = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    nombre = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SesionesCrearSerializer(serializers.Serializer):
    """Bulk create: lista de sesiones a crear para un curso."""
    sesiones = ClaseSerializer(many=True, min_length=1)


class MarcaAsistenciaSerializer(serializers.Serializer):
    """Marca individual de asistencia en el bulk POST."""
    participante_id = serializers.IntegerField()
    presente = serializers.BooleanField(default=False)
    observacion = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TomarListaSerializer(serializers.Serializer):
    """Bulk upsert de asistencia para una sesión (Clase)."""
    fecha = serializers.DateField(required=False, allow_null=True,
                                  help_text="Si se omite, se usa clase.fecha")
    marcas = MarcaAsistenciaSerializer(many=True, min_length=0)


class AsistenciaMarcaSerializer(serializers.Serializer):
    """Marca persistida (respuesta GET)."""
    id = serializers.IntegerField(read_only=True)
    clase_id = serializers.IntegerField(read_only=True)
    participante_id = serializers.IntegerField()
    fecha = serializers.DateField()
    asistencia = serializers.BooleanField()
    observaciones = serializers.CharField(allow_null=True)
