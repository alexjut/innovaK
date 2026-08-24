# Descubrimiento — Completitud del expediente y cascada de ambientes

**Fecha:** 2026-08-24 · **Estado:** evidencia, sin cambios de código.
Todas las cifras están medidas contra la BD y el repositorio, no tomadas de
documentos. Cada afirmación dice cómo se comprobó.

---

## 1 · Arquitectura real de Mi Área

`/app/mi-area/<slug>` → `AREA_ROUTES` → `AreaPanelComponent`
→ `GET /presupuesto/api/areas/<slug|id>/panel/` → `AreaPanelView`
→ `apps/presupuesto/services/panel_area.py`.

**El ancla ya es la correcta y no hay que cambiarla.** `panel_area` deriva todo
de `proyecto.subgrupo_id`, no de `evento.subgrupo_id`. Eso ya resolvió el
problema de las áreas que planean y contratan pero no capturan eventos
(Educación e Infraestructura tenían el panel en blanco).

Ya existe, y hay que reutilizarlo, no reinventarlo:

| Pieza | Dónde | Qué hace |
|---|---|---|
| `panel_area(subgrupo_id)` | `services/panel_area.py` | arma Área → Proyectos → Metas/KPI → Actividades → Contratos + Eventos |
| `sueltos` | mismo servicio | ya expone lo NO enganchado, con `n`, `de`, `que_significa` e `items` |
| `VincularContratoActividadPlanView` | `api/views.py:1643` | ya permite enganchar contrato ↔ actividad desde Mi Área |
| `subgrupos_visibles(user)` | `login/services/scope.py:33` | gate de scope en backend |
| `resolver_area(slug\|id)` | `services/modulos_area.py` | resuelve el slug |
| `EtapaContrato` | `presupuesto/models/core.py:76` | catálogo de 4 etapas, DDL 010 **ya aplicado** |

**`sueltos` es el 80 % de «pendientes» ya construido**, pero a nivel de
RELACIONES (actividad sin contrato, contrato sin actividad…). Lo que falta es
completitud a nivel de CAMPO por contrato.

---

## 2 · Usuario → Subgrupo → Proyecto → Meta → Contrato

```
Usuario ──(scope)──► Subgrupo ──(proyecto.subgrupo_id)──► Proyecto
                                                             │
                        ┌────────────────────────────────────┤
                        ▼                                    ▼
                 ActividadPlan                         ContratoProyecto
                        │                                    │
             ActividadIndicador                          Contrato
                        │                                    │
                   Indicador ──► MetaProyecto ──► Meta       │
                        ▲                                    │
                        └────── ContratoActividadPlan ───────┘
```

**No hay FK directa Contrato → Meta, y no debe crearse.** Ver §4.

---

## 3 · Matriz de procedencia (medida)

Los 25 contratos del sistema, campo por campo:

| Campo | Fuente autoritativa | Modelo.campo | Hoy | Precargable | Editable | Quién |
|---|---|---|---|---|---|---|
| Número / tipo / vigencia | SECOP II | `Contrato.contrato_{tipo,numero,vigencia}` | 25/25 | ya está | no | — |
| Objeto | SECOP II | `Contrato.objeto` | 24/25 | **sí** (`SecopContrato.objeto_contrato`) | no | — |
| Valor | SECOP II | `Contrato.valor` | 22/25 | **sí** (`SecopContrato.valor_contrato`) | no | — |
| Fecha inicio / fin | SECOP II | `Contrato.fecha_{inicio,fin}` | 20/25 | **sí** (`SecopContrato.fecha_*`) | no | — |
| Contratista | SECOP II | `Contrato.proveedor_id` | **0/25** | **sí** (`SecopContrato.proveedor` + `documento_proveedor`) | no | — |
| CDP | interno | `Contrato.cdp_id` | 4/25 | parcial | sí | Subgrupo |
| **Etapa contractual** | **ninguna** | `Contrato.etapa` | **0/25** | **NO** | sí | Subgrupo |
| **Forma de pago** | **ninguna** | *no existe el campo* | — | **NO** | sí | Subgrupo |
| Plan de pago | SECOP II | `SecopPlanPago` | **20/25** | **sí, ya ingerido** | no | — |
| Ejecución financiera | SECOP II | `SecopContrato.valor_pagado` | 25/25 | **sí** | no | — |
| Ejecución técnica (%) | interno | `Contrato.ejecucion` | 4/25 | derivable de KPI (por decidir) | sí | Subgrupo |
| Proyecto | interno | `ContratoProyecto` | 20/25 | no | sí | Subgrupo |
| Actividad del plan | interno | `ContratoActividadPlan` | 5/25 | no | sí | Subgrupo |
| Metas | **derivada** | vía actividad → indicador → meta | 5/25 | **derivada, no se captura** | no | — |

