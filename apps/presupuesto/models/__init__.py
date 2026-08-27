from .core import (
    FormaPago,
    Proyecto, Actividad, ActividadPlan,
    EtapaContrato,
    Contrato, ContratoProyecto, ContratoActividad,
    TramoVialContrato, IntervencionParque, CorteAvanceObra,
)
from .indicadores import (
    MetaBD, MetaProyectoBD,
    Indicador, ActividadIndicador, AvanceIndicador,
)
from .sql import ContratoActividadPlan
from .sdp_oficial import SdpMetaOficial
from .auditoria import AuditoriaDato
from .plan_pago import ContratoPlanPago
from .secop import SecopContrato, SecopPlanPago, tabla_plan_pago_existe
# Se exporta acá A PROPÓSITO. `financiero.py` no está en este archivo y por eso
# sus cinco modelos —ProyectoInversion, PresupuestoProyecto, PresupuestoTiempo…—
# no quedan registrados al arrancar Django: son invisibles para `get_models()`,
# para el admin y para cualquier auditoría automática. No repetir ese olvido.
from .formulacion import (
    EstadoFormulacion, TransicionFormulacion, Formulacion,
    RequisitoFormulacion, RequisitoCumplido, DocumentoFormulacion,
    FormulacionContrato,
)

__all__ = [
    "SdpMetaOficial",
    "EstadoFormulacion", "TransicionFormulacion", "Formulacion",
    "RequisitoFormulacion", "RequisitoCumplido", "DocumentoFormulacion",
    "FormulacionContrato",
    "AuditoriaDato", "FormaPago", "ContratoPlanPago",
    "SecopContrato", "SecopPlanPago", "tabla_plan_pago_existe",
    "Proyecto", "Actividad", "ActividadPlan", "EtapaContrato",
    "Contrato", "ContratoProyecto", "ContratoActividad",
    "TramoVialContrato", "IntervencionParque", "CorteAvanceObra",
    "ContratoActividadPlan",
    "MetaBD", "MetaProyectoBD",
    "Indicador", "ActividadIndicador", "AvanceIndicador",
]
