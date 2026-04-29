# Plan de siembra demo + integración con PRs del Dashboard

> **Fecha:** 2026-04-23
> **Rama:** `feat/mapa-kennedy-dashboard`
> **Estado:** plan para revisión — NO ejecutado todavía.

## 1. Objetivo

Transformar el dashboard ejecutivo (`/dashboard/presupuesto/`) de demo pobre
(6 KPIs, 3.9% promedio) a demo "WOW" creíble para jefes de Alcaldía, con
cantidad y calidad de datos comparable a un Power BI real.

## 2. Principios de seguridad

1. **Prefijo `DEMO_`** en todo nombre de proyecto / meta / KPI / evento
   sembrado. Permite identificar y borrar con `WHERE nombre LIKE 'DEMO_%'`.
2. **IDs ≥ 100000** donde haya secuencia controlable (sin chocar con
   data real; el MAX actual más alto es `proyecto.id=2807`).
3. **Script idempotente**: re-ejecutable con `ON CONFLICT DO NOTHING`.
4. **Todo en `apps/dashboard/scripts/seeds/`** — carpeta nueva, aislada.
5. **Script `cleanup_demo.py`** escrito antes que los de siembra, para
   garantizar rollback.
6. **Backup BD pre-siembra** obligatorio antes de ejecutar.

## 3. Inventario de schemas verificados (2026-04-23)

### 3.1 Tablas de presupuesto

```
proyecto                      rows=8    MAX(id)=2807
  id, codigo, nombre, nombre_ci, dependencia_id, subgrupo_id, programa_id
  ⚠ NO tiene fecha_inicio/fecha_fin propios.

metas                         rows=10   MAX(codigo)=10
  codigo (PK INTEGER), musi, codprog, nomprog, codproy, nomproy,
  componente, anualizacion, nombre, linea, concepto, sector,
  codind, nomind, link, proyecto_id, codigo_meta, descripcion, proyecto_codigo
  ⚠ PK es `codigo` (no `id`).

meta_proyecto                 rows=9    MAX(id)=11
  id, meta_id (NOT NULL FK metas.codigo), proyecto_id (NOT NULL FK),
  fecha_inicio (DATE null), fecha_fin (DATE null)
  ⚠ Ambas fechas están NULL en todos los 9 rows existentes.

presu_indicador_meta_proyecto rows=6    MAX(id)=6
  id (BIGINT), meta_proyecto_id (NOT NULL), nombre, descripcion,
  unidad_medida, meta_magnitud (NUMERIC), tipo_agregacion, activo,
  eliminado_en, created_at, updated_at

presu_avance_ind_periodo      rows=7    MAX(id)=7
  id, indicador_id (NOT NULL FK presu_indicador_meta_proyecto.id),
  evento_id (null), magnitud_aportada (NOT NULL), fecha_aporte,
  periodo (VARCHAR, formato 'YYYY-MM'), observaciones, origen,
  activo, eliminado_en, created_at, updated_at

actividad_plan                rows=42   (usa BIGINT id)
  id, proyecto_id, descripcion, descripcion_ci, actividad_id

presu_impacto_actividad_indicador rows=5
  id, actividad_plan_id, indicador_id, cantidad_aportada,
  evidencia_url, registrado_en, registrado_por

⚠ NO EXISTE: presu_proyecto, presu_actividad_plan (nombres del prompt
  que resultaron inexistentes — los reales son `proyecto` y `actividad_plan`).
```

### 3.2 Tablas de eventos

```
evento                        rows=46   MAX(id)=61
  id, nombre, tipo_evento_codigo (VARCHAR FK tipo_evento.codigo),
  lugar_incidencia_id, fecha_inicio, fecha_fin, activo,
  dependencia_id, subgrupo_id, funcionario_id, actividad_plan_id,
  descripcion, created_at, updated_at, indicador_id, magnitud_aportada
  ⚠ Conecta directamente al KPI con indicador_id + magnitud_aportada.

tipo_evento                   rows=4    PK=codigo (VARCHAR)
  codigo, nombre, descripcion, activo
  Valores: CAPACITACION, CURSO, ENTREGA, INFO_TERRENO

evento_info_terreno           rows=1    PK=evento_id (1:1)
  evento_id, hallazgos, recorrido, observaciones,
  lat_confirmacion, lon_confirmacion, timestamp_llegada, confirmado,
  created_at, updated_at

documento_evento              rows=2    MAX(id) n/d
  id, evento_id, tipo_archivo_id, nombre_archivo, archivo, fecha_subida

tipo_archivo                  rows=1    PK=id
  id, nombre
  ⚠ Solo tiene (id, nombre) — sin columna 'codigo'.
```

