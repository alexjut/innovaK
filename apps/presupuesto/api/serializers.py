"""Serializers DRF del módulo presupuesto — Etapa B Plan Frontend.

Cobertura read-only de las 5 entidades principales del flujo
presupuestal: Proyecto, Indicador (KPI), AvanceIndicador, Cdp, Contrato.

Las mutaciones (crear/editar/borrar) se siguen haciendo por la UI HTML
del organizador. Esta API REST coexiste para consumo externo (Angular
futuro, móvil, dashboards BI).
"""
from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from apps.presupuesto.models import (
    ActividadPlan,
    AvanceIndicador,
    Indicador,
    Proyecto,
)
from apps.presupuesto.models.core import Contrato
from apps.presupuesto.models.sql import Cdp


# ─────────────────────────────────────────────────────────────────────
# Proyecto
# ─────────────────────────────────────────────────────────────────────

class ProyectoListSerializer(serializers.ModelSerializer):
    """Campos clave para tabla paginada de proyectos."""
    programa = serializers.CharField(source="programa.nombre", read_only=True, default=None)
    subgrupo = serializers.CharField(source="subgrupo.nombre", read_only=True, default=None)
    dependencia = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = ["id", "codigo", "nombre", "programa", "subgrupo", "dependencia"]

    def get_dependencia(self, obj):
        d = obj.dependencia
        return d.nombre if d else None


class ProyectoDetailSerializer(serializers.ModelSerializer):
    """Vista 360° del proyecto: CDPs hijos, metas vinculadas, KPIs, contratos."""
    programa = serializers.SerializerMethodField()
    subgrupo = serializers.SerializerMethodField()
    dependencia = serializers.SerializerMethodField()
    cdps = serializers.SerializerMethodField()
    actividades_plan = serializers.SerializerMethodField()
    indicadores = serializers.SerializerMethodField()
    presupuesto_total_cdps = serializers.SerializerMethodField()

    class Meta:
        model = Proyecto
        fields = [
            "id", "codigo", "nombre",
            "programa", "subgrupo", "dependencia",
            "cdps", "presupuesto_total_cdps",
            "actividades_plan", "indicadores",
        ]

    def get_programa(self, obj):
        if not obj.programa_id:
            return None
        return {"id": obj.programa_id, "nombre": obj.programa.nombre}

    def get_subgrupo(self, obj):
        if not obj.subgrupo_id:
            return None
        return {"id": obj.subgrupo_id, "nombre": obj.subgrupo.nombre}

    def get_dependencia(self, obj):
        d = obj.dependencia
        return {"id": d.id, "nombre": d.nombre} if d else None

    def get_cdps(self, obj):
        return [
            {
                "id": c.id,
                "numero": c.numero,
                "fecha": c.fecha.isoformat() if c.fecha else None,
                "valor": float(c.valor) if c.valor is not None else 0,
                "descripcion": (c.descripcion or "")[:200],
            }
            for c in obj.cdps.all()
        ]

    def get_presupuesto_total_cdps(self, obj):
        total = obj.cdps.aggregate(s=Sum("valor"))["s"] or Decimal("0")
        return float(total)

    def get_actividades_plan(self, obj):
        return [
            {"id": ap.id, "descripcion": ap.descripcion}
            for ap in ActividadPlan.objects.filter(proyecto=obj)
        ]

    def get_indicadores(self, obj):
        rels = Indicador.objects.filter(
            meta_proyecto__proyecto=obj, activo=True,
        ).select_related("meta_proyecto", "meta_proyecto__meta")
        out = []
        for ind in rels:
            mp = ind.meta_proyecto
            meta = mp.meta if mp else None
            acum = AvanceIndicador.objects.filter(
                indicador=ind, activo=True
            ).aggregate(s=Sum("magnitud_aportada"))["s"] or Decimal("0")
            pct = (float(acum) / float(ind.meta_magnitud) * 100) if ind.meta_magnitud else None
            out.append({
                "id": ind.id,
                "nombre": ind.nombre,
                "unidad": ind.unidad_medida,
                "meta_magnitud": float(ind.meta_magnitud or 0),
                "avance_acumulado": float(acum),
                "avance_pct": round(pct, 1) if pct is not None else None,
                "meta_codigo": meta.codigo if meta else None,
                "meta_nombre": meta.nombre if meta else None,
            })
        return out