**Cobertura de SECOP, medida:** los **25/25** contratos tienen espejo en
`secop_contrato` (3.073 filas) y **20/25** tienen plan de pago en
`secop_plan_pago` (36.210 filas, 4.889 contratos con referencia parseada).

---

## 4 · Contrato ↔ Meta: la cardinalidad REAL es N, no 1

Medido sobre los 5 contratos que hoy llegan al plan:

| Contrato | Actividades | KPIs | Metas distintas | ¿Determinable? |
|---|---|---|---|---|
| 97 | 3 | 3 | **3** | ✗ ambigua |
| 98 | 7 | 7 | **7** | ✗ ambigua |
| 99 | 2 | 2 | **2** | ✗ ambigua |
| 100 | 2 | 2 | **2** | ✗ ambigua |
| 105 (Educación) | 1 | 2 | **1** | ✓ determinada |

**Conclusión: NO crear una tabla `contrato_meta`, y NO pedirle al usuario que
elija «la» meta.** Un contrato toca N metas y eso es correcto: es plata que
financia varias actividades que aportan a varios indicadores. Un campo escalar
sería una mentira estructural. Lo que falta no es persistencia: es **mostrar el
conjunto** de metas que ya se deriva.

`contrato_proyecto` sí es 1:1 hoy (los 20 contratos tienen exactamente 1
proyecto), pero la tabla admite N y no conviene asumir 1.

---

## 5 · El «24/25» del dashboard

Confirmado y explicado:

- `contrato_proyecto`: 20 filas, 20 contratos distintos
- `contrato_actividad_plan` (activas): 15 filas, **5** contratos distintos
- **unión = 24 de 25**; **1 contrato sin ninguna vía**

Se resuelve desde Mi Área con el endpoint que ya existe. No hacen falta mappings.

---

## 6 · Lo que realmente falta persistir

| Necesidad | ¿Falta modelo? | Evidencia |
|---|---|---|
| Etapa contractual | **NO** | `EtapaContrato` + `Contrato.etapa/etapa_fecha/etapa_usuario` ya existen (DDL 010 aplicado 2026-08-23). Está en 0/25 porque **nadie la ha capturado**, no porque falte dónde |
| Plan de pago | **NO** | `SecopPlanPago` ingerido, 20/25 cubiertos |
| Contrato ↔ Meta | **NO** | derivable; ver §4 |
| **Forma de pago** | **SÍ** | no existe el campo en ninguna tabla ni en SECOP. `SecopContrato.modalidad` es modalidad de *contratación*, no forma de pago |
| **Auditoría genérica** | **SÍ** | no hay tabla de auditoría. Sólo columnas de rastro por campo (`etapa_usuario_id`, `etapa_fecha`) y `created_at/updated_at` sueltos. `AuditoriaPertenencia` es de permisos, no sirve |
| Ejecución técnica | **por decidir** | `Contrato.ejecucion` existe (4/25). Antes de volverlo captura manual hay que decidir si se deriva de los KPIs |

---

## 7 · Brain / Obsidian

**No existe.** No hay `brain/`, `knowledge/`, `obsidian/`, `vault/` ni ningún
`.obsidian/`. Lo que hay es `docs/` con 12 subcarpetas ya pobladas y bien
mantenidas (`arquitectura/`, `referencia/`, `operacion/`, `propuestas/`,
`manuales_modulos/`, `_historico/`…).

**Recomendación:** el Brain nace como `brain/` con enlaces `[[wiki]]` y
**apunta** a `docs/`, sin copiar. Duplicar el contenido de `docs/` en el vault
crearía dos fuentes que se separarán.

---

## 8 · Spec Kit

**No existe.** Ni `.specify/`, ni `specs/`, ni nada equivalente. Se integra
desde cero. `CLAUDE.md`, `.claude/agents`, skills y `docs/` quedan intactos.

---

## 9 · Flujo REAL Desarrollo → Pruebas → Producción

**No existe un flujo de despliegue. Existen tres ramas de git y nada al otro
lado.** Evidencia:

1. **Las tres ramas tienen el MISMO árbol**: `desarrollo`, `Pruebas` y
   `produccion` comparten el hash de árbol `0831ed0f9a3b986ab24da3851ddeba67bf9271f2`.
   `git diff` entre cualquier par: **cero diferencias**. Los 3 y 6 commits de
   «adelanto» son sólo comisiones de merge.
2. **Hay UN solo checkout del repositorio en el host** (`/home/innova/Proyectos/innovaK`)
   y **UN solo contenedor** `innova_k`.
3. `docker-compose.yml` monta el código: `volumes: - .:/app`. El contenedor
   sirve **el working tree**, sea cual sea la rama que esté checkouteada.