### 3.3 Cadena geográfica (necesaria para evento.lugar_incidencia_id)

```
lugar_incidencia              rows=12   MAX(id)=12
  id, geo_referenciacion
  ⚠ Sin secuencia nativa. Crear via helper crear_con_fallback_id()
  que ya arreglamos en PR1 (savepoint + MAX(id)+1 + force_insert).

geo_referenciacion            rows=248  MAX(id)=548
  id, latitud, longitud, lugar_id, persona_id, direccion_texto,
  formatted_address, fuente, precision, ...
  ✓ Secuencia reseteada hoy, inserts normales funcionan.

lugar                         rows=224
  Usar get_lugar_generico() para el lugar singleton.
```

### 3.4 Catálogos ya disponibles (no se tocan, solo se usan)

```
dependencia                   rows=5
  id=1 INSPECCIONES DE POLICIA
  id=2 DESPACHO
  id=3 INVERSIÓN LOCAL              ← principal para eventos demo
  id=4 ADMINISTRATIVO Y FINANCIERO
  id=5 GESTIÓN POLICIVA Y JURÍDICA

subgrupo                      rows=44
  Para dep=3 (Inv. Local) hay 15 subgrupos:
  Cultura(1), Deporte(2), Participación(3), Buen trato(4), Seguridad(5),
  Subsidio tipo C(6), Educación(8), Ambiente(10), Reactivación Económica(35),
  Coordinación Inversión Local(36), Infraestructura(37), Seguridad(38),
  Acuerdos ciudadanos(39), Mujer(40), Paz Memoria y Reconciliación(41).

funcionario                   rows=18
  3 originales + 15 de Javier Aguilar (uno por cada subgrupo de Inv. Local).

upz                           rows=12   (solo Kennedy, localidad=8)
  codigo=44 AMERICAS, 45 CARVAJAL, 46 CASTILLA, 47 KENNEDY CENTRAL,
  48 TIMIZA, 78 TINTAL NORTE, 79 CALANDAIMA, 80 CORABASTOS,
  81 GRAN BRITALIA, 82 PATIO BONITO, 83 LAS MARGARITAS, 113 BAVARIA.
  ⚠ PK es codigo (no id).
```

## 4. Plan de siembra en 6 fases

### Fase A — 10 proyectos DEMO (id ≥ 100000)

**Tabla:** `proyecto`

Proyectos inspirados en ejes reales de Alcaldía Kennedy:

| id     | código        | nombre                                          | dependencia_id |
|--------|---------------|-------------------------------------------------|----------------|
| 100001 | DEMO_FI       | DEMO_ Fortalecimiento Institucional             | 3              |
| 100002 | DEMO_MV       | DEMO_ Malla Vial y Movilidad Segura             | 3              |
| 100003 | DEMO_CUL      | DEMO_ Cultura, Recreación y Deporte             | 3              |
| 100004 | DEMO_MUJ      | DEMO_ Mujer y Equidad de Género                 | 3              |
| 100005 | DEMO_SEG      | DEMO_ Seguridad y Convivencia                   | 3              |
| 100006 | DEMO_AMB      | DEMO_ Ambiente y Arbolado Urbano                | 3              |
| 100007 | DEMO_EDU      | DEMO_ Educación y Formación Ciudadana           | 3              |
| 100008 | DEMO_INF      | DEMO_ Infraestructura Comunitaria               | 3              |
| 100009 | DEMO_JOV      | DEMO_ Juventud y Oportunidades                  | 3              |
| 100010 | DEMO_PAZ      | DEMO_ Paz, Memoria y Reconciliación             | 3              |

Se dejan `subgrupo_id`, `programa_id` en NULL (no son requeridos y los
proyectos reales están así).

### Fase B — 10 entradas en `metas` (PK=codigo) + 30 `meta_proyecto`

**Tabla:** `metas` (10 nuevos, `codigo` ≥ 100)

Una meta PDD por proyecto (10 metas):
- `codigo` en rango 100..109
- `nombre` = "DEMO_ Meta <sector> 2025-2026"
- `proyecto_id` = el DEMO_ correspondiente (100001..100010)
- `sector`, `componente`, `nombre`, `descripcion` con texto realista
- `anualizacion` = '{"2025": 30, "2026": 70}' (string JSON-like como el real)