# ─────────────────────────────────────────────────────────────────────
# Indicador (KPI)
# ─────────────────────────────────────────────────────────────────────

class IndicadorListSerializer(serializers.ModelSerializer):
    """KPI con su avance acumulado calculado en runtime."""
    proyecto_codigo = serializers.SerializerMethodField()
    proyecto_id = serializers.SerializerMethodField()
    meta_codigo = serializers.SerializerMethodField()
    meta_nombre = serializers.SerializerMethodField()
    avance_acumulado = serializers.SerializerMethodField()
    avance_pct = serializers.SerializerMethodField()

    class Meta:
        model = Indicador
        fields = [
            "id", "nombre", "descripcion", "unidad_medida", "meta_magnitud",
            "tipo_agregacion", "activo",
            "proyecto_id", "proyecto_codigo", "meta_codigo", "meta_nombre",
            "avance_acumulado", "avance_pct",
        ]

    def _proy(self, obj):
        mp = obj.meta_proyecto
        return mp.proyecto if mp else None

    def _meta(self, obj):
        mp = obj.meta_proyecto
        return mp.meta if mp else None

    def get_proyecto_id(self, obj):
        p = self._proy(obj)
        return p.id if p else None

    def get_proyecto_codigo(self, obj):
        p = self._proy(obj)
        return p.codigo if p else None

    def get_meta_codigo(self, obj):
        m = self._meta(obj)
        return m.codigo if m else None

    def get_meta_nombre(self, obj):
        m = self._meta(obj)
        return m.nombre if m else None

    def _acum(self, obj):
        return AvanceIndicador.objects.filter(
            indicador=obj, activo=True,
        ).aggregate(s=Sum("magnitud_aportada"))["s"] or Decimal("0")

    def get_avance_acumulado(self, obj):
        return float(self._acum(obj))

    def get_avance_pct(self, obj):
        if not obj.meta_magnitud:
            return None
        return round(float(self._acum(obj)) / float(obj.meta_magnitud) * 100, 1)


class IndicadorDetailSerializer(IndicadorListSerializer):
    """Igual que la list + lista de avances individuales."""
    avances = serializers.SerializerMethodField()

    class Meta(IndicadorListSerializer.Meta):
        fields = IndicadorListSerializer.Meta.fields + ["avances"]

    def get_avances(self, obj):
        return [
            {
                "id": av.id,
                "magnitud_aportada": float(av.magnitud_aportada),
                "fecha_aporte": av.fecha_aporte.isoformat() if av.fecha_aporte else None,
                "periodo": av.periodo,
                "origen": av.origen,
                "evento_id": av.evento_id,
                "evento_nombre": av.evento.nombre if av.evento_id and av.evento else None,
                "observaciones": (av.observaciones or "")[:300],
            }
            for av in obj.avances.filter(activo=True).select_related("evento").order_by("-fecha_aporte", "-id")
        ]


# ─────────────────────────────────────────────────────────────────────
# AvanceIndicador
# ─────────────────────────────────────────────────────────────────────

class AvanceIndicadorListSerializer(serializers.ModelSerializer):
    indicador = serializers.CharField(source="indicador.nombre", read_only=True)
    evento_nombre = serializers.CharField(source="evento.nombre", read_only=True, default=None)

    class Meta:
        model = AvanceIndicador
        fields = [
            "id", "indicador_id", "indicador",
            "evento_id", "evento_nombre",
            "magnitud_aportada", "fecha_aporte", "periodo",
            "origen", "activo", "observaciones",
        ]


# ─────────────────────────────────────────────────────────────────────
# CDP
# ─────────────────────────────────────────────────────────────────────