4. Ahora mismo el checkout está en `feat/expediente-contrato-completo` — o sea
   que lo que corre **no es `produccion`**.
5. **No hay CI.** No hay `.github/workflows`, ni GitLab CI, ni Jenkins. Sólo un
   hook local `pre-push` que corre los tests.

---

## 10 · Por qué los cambios no cascadean — la causa concreta

**El frontend no viaja con el repositorio.**

- `frontend/dist` está en `frontend/.gitignore` (línea 4).
- Archivos de `dist` en el índice de git: **0**. En disco: **147**.
- `apps/login/views/spa.py` sirve la SPA leyendo
  `frontend/dist/innovak-frontend/browser/` del filesystem.
- El propio docstring de esa vista dice: *«Para rebuildear, en el host:
  cd frontend && npm run build -- --base-href=/app/»* — un paso **manual**.
- El dossier de k8s (`docs/infra/despliegue_kubernetes.md`, 2026-06-24) ya lo
  había advertido: *«El Dockerfile no compila la SPA Angular; hoy ese build se
  hace aparte en el server»*.

De ahí sale el síntoma exacto que se reporta: **lo que no aparece es Dashboard,
Mi Área, estilos, accesibilidad y SCSS — todo frontend.** Los cambios de
backend sí «cascadean», porque el código Python está bind-mounteado y basta un
`git checkout` + restart.

**No es un problema de git. Es que no hay pipeline ni artefacto versionado.**

---

## 11 · Riesgos antes de tocar producción

| Riesgo | Por qué | Mitigación |
|---|---|---|
| **La BD es única y compartida** | `managed=False`, PostgreSQL externa en `10.100.102.12`. No hay BD por ambiente: un DDL afecta a todos a la vez | Todo DDL con backup <24h y OK explícito. Migraciones aditivas y nullable |
| **`contrato.id` no tiene secuencia** | deuda S5 conocida | No insertar contratos nuevos sin el fallback |
| **Un solo host** | separar ambientes es infraestructura nueva, no un cambio de código | La fase de ambientes es un proyecto propio, no un apéndice |
| **Escritura sin scope de contrato** | `VincularContratoActividadPlanView` valida la actividad pero **no el contrato**: un usuario de Educación puede enganchar un contrato de Seguridad a su plan | **Arreglar antes de abrir más escritura desde Mi Área** |
| **`frontend/dist` sin versionar** | cualquier despliegue nuevo hereda el problema | Multi-stage build en el Dockerfile |
| **Sin auditoría genérica** | los campos manuales nuevos nacerían sin rastro | Diseñar la auditoría **antes** que los formularios |

---

## 12 · Plan por fases, corregido por lo que se encontró

El descubrimiento **encoge** la fase de modelo y **agranda** dos que no estaban
dimensionadas (seguridad de escritura y auditoría).

| # | Fase | Qué cambia respecto al plan original |
|---|---|---|
| 0 | **Cerrar el hueco de scope** | *Nuevo, y va primero.* `VincularContratoActividadPlanView` no valida que el contrato sea del área. Abrir más escritura desde Mi Área sin esto multiplica el problema |
| 1 | Brain | `brain/` que **apunta** a `docs/`, sin copiar. Notas destiladas + la matriz de §3 |
| 2 | Spec Kit | desde cero. `constitution` + spec `completitud-expediente-subgrupos` |
| 3 | **Auditoría genérica** | *Antes que los formularios.* Hoy no existe; si nacen los campos manuales primero, nacen sin rastro |
| 4 | Modelo | **mucho menos de lo previsto**: sólo `forma_pago`. Etapa, plan de pago y contrato↔meta ya están resueltos |
| 5 | Precarga | servicio que llena desde `secop_contrato` los 3 valores, 5 fechas y **25 contratistas** que faltan. Es el mayor golpe de completitud y **no requiere un solo formulario** |
| 6 | Mi Área — completitud por contrato | ficha contrato a contrato sobre `panel_area`, reutilizando `sueltos` |
| 7 | Dashboard 360° | consumir etapa y forma de pago. El stepper ya existe y lee `Contrato.etapa` |
| 8 | Segundo subgrupo | Seguridad (3 proyectos) o Infraestructura (2). Educación tiene 1 proyecto y 1 contrato: es el piloto más pequeño, no el más representativo |
| 9 | Ambientes | multi-stage build + artefacto versionado + identificación de versión |
| 10 | Brain final | decisiones y operación |

**Ojo con el piloto:** el enunciado esperaba «3 proyectos, 5 contratos» en
Educación. Lo medido es **1 proyecto (2805 «Kennedy Germinando Futuros») y 1
contrato (105, CIA 773/2025, $23.168.769.452)**. Educación sirve para probar la
mecánica, pero no ejercita la cardinalidad N. El segundo subgrupo no es
opcional: es donde se valida de verdad.