**Tabla:** `meta_proyecto` (30 nuevos, id ≥ 100000)

3 meta_proyecto por cada meta (variedad de vigencia):

| Grupo        | Cantidad | fecha_inicio | fecha_fin  | Semántica         |
|--------------|----------|--------------|------------|-------------------|
| Vigencia 2025 (cumplidas) | 10 | 2025-01-01 | 2025-12-31 | Al 85-100% |
| Vigencia 2026 (en curso)  | 15 | 2026-01-01 | 2026-12-31 | Variedad 10-70% |
| Vigencia 2026-27 (iniciando) | 5 | 2026-06-01 | 2027-12-31 | 0-20% |

### Fase C — 35 KPIs DEMO (`presu_indicador_meta_proyecto`, id ≥ 100000)

**Tabla:** `presu_indicador_meta_proyecto`

Distribución por meta_proyecto (promedio 1.17 KPIs/meta):

| meta_proyecto     | # KPIs por meta | Diversidad |
|-------------------|-----------------|------------|
| 10 metas 2025     | 1 c/u (10)      | Uno por meta, al 85-100% |
| 15 metas 2026     | 1-2 c/u (20)    | Variedad 10-70% |
| 5 metas 2026-27   | 1 c/u (5)       | 0-20% |

Unidades variadas para rica visualización:
- `personas` (capacitadas, atendidas, beneficiadas)
- `eventos`, `talleres`, `visitas`, `jornadas`
- `kits`, `bonos`, `ayudas`, `subsidios`
- `árboles`, `metros`, `obras`, `intervenciones`
- `denuncias_atendidas`, `mediaciones`, `conflictos_resueltos`

Magnitudes variadas (10 a 10,000) con `tipo_agregacion='SUMA'` para
todos (consistente con los existentes).

### Fase D — 55 eventos DEMO (`evento`, id ≥ 100000)

**Tabla:** `evento` + `lugar_incidencia` + `geo_referenciacion`

**Distribución temporal (6 meses):**

| Mes        | # eventos |
|------------|-----------|
| Oct 2025   | 8         |
| Nov 2025   | 9         |
| Dic 2025   | 6         |
| Ene 2026   | 10        |
| Feb 2026   | 8         |
| Mar 2026   | 10        |
| Abr 2026   | 4         |
| **Total**  | **55**    |

**Distribución por tipo:**

| tipo_evento_codigo | # | Nota |
|---|---|---|
| ENTREGA            | 18 | "DEMO_ Entrega de kits escolares en Corabastos" |
| CAPACITACION       | 15 | "DEMO_ Capacitación en emprendimiento Patio Bonito" |
| CURSO              | 12 | "DEMO_ Curso de formación para mujeres cabeza de familia" |
| INFO_TERRENO       | 10 | "DEMO_ Visita técnica a parque Cayetano Cañizares" |

**Distribución por UPZ (GPS real de Kennedy):**

| UPZ                   | # eventos |
|-----------------------|-----------|
| PATIO BONITO          | 10        |
| CORABASTOS            | 9         |
| KENNEDY CENTRAL       | 7         |
| AMERICAS              | 6         |
| TIMIZA                | 6         |
| CASTILLA              | 5         |
| GRAN BRITALIA         | 5         |
| CALANDAIMA            | 4         |
| CARVAJAL              | 3         |

GPS por UPZ: usar un centroide aproximado conocido + jitter ±0.005° para variedad.

**Distribución por dependencia/subgrupo:**
- Todos con `dependencia_id=3` (Inv. Local).
- Subgrupo rotando por los 15 disponibles.
- Funcionario rotando por los 15 de Javier Aguilar (id 4-18).

**Enlace a KPI:**
- Cada evento tiene `indicador_id` apuntando a un KPI del mismo sector.
- `magnitud_aportada` entre 1 y 50 (según unidad del KPI).

**Sub-datos por INFO_TERRENO:**
- Los 10 INFO_TERRENO crean su `evento_info_terreno` con hallazgos/
  recorrido/observaciones realistas.
- 5 de los 10 se marcan como `confirmado=TRUE` con GPS en sitio.

### Fase E — 75 avances (`presu_avance_ind_periodo`, id ≥ 100000)

**Tabla:** `presu_avance_ind_periodo`

