# Formulación de necesidades

Lo que el área prepara **antes de que exista el contrato**: la necesidad, sus
requisitos, sus soportes, las observaciones de quien revisa y el salto final al
contrato de SECOP. Termina donde empieza `presupuesto`.

## Por qué es una app y no una carpeta de `presupuesto`

Vivió dentro de `apps/presupuesto/` hasta el 2026-10-15, porque el Manual
entregado dice que las ocho apps que propone *«son una separación conceptual, no
una orden de crear ocho apps nuevas»* y que si ya hay apps equivalentes **se
reutilicen**. Se tomó al pie de la letra y quedó escondida: siete modelos, tres
servicios, once rutas y 1.200 líneas de API mezcladas con las 5.000 de
presupuesto, sin nada en `apps/` que dijera que existía.

Alex lo sacó: *«todo lo tenemos de esta forma para la administración a futuro, o
como es más difícil»*. Y es el criterio correcto —el resto del sistema está por
dominio— así que lo conceptual del Manual se respeta igual: Formulación **sigue
siendo un dominio**, nada más que ahora se ve.

## Qué contiene

| | |
|---|---|
| `models.py` | los 7 modelos (`formulacion*`), todos `managed=False` |
| `services/flujo.py` | la máquina de estados: catálogo, transiciones, `cambiar_estado` con sus cinco compuertas, completitud, semáforo, coherencia |
| `services/observaciones.py` | el carril de vuelta: `abierta → respondida → atendida\|desestimada` |
| `services/contrato.py` | el enlace N:M con el contrato de SECOP, en los dos sentidos |
| `api/views.py` | las once vistas |
| `urls.py` | las once rutas — **el prefijo sigue siendo `presupuesto/`**, ver el docstring |
| `scripts/` | el DDL: 019, 037, 038, 039, 040 y sus rollback |
| `tests/` | flujo, carriles, observaciones, contrato |

## Lo que NO está acá, a propósito

- **Los carriles** (`formulador` / `contratacion` / `presupuesto`) viven en
  `apps/login/services/permisos.py`, con el resto del RBAC. Quién puede qué es
  una pregunta de identidad, no de formulación.
- **La auditoría** es `apps/presupuesto/services/auditoria.py`, compartida. Acá
  se la llama con `entidad="formulacion"`.
- **La pantalla** es `frontend/src/app/features/formulacion/`.

## La numeración del DDL es GLOBAL, no por app

`019` y `037–040` están acá, pero el siguiente número lo da el ledger de TODO el
repositorio, no esta carpeta:

    docker exec -i innova_k python manage.py shell < scripts/ledger_ddl.py

El ledger existe porque hubo 92 scripts en 14 carpetas con números repetidos.
Mover estos cinco de carpeta no cambia eso: **nunca se elige el número mirando
un solo directorio.**
