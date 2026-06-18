# Análisis de brecha: módulo de Cursos de innovaK vs. KDApp (Kennedy Deporte y Arte)

> Reporte de SOLO LECTURA. Fecha: 2026-06-18. Verificado contra el código real.
> KDApp = sistema externo de Carlos Gómez (BD `basedpc`) para escuelas de
> formación deporte/cultura. Sin login; Carlos planea unificarse a la BD central.

## 1. Tabla de brecha (capacidad KDApp → estado en innovaK)

| Capacidad KDApp | ¿innovaK lo tiene? | Evidencia |
|---|---|---|
| Inscripción con datos completos (género, discapacidad, etnia, complementarios) | ✅ SÍ (modelo+UI) | `serializers.py:27-45`; caracterización 6 sectores |
| Disciplina (catálogo) | ⚠️ TABLA HUÉRFANA (sin modelo) | `disciplina` sin modelo; hoy texto libre |
| Acudiente (menor) | ⚠️ Doble: modelo `Acudiente` dormido + caracterización Explorarte sí lo capta | `curso_sesiones.py:219-238` |
| Grupos | ⚠️ MODELO SIN CABLEAR (sin FK a Evento) | `curso_sesiones.py:203-216` |
| Horarios con lugar | 🟡 PARCIAL (`clase.lugar` texto; `HorarioClase` sin cablear; sin conflictos) | `curso_sesiones.py:31-98` |
| **Cupos limitados** | ❌ NO EXISTE | sin campo `cupo` |
| **Lista de espera** | ❌ NO EXISTE | — |
| **Validación documental** (checklist + habeas data) | ⚠️ TABLA HUÉRFANA `validacion_documental` | sin modelo |
| Nota médica | ⚠️ MODELO SIN CABLEAR | `curso_sesiones.py:241-260` |
| Georreferenciación / mapa de calor | 🟡 PARCIAL (heatmap solo en JS legacy; cursos no ligados a escuela) | `mapa_kennedy.js:218` |
| Dashboard docente | ✅ SÍ (mis cursos, sesiones, asistencia, notas, reporte, exports) | `features/cursos/*` |
| Inscripción robusta (anti-manual/anti-pérdida docs) | ✅ SÍ (QR→Angular, firma cifrada Mongo, atómico) | `inscripcion_evento.py` |
| Roles (Admin/Docente/Funcionario/Consulta) | ✅ SÍ y superior (N15, KDApp ni tiene login) | sistema roles dinámico |

**Resumen:** de 13 capacidades — innovaK **iguala/supera 6**, **5 son tablas/modelos remanentes sin cablear**, **2 no existen** (cupos, lista de espera), **2 parciales**.

## 2. Tablas remanentes (kactivo → fusión 2026-05-27)

| Tabla | Modelo | Cableado | Recomendación |
|---|---|---|---|
| `escuela` (241) | ✅ Escuela | API mapa; NO ligada a cursos | **REUSAR** (ancla cursos↔escuela↔mapa) |
| `clase`, `asistencia_clase`, `evaluacion_participante`, `participante_evento` (2.545) | ✅ | Totalmente cableado | **REUSAR** (núcleo) |
| `horario_clase` | ✅ HorarioClase | sin cablear | REUSAR (recurrencia + conflictos) |
| `grupo` | ✅ Grupo | sin cablear, sin FK Evento | REUSAR (falta `evento_id`) |
| `acudiente`, `nota_medica` | ✅ | dormidos | EVALUAR (caracterización ya cubre) |
| `disciplina`, `validacion_documental` | ❌ sin modelo | huérfanas | REUSAR (validación doc = checklist faltante) |
| `curso` | ❌ (zombi) | — | DESCARTAR (Evento es la cabecera) |

Secuencias BIGSERIAL ya creadas (`005_curso_sesiones_secuencias.sql`).

## 3. Lo que falta concreto (reusando lo existente)
- **Cupos + lista de espera**: `evento.cupo_maximo` + `participante_evento.estado` ('inscrito|espera|rechazado') — reusa la tabla de inscritos, sin tabla nueva.
- **Validación documental**: reusar tabla huérfana `validacion_documental` (o nueva ligada a `participante_evento`) + pipeline Mongo cifrado + checkbox habeas data.
- **Grupos**: `ALTER TABLE grupo ADD COLUMN evento_id` + cablear el modelo `Grupo` (ya hecho).
- **Horarios↔lugar↔escuela↔mapa**: `clase.escuela_id` FK a `Escuela` (241, con lat/lon) + cablear `HorarioClase` + detección de conflictos. Mapa de calor de oferta formativa portado al mapa Angular.
- **Inscripción completa**: NO recrear datos complementarios/acudiente — encadenar a la caracterización del sector (ya funciona en Explorarte; generalizar).

## 4. Plan de PRs (cascadeable, por valor/riesgo)
- **PR-1** Cupos + lista de espera (alto valor, bajo riesgo). DDL: `evento.cupo_maximo`, `participante_evento.estado`.
- **PR-2** Cursos↔Escuela (sede) + filtro territorial. DDL: `clase.escuela_id`.
- **PR-3** Validación documental + habeas data. Reusa `validacion_documental` + Mongo.
- **PR-4** Grupos del curso. DDL: `grupo.evento_id`.
- **PR-5** Horarios recurrentes + conflictos. Sin DDL (tabla lista).
- **PR-6** Mapa de calor de cursos en Angular. Reusa `escuela` + heatmap.
- **PR-7** (opcional) Catálogo Disciplina + nota médica rápida.

Cada DDL 🚨 requiere confirmación de Alex + backup.

## 5. Decisión: ¿absorber KDApp o solo tomar ideas?
KDApp es el **mismo dominio** que innovaK; su BD `basedpc` es casi un subconjunto de tablas que innovaK ya tiene (herencia kactivo); no tiene login; Carlos planea unificarse a la central.

- **Opción A — Absorber (recomendada)**: innovaK único sistema. KDApp aporta requisitos (cupos, lista espera, validación doc, conflictos). Carlos no construye login/roles (innovaK ya los tiene). `basedpc` se migra como **datos** (ETL), no esquema paralelo. Cero duplicación.
- **Opción B — Solo ideas, sistemas separados**: doble mantenimiento, datos divergentes, doble caracterización del mismo ciudadano. Trabajo desechable (Carlos igual quiere unificar).

**Recomendación: Opción A.** innovaK ya tiene ~70% del esquema + todo lo que KDApp NO tiene (roles, cadena presupuestal, mapa, exports, caracterización). PRs 1-6 + un PR de ETL de `basedpc`.

## Verificaciones de BD antes de DDL (correr con Alex)
```
\d validacion_documental   \d disciplina   \d grupo   \d clase
SELECT count(*) FROM escuela;  SELECT count(*) FROM disciplina;  SELECT count(*) FROM validacion_documental;
```
