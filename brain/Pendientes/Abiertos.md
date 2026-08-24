# Pendientes abiertos

> Al 2026-08-24. Lo ya decidido vive en las notas de decisión:
> [[2026-08-24-contrato-meta-derivada]] · [[2026-08-24-precarga-antes-que-formulario]] ·
> [[2026-08-24-auditoria-antes-que-captura]]

## Bloquean la fase de completitud

| | Qué | Por qué importa |
|---|---|---|
| 🔴 | **Scope de contrato en escritura** | `VincularContratoActividadPlanView` no valida que el contrato sea del área. Cerrar **antes** de abrir más escritura. Ver [[Scope-por-subgrupo]] |
| 🔴 | **Auditoría genérica** | no existe; ver [[Auditoria]] |
| 🟠 | **Forma de pago** | único campo que de verdad falta persistir. No está en ninguna tabla ni en [[SECOP]] |
| 🟠 | **Ejecución técnica** | decidir si se deriva de los KPIs o es captura propia. `Contrato.ejecucion` existe (4/25) |

## Ambientes

| | Qué |
|---|---|
| 🔴 | `frontend/dist` sin versionar → el frontend no viaja con el repo. Ver [[Ambientes-y-despliegue]] |
| 🟠 | Sin CI, sin artefacto promovible, sin identificación de versión por ambiente |
| 🟠 | Un solo checkout y un solo contenedor para dos personas |

## Datos

| | Qué |
|---|---|
| 🟠 | **1 contrato de 25** no llega a ningún proyecto ni actividad |
| 🟠 | `Contrato.cdp_id` en 4/25 |
| 🟡 | Catálogo `Objetivo`: 4 de 6 filas se llaman «prueba»; 3 de 12 proyectos tienen objetivo |
| 🟡 | Proyecto `000007895` es registro de prueba confirmado; espera respuesta del Despacho sobre su CDP 1486 |

## Calidad

| | Qué |
|---|---|
| 🟡 | 198 parejas de contraste en línea base, marcadas `PENDIENTE DE REVISAR`. No es deuda nueva: es deuda que antes no se veía |
| 🟡 | La reducción de **−168 px** sale de valores declarados, **no** de medición en navegador. El intento con Chromium falló por red |
| 🟡 | Auditoría del expediente **incompleta**: 11 agentes de 25 terminaron, 14 murieron por límite de sesión |
| 🟡 | `ENTIDADES` en `presupuesto.types.ts` — 55 de 77 líneas, sin consumidores. Alex autorizó borrarlo con TS + tests + build en verde |
