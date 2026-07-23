# Plan funcional — Alineación innovaK ↔ Visor SDP-PDL (Planeación) + conexión total de la cadena + limpieza

> Consolidado de 3 análisis expertos (BD/datos, arquitectura, limpieza) verificados
> contra la BD viva y el código en `produccion` (2026-07-23). Este documento reemplaza
> al brief anterior: separa lo verificado de lo que falta decidir, y baja todo a fases
> **funcionales y cascadeables a producción**.

---

## 0. La idea en una frase

Hoy la cadena `Proyecto → Meta → CDP → Contrato → ActividadPlan → Evento → Beneficiarios`
**existe** pero está **mayormente desconectada**, y **no engancha con lo oficial del
Distrito (Planeación/SDP)**. "Lo que falta" = poblar el enganche a Planeación
(`metas.codigo_meta`) + ingerir los datos oficiales + reconectar los huérfanos. Con eso
innovaK deja de "inspirarse" en el visor y pasa a **compararse contra lo oficial**.

---

## 1. 🔴 URGENTE / LEGAL — antes de cualquier otra cosa

**Datos personales reales en el repositorio PÚBLICO** (habeas data, Ley 1581):

| Archivo (raíz, tracked) | Contenido |
|---|---|
| `personas_con_documento.csv` | **4383 filas**: cédulas + nombres completos reales |
| `ultimos_200.csv` | 201 filas (cédulas/nombres) |
| `personas_esta_semana.csv` | 1 fila |

Borrarlos del HEAD **no basta** — quedan en el historial de git público. Requiere purga
de historial (`git filter-repo`) + reescritura del remoto, junto con el ítem **P1** de
`DEUDA_TECNICA.md`. **Decisión de Alex.** Es el hallazgo más grave del barrido.

---

## 2. Estado real de la conexión (auditoría de huérfanos, BD viva)

| Eslabón | Desconectado hoy |
|---|---|
| Metas **sin código oficial** (`metas.codigo_meta`) → cruce con Planeación | **24/24 = 100%** 🔴 |
| Contratos **sin CDP** (dinero no traza al plan) | **100/104 = 96%** 🔴 |
| Contratos legacy sin valor **y** sin CDP | **96** |
| Eventos **sin actividad_plan** (no suben al KPI) | **33/52 = 63%** |
| Actividades del plan **sin KPI** | **42/60 = 70%** |

Solo **19/52 eventos (37%)** trazan hasta un KPI; **0** llegan a la meta oficial.
**La estructura está bien hecha; es un problema de conectar/poblar datos, no de reconstruir.**

---

## 3. Hallazgos que corrigen el brief

- **La llave a Planeación NO es `meta_proyecto.codigo`** (esa tabla no tiene código).
  Es **`metas.codigo_meta` (varchar)** — mismo nombre que el CSV del Distrito, **hoy 100% NULL**.
- **`proyecto.codigo` SÍ trae códigos oficiales** (2780, 2784, 2788…) → el cruce a nivel
  **proyecto** ya es posible hoy; falta cerrarlo a nivel **meta**.
- **D1 "Formulación → Publicación de adjudicación" NO es un renombre** — la palabra
  aparece **0 veces**. Es una **feature nueva pequeña**: el "estado de contratación" del
  visor no existe (contrato no tiene campo `estado`). Nace ya con el nombre correcto.
- **D4 ya está separado** (SIPSE presupuestal vs actividad SIPSE). Falta solo que SIPSE
  sea **columna real** (hoy es anotación en seeds).
- **innovaK YA usa DRF** (el CLAUDE.md §7 "Sin DRF" está desactualizado). Todo lo nuevo
  va sobre la capa DRF.
- **Gran parte del "visor" ya está construida**: 360° del proyecto, cockpit ejecutivo,
  "avance por sector" (`top_sectores_avance`), cadena visual.

---

## 4. Plan por fases (funcional, cascadeable, bajo riesgo)

Orden pensado para que cada fase **se vea funcionando** y desbloquee la siguiente.
Las fases sin DDL son inmediatas; las que tocan BD externa necesitan **OK de Alex + backup**.