- Cada evento genera **1 avance** alimentando su KPI (55 avances).
- **20 avances "manuales"** adicionales (origen='MANUAL') para mostrar
  que el sistema soporta ambas vías.
- `fecha_aporte` coherente con fecha del evento.
- `periodo` en formato 'YYYY-MM'.
- `observaciones` descriptivas ("Entrega realizada en jornada…").

**Resultado esperado** tras siembra:

| KPI                              | Meta  | Avance | % |
|----------------------------------|-------|--------|---|
| KPIs 2025 cumplidos (10)         | varía | 85-100% | verde |
| KPIs 2026 en curso (20)          | varía | 10-70%  | mezcla |
| KPIs 2026-27 iniciando (5)       | varía | 0-20%   | rojo/gris |
| Total: 35 KPIs con 75 avances    |       |         | |

### Fase F — Fotos mock (opcional, solo si hay tiempo)

**Tabla:** `documento_evento` + archivos en `/app/media/documentos/eventos/`

- 2-3 fotos placeholder por cada INFO_TERRENO confirmado (5 × 3 = 15 archivos).
- PNGs mini 1x1 con nombres reconocibles: `DEMO_foto_terreno_<id>_1.png`.
- `tipo_archivo_id` = el de "Foto de evidencia de visita en terreno"
  (creado en PR1).

Esto hace que la UI `/evento/info-terreno/exitoso/<id>/` muestre
thumbnails en los eventos demo.

## 5. Impacto en el dashboard

### PR1 (ya hecho): Sección "Avance de KPIs"
- **Antes**: 6 KPIs, 3.9% promedio, ninguno en riesgo.
- **Después** de siembra: **35 KPIs, ~55% promedio, ~8 en riesgo**.
- La sección existente se llena sola (usa el mismo endpoint).

### PR2 planeado: "Metas PDD con fechas y estado"
Nuevo endpoint `/dashboard/api/presupuesto/metas-pdd/` que devuelva:
```
[
  { meta_id, nombre, proyecto, vigencia_inicio, vigencia_fin,
    total_indicadores, pct_promedio, dias_restantes, estado }
]
```
Estados: `en_curso`, `cumplida`, `vencida`, `en_riesgo` (< 90 días).

Con 30 metas demo: lista visual rica con barras de progreso y fechas.

### PR3 planeado: "Timeline eventos → KPIs"
Endpoint `/dashboard/api/presupuesto/timeline-eventos/`:
```
Últimos 20 eventos con: fecha, tipo, nombre_evento,
kpi_alimentado, magnitud_aportada, dependencia
```

Con 55 eventos DEMO: timeline densa de 6 meses, bien narrativa.

### PR4 planeado: "Filtros"
- Vigencia (2025/2026/2026-27): trivial con los `fecha_inicio` de meta_proyecto sembrados.
- Sector: nuevo campo en meta/proyecto o derivado del nombre DEMO_*.
- Dependencia: trivial (todos id=3 + reales si las hay).
- Rango fecha: trivial.

Con data densa, los filtros efectivamente filtran y el demo "vuela".

## 6. Scripts de ejecución (a crear, NO incluidos en este plan)

Carpeta: `apps/dashboard/scripts/seeds/`

```
00_cleanup_demo.py              # borra todo DEMO antes de empezar (idempotente)
01_siembra_proyectos.py         # Fase A (10 proyectos)
02_siembra_metas_mp.py          # Fase B (10 metas + 30 meta_proyecto)
03_siembra_kpis.py              # Fase C (35 KPIs)
04_siembra_eventos.py           # Fase D (55 eventos + lugar_incidencia + info_terreno)
05_siembra_avances.py           # Fase E (75 avances)
06_siembra_fotos_mock.py        # Fase F (opcional, 15 fotos mini)
run_all.py                      # orquesta 00..06 con confirmación
README.md                       # cómo ejecutar, cómo revertir
```

Cada script:
- `@transaction.atomic` individual.
- Idempotente vía `ON CONFLICT DO NOTHING` o chequeo previo.
- Logging claro con counts.
- Aborta si algún FK esperado no existe.

## 7. Cleanup (script 00)