class CdpListSerializer(serializers.ModelSerializer):
    proyecto_codigo = serializers.CharField(source="proyecto.codigo", read_only=True, default=None)

    class Meta:
        model = Cdp
        fields = [
            "id", "numero", "fecha",
            "valor", "descripcion", "objeto",
            "proyecto_id", "proyecto_codigo",
        ]


class CdpDetailSerializer(CdpListSerializer):
    """CDP con saldo (valor - comprometido en contratos) + lista contratos hijos."""
    saldo_comprometido = serializers.SerializerMethodField()
    saldo_disponible = serializers.SerializerMethodField()
    contratos = serializers.SerializerMethodField()

    class Meta(CdpListSerializer.Meta):
        fields = CdpListSerializer.Meta.fields + [
            "saldo_comprometido", "saldo_disponible", "contratos",
        ]

    def _comprometido(self, obj):
        return obj.contratos.aggregate(s=Sum("valor"))["s"] or Decimal("0")

    def get_saldo_comprometido(self, obj):
        return float(self._comprometido(obj))

    def get_saldo_disponible(self, obj):
        total = obj.valor or Decimal("0")
        return float(total - self._comprometido(obj))

    def get_contratos(self, obj):
        return [
            {
                "id": c.id,
                "tipo": c.contrato_tipo,
                "numero": c.contrato_numero,
                "vigencia": c.contrato_vigencia,
                "valor": float(c.valor) if c.valor is not None else 0,
                "fecha_inicio": c.fecha_inicio.isoformat() if c.fecha_inicio else None,
                "fecha_fin": c.fecha_fin.isoformat() if c.fecha_fin else None,
            }
            for c in obj.contratos.all()
        ]


# ─────────────────────────────────────────────────────────────────────
# Contrato
# ─────────────────────────────────────────────────────────────────────

class ContratoListSerializer(serializers.ModelSerializer):
    cdp_numero = serializers.CharField(source="cdp.numero", read_only=True, default=None)

    class Meta:
        model = Contrato
        fields = [
            "id", "contrato_tipo", "contrato_numero", "contrato_vigencia",
            "objeto", "valor",
            "fecha_inicio", "fecha_fin",
            "cdp_id", "cdp_numero",
            "tipo_contrato", "funcionario", "proveedor_id",
        ]


class ContratoDetailSerializer(ContratoListSerializer):
    """Contrato + sus vinculaciones a actividad_plan."""
    cdp = serializers.SerializerMethodField()
    vinculaciones_actividad = serializers.SerializerMethodField()
    saldo_vinculado = serializers.SerializerMethodField()

    class Meta(ContratoListSerializer.Meta):
        fields = ContratoListSerializer.Meta.fields + [
            "cdp", "vinculaciones_actividad", "saldo_vinculado",
        ]

    def get_cdp(self, obj):
        if not obj.cdp_id:
            return None
        return {
            "id": obj.cdp_id,
            "numero": obj.cdp.numero,
            "valor": float(obj.cdp.valor) if obj.cdp.valor else 0,
        }

    def get_vinculaciones_actividad(self, obj):
        return [
            {
                "id": v.id,
                "actividad_plan_id": v.actividad_plan_id,
                "actividad_plan_descripcion": v.actividad_plan.descripcion if v.actividad_plan_id else None,
                "meta_proyecto_id": v.meta_proyecto_id,
                "concepto_gasto_id": v.concepto_gasto_id,
                "monto": float(v.monto or 0),
                "fecha_inicio": v.fecha_inicio.isoformat() if v.fecha_inicio else None,
                "fecha_fin": v.fecha_fin.isoformat() if v.fecha_fin else None,
                "activo": v.activo,
            }
            for v in obj.vinculaciones_actividad.filter(activo=True).select_related("actividad_plan")
        ]

    def get_saldo_vinculado(self, obj):
        return float(
            obj.vinculaciones_actividad.filter(activo=True).aggregate(s=Sum("monto"))["s"]
            or Decimal("0")
        )
