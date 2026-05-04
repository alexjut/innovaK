# Importa todos los modelos desde sus submódulos
# M1: karacterizacion eliminado — los modelos `CaracterizacionCultura` y
# `CaracterizacionDeporte` ahora viven en `apps.caracterizacion.models`
# (schema vivo post-N12).
from .kasistencia import *
from .kdocumentos import *
from .kregistro import *