```sql
-- En orden inverso de dependencias:
DELETE FROM presu_avance_ind_periodo
 WHERE indicador_id IN (SELECT id FROM presu_indicador_meta_proyecto WHERE nombre LIKE 'DEMO_%')
    OR id >= 100000;

DELETE FROM documento_evento
 WHERE evento_id IN (SELECT id FROM evento WHERE nombre LIKE 'DEMO_%')
    OR nombre_archivo LIKE 'DEMO_%';

DELETE FROM evento_info_terreno
 WHERE evento_id IN (SELECT id FROM evento WHERE nombre LIKE 'DEMO_%');

DELETE FROM evento WHERE nombre LIKE 'DEMO_%' OR id >= 100000;

DELETE FROM presu_indicador_meta_proyecto
 WHERE nombre LIKE 'DEMO_%' OR id >= 100000;

DELETE FROM meta_proyecto WHERE id >= 100000;

DELETE FROM metas WHERE nombre LIKE 'DEMO_%' OR codigo >= 100;

DELETE FROM proyecto WHERE nombre LIKE 'DEMO_%' OR id >= 100000;

-- Nota: lugar_incidencia y geo_referenciacion NO se borran por seguridad
-- (podrían estar siendo usados por otros módulos). Los registros huérfanos
-- quedan como deuda limpia (uso futuro).

-- Opcional: borrar archivos en disco
-- find /app/media/documentos/eventos -name 'DEMO_*' -delete
```

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Romper data real existente | Prefijo `DEMO_`, IDs ≥ 100000, chequeos pre-INSERT |
| No poder borrar después | Script `00_cleanup_demo.py` escrito y probado en vacío primero |
| Columnas distintas a lo supuesto | Plan ya verificó los schemas reales (sección 3) |
| FKs rotas | Scripts en orden de dependencia A→F |
| Duplicados en re-ejecución | `ON CONFLICT DO NOTHING` + check por nombre |
| `lugar_incidencia` sin secuencia | Usar helper `crear_con_fallback_id` (ya arreglado en PR1) |
| UPZ PK es codigo (no id) | Usar `upz.codigo` como FK al poblar |
| `metas` PK es codigo | Usar codigo ≥ 100 como espacio DEMO |
| `proyecto.id` nullable en FKs | No esperar FKs formales, verificar antes de usar |
| Usuario no respalda BD antes | Paso 0 obligatorio: backup pre-siembra |

## 9. Tiempos estimados

| Fase | Tiempo | Notas |
|------|--------|-------|
| **Plan documentado + inspección schemas** | ✓ HECHO | (este documento) |
| Backup BD pre-siembra | 2 min | `docker run pg_dump`, ya probado |
| Script 00 cleanup (primer intento en vacío) | 15 min | Verifica idempotencia |
| Scripts 01-05 siembra | 60 min | ~12 min por script |
| Script 06 fotos mock (opcional) | 15 min | |
| Ejecución `run_all.py` | 5 min | Inserts rápidos |
| Validación visual dashboard | 15 min | Navegar el UI con data densa |
| PR2 "Metas PDD" (endpoint + UI) | 45 min | Aprovechando data sembrada |
| PR3 "Timeline" (endpoint + UI) | 45 min | |
| PR4 "Filtros" (4 selects + lógica) | 60 min | |
| **Total demo robusto** | **~4h 30min** | |

## 10. Preguntas abiertas para Alex antes de ejecutar

1. **¿OK con IDs ≥ 100000 para DEMO?** Es la convención más limpia. Si prefieres otro rango, especifica.
2. **¿OK con prefijo `DEMO_`** en todos los nombres visibles? Alternativa: campo `es_demo boolean` — requiere ALTER TABLE.
3. **¿Cuándo se limpia?** ¿Después de la demo (fecha concreta), o se mantiene como data de prueba?
4. **¿Ejecutamos Fase F (fotos mock)?** Son solo 15 archivos de 67 bytes cada uno, inofensivo. Recomiendo sí.
5. **¿El demo es para fecha concreta?** Influye en el timing de siembra (lo más cercano posible a la demo para que "últimos 30 días" tenga data).

## 11. Plan de continuación tras tu OK

1. Commitear este plan (→ PR único `docs:`).
2. Tras tu "dale", **siguiente sesión**: genero los 7 scripts en
   `apps/dashboard/scripts/seeds/` con los schemas de este plan. NO los
   ejecuto — te los reviso.
3. Tras OK de scripts, ejecuto `run_all.py` con backup previo.
4. Validación visual conjunta.
5. PR2 → PR3 → PR4 en orden.

---

**Este documento no ejecuta nada.** Espera tu revisión + respuesta a las
5 preguntas de la sección 10 para avanzar.