| Fase | Qué | DDL? | Desbloquea |
|---|---|---|---|
| **0** | Purga de los CSV con datos personales del historial (con P1) | No (git) | Legal / limpieza |
| **1** | **Ingesta Planeación**: 2 tablas espejo (`sdp_meta_oficial`, `sdp_contrato_oficial`) + comando `ingest_sdp_datos_abiertos` (idempotente, filtra Kennedy=8) | **Sí** | El cruce con lo oficial |
| **2** | **Poblar `metas.codigo_meta`** con el SEGPLAN oficial (24 metas) | Sí (UPDATE) | Trazabilidad meta→Planeación |
| **3** | **Capa de comparación**: servicio/endpoint que cruza interno vs oficial por `codigo_meta`/`codigo_proyecto` y calcula deltas | No | El "compararse contra lo oficial" |
| **4** | **Reordenar el hub Presupuesto** como el visor (Planeación/Contratación/Seguimiento) — solo front | No | Alineación visual D5 |
| **5** | **Avance por sector** (D7) reusando `top_sectores_avance` + drill-down | No | Dashboard por sector |
| **6** | **Estado de contratación** (catálogo + `contrato.estado_codigo`) → "Publicación de adjudicación" en 360° y cockpit | **Sí** | D1 real |
| **7** | **Reconectar huérfanos**: campañas para vincular contratos↔CDP, actividades↔KPI, eventos↔actividad_plan; y hacer el KPI obligatorio en captura | Depende | "todo conectado" real |
| **8** | **Evidencias** (P4): tabla `documento_proceso` en `apps/documentos`, polimórfica, reusa Mongo cifrado + `TipoArchivo` | **Sí** | D2/D3 |
| **9** | **Exportes alineados a SEGPLAN** (D6) — cuando (3) esté estable | No | Reporte institucional |
| **10** | **Limpieza** del fósil pre-Angular (`static/node_modules` 4019 archivos, `static/js/*`, `estructura.txt`, `votaciones.tar.gz`) + `.pyc`/`staticfiles` root-owned (sudo) | No | Higiene |
| — | **Consulta inteligente ampliada** (D8) — paralelo, independiente | No | KENNY |

---

## 5. Lo que necesito de ti (decisiones que bloquean)

| # | Necesito | Para |
|---|---|---|
| A | **OK para purgar los CSV** de datos personales del historial (junto con P1) | Fase 0 (urgente) |
| B | **Los CSV oficiales** del Distrito (o confirmar que los descargo yo) — Proyectos Desarrollo Local + Contratos + presupuesto_x_meta | Fases 1-2 |
| C | **El mapeo `metas.codigo_meta`**: ¿tienes qué código SEGPLAN va a cada una de las 24 metas, o lo derivamos del CSV por proyecto? | Fase 2 |
| D | **P1**: ¿qué es "RAN" en la consulta inteligente? | D8 |
| E | **P2**: ¿"Banco de Iniciativas" se renombra o se queda? | ortogonal |
| F | **P3/P4**: matriz de riesgo/SECOP y evidencias — ¿captura nueva o solo link? (el experto recomienda tabla `documento_proceso` reusando Mongo) | Fase 8 |

---

## 6. Basura a quitar (inventario verificado)

**Seguro (sin OK):** `static/js/Untitled-1` (0 bytes) · `static/node_modules/` (4019
archivos tracked por error). **Seguro tras confirmar:** `static/js/*` y `static/dist/js/*`
(frontend pre-Angular, 0 referencias) · `estructura.txt` (snapshot de abril, engañoso) ·
`votaciones.tar.gz` · backup SQL de `escuelas_staging`. **Requiere sudo:** `__pycache__`
y `staticfiles/` root-owned. **NO tocar:** `static/dist/css/base.css` (vivo, lo usa
`scan.html` + cache-buster).

> Ya confirmado que `apps/kordial`, `apps/VitalK`, `apps/documento` **ya no existen**
> (la bitácora estaba vieja). Templates legacy: solo 3, todos vivos.

---

## 7. Arranque recomendado

**Hoy mismo, sin esperar nada** (cero riesgo, cero DDL): Fase 4 (reordenar hub como el
visor) + Fase 5 (avance por sector) + limpieza Tier 1 de basura. En paralelo, tú
consigues los CSV oficiales (B) y decides A/C. Con eso arrancamos la parte pesada
(ingesta Planeación + poblar código + capa de comparación), que es "la línea que falta".
