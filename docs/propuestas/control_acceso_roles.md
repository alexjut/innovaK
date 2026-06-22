# Control de acceso por rol / dependencia — Hallazgo QA 3.3

> Estado: BORRADOR PARA DECISIÓN DE ALEX. No implementar nada hasta su OK.
> Fecha análisis: 2026-06-22. Verificado contra código (no memorias).

## 0. Resumen en una frase

El control de acceso de innovaK es **por MÓDULO** (qué funcionalidad puede
abrir cada rol) y funciona bien. Lo que NO existe es **segmentación por
DEPENDENCIA/SUBGRUPO**: cualquier usuario con el módulo correspondiente
ve y edita datos de TODAS las áreas, no solo de la suya. El hallazgo QA
3.3 es correcto. La pregunta abierta — confirmada por el propio informe —
es si esa transversalidad es **intencional (transparencia)** o un hueco.

---

## 1. Estado actual documentado (verificado en código)

### 1.1 Cómo funciona la autorización HOY

- Modelo dinámico N15: tablas `modulo`, `rol_modulo`, `rol_meta`. Un rol
  (grupo Django) tiene asignados N módulos vía `rol_modulo`.
- Servicio `apps/login/services/permisos.py`: resuelve `get_modulos_usuario(user)`
  → set de códigos de módulo, con caché Redis versionada. Bypass total si
  `is_superuser=True` (escotilla, `superusuario_o_modulo`).
- Enforcement:
  - Vistas HTML legacy: decorador `@modulo_required("codigo")`
    (`apps/login/decorators.py`).
  - APIs DRF (lo vivo hoy): `ModuloRequiredPermission("codigo")`
    (`apps/login/api/permissions.py`) en `permission_classes`. Reusa el
    MISMO servicio.
- Visibilidad de UI: context processor `modulos_usuario` + frontend Angular
  gatean cards/sidebar por módulo.

**El check es binario: "¿tu rol tiene el módulo X?" → sí/no.** No hay un
segundo eje que pregunte "¿este dato es de TU dependencia?".

### 1.2 Catálogo de roles → módulos (fuente: `seed_modulos.ASIGNACION_INICIAL`)

| Rol | Módulos asignados (resumen) |
|-----|------------------------------|
| **Admin** | Los 19 (todo) |
| **Lider** | mapa, eventos, presupuesto (×3), banco, jóvenes, entregas, festivales, votaciones (×2), dashboard_ia, caracterizacion, personas_registro |
| **LiderParticipacion** | mapa, eventos, votaciones (×2), dashboard_ia, caracterizacion |
| **Coordinador** | mapa, cursos, eventos_asistencia, caracterizacion, festivales, dashboard_ia, personas_registro |
| **Docente** | mapa, cursos, eventos_asistencia, dashboard_ia |
| **CoordinadorDeportes** (Daniel) | mapa, eventos, banco, caracterizacion, dashboard_ia, org_admin |
| **UsuarioGeneral** | mapa, cursos, dashboard_ia |

### 1.3 Qué puede hacer cada área clave HOY (verificado endpoint por endpoint)

| Área / acción | Gating actual | ¿Filtra por dependencia del usuario? |
|---|---|---|
| **Eventos — listar** (`EventoListView`) | `eventos` | **NO.** Filtros `dependencia_id`/`subgrupo_id` vienen del query param (UI), no del usuario. Ve todos los eventos. |
| **Eventos — crear/editar** (`EventoCRUDView`) | `eventos` | **NO.** `dependencia_id`/`subgrupo_id` son campos editables libres. Puede crear para cualquier área. |
| **Panel de curso por URL directa** (`CursoDetalleView`, `NotasEventoView`, `CursoInscritosView`, `ReporteCursoView`) | `cursos` | **NO.** `get_object_or_404(Evento, pk=...)` sin chequeo de propiedad. Cualquiera con `cursos` abre/edita cualquier curso, aunque no sea su docente titular. |
| **Banco — validar/rechazar** (`InscripcionEstadoView`) | `banco_iniciativas` | **NO.** Filtra solo por `estado`/`evento_id` del query param. Sin scope de área. |
| **Presupuesto — CRUD completo** (Proyectos, CDPs, Contratos, Metas, KPIs, Avances, Vinculaciones, Conceptos) | `presupuesto_*` | **NO.** Ningún queryset acota por subgrupo del usuario. Todo el CRUD es transversal. |
| **Festivales** (`Festival*View`) | `festivales` | **NO.** |
| **Caracterización** (organizador) | `caracterizacion` | **NO.** |
| **Jóvenes / Entregas** (validar/rechazar) | `jovenes_a_la_e` / `entregas` | **NO.** |

### 1.4 Confirmaciones técnicas clave

1. **El vínculo usuario→dependencia SÍ existe en datos pero NO se usa para
   filtrar.** La cadena es `Usuario → Persona (persona.usuario_id) →
   Funcionario (activo) → dependencia_id / subgrupo_id`. Hoy esa cadena se
   resuelve en UN solo lugar: `apps/caracterizacion/services/funcionario_lookup.py::funcionario_actual_o_none`,
   y **solo para auditoría** (registrar quién recolectó una caracterización),
   nunca para autorizar ni filtrar.

2. **No existe ningún helper de scope por dependencia** en todo `apps/`
   (búsqueda de `scope`, `mi_dependencia`, `filtrar_por_dependencia`, etc.:
   cero resultados en código de producción).

3. **El informe probó con superusuario**, que por diseño (`is_superuser` →
   bypass total) salta TODO. Eso explica el "puede hacer de todo". Un rol
   regular SÍ está limitado por módulo — pero, dentro de su módulo, sigue
   siendo transversal a todas las áreas.

**Conclusión del estado actual: el control por módulo es sólido; la
segmentación por dependencia es inexistente por diseño actual, no por bug.**

---

## 2. El dilema

### Opción A — Visibilidad transversal (lo actual)

Todos los que tienen el módulo ven/editan datos de todas las áreas.

- **Pros**: transparencia interna (cualquier líder ve el panorama
  completo); simple; cero código nuevo; útil en alcaldía chica donde la
  gente cubre varias áreas; reportes consolidados sin fricción.
- **Contras**: un coordinador de Cultura puede editar/borrar datos de
  Deporte o Educación (accidental o no); sin trazabilidad de "esto no era
  tu área"; riesgo si entran más usuarios operativos por subgrupo; el QA
  lo marca como hallazgo.

### Opción B — Segmentación por área (escritura restringida)

Cada coordinador solo edita su dependencia/subgrupo; lectura puede seguir
siendo transversal o también restringirse.

- **Pros**: principio de menor privilegio; previene ediciones cruzadas
  accidentales; encaja cuando lleguen los usuarios de Cultura/Deporte/
  Educación cada uno con su área; auditoría más limpia.
- **Contras**: más complejo; hay que poblar bien el vínculo
  usuario→funcionario→dependencia (hoy no garantizado para todos los
  usuarios); algunos flujos legítimamente cruzan áreas (Presupuesto
  consolidado, mapa); riesgo de bloquear a alguien que sí necesita ver otra
  área; mantenimiento de la matriz.

---

## 3. Propuesta borrador de modelo de roles (para aprobación)

Principio sugerido: **lectura/dashboards transversales** (transparencia),
**escritura acotada al área** para roles operativos, **escritura
transversal** solo para roles de gobierno (Admin/Líder).

Incluye el rol nuevo **Analista** (solo lectura) ya pendiente para Cultura.

| Rol | Puede VER todo | Puede EDITAR solo su área | Puede EDITAR todo |
|-----|:---:|:---:|:---:|
| **Admin** | ✅ | — | ✅ |
| **Lider** | ✅ | — | ✅ (su ámbito: presupuesto, banco, eventos) |
| **LiderParticipacion** | ✅ | ✅ (participación/votaciones) | — |
| **Coordinador** (Cultura) | ✅ (lectura) | ✅ (su subgrupo) | — |
| **CoordinadorDeportes** | ✅ (lectura) | ✅ (Deporte) | — |
| *CoordinadorEducacion* (futuro) | ✅ (lectura) | ✅ (Educación) | — |
| **Docente** | parcial (sus cursos) | ✅ (sus cursos como titular) | — |
| **UsuarioGeneral** | parcial | ✅ (lo que captura) | — |
| **Analista** (NUEVO) | ✅ (lectura total) | — (cero escritura) | — |

Notas de la propuesta:
- **Analista**: módulos de solo-lectura — `mapa_kennedy`, `dashboard_ia`,
  insights de cursos/banco/presupuesto, y los exports. NO recibe ningún
  endpoint POST/PATCH/DELETE. Como el gating es por módulo y muchos
  POST/GET comparten módulo, esto requiere o bien (a) separar módulos de
  lectura vs escritura, o (b) un flag `solo_lectura` por rol (ver §4).
- **Presupuesto siempre transversal** (la cadena Proyecto→Meta→Contrato es
  cross-área por naturaleza): mantener Admin/Líder como únicos editores.
- **Docente**: restringir el panel de curso a su `Evento.funcionario` (es el
  caso más concreto y de menor riesgo para empezar).

---

## 4. Esfuerzo técnico si se decidiera segmentar (Opción B)

No es trivial pero es acotado porque la infraestructura de permisos ya
existe. Pasos concretos:

1. **Garantizar el vínculo usuario→dependencia/subgrupo** (precondición).
   - Hoy resoluble vía `Persona.usuario_id → Funcionario`. Verificar que
     CADA usuario operativo tenga Funcionario activo con
     `dependencia_id`/`subgrupo_id`. Auditar datos: posiblemente falten.
   - Promover `funcionario_actual_o_none` (hoy en caracterizacion) a un
     servicio compartido en `apps/login/services/` que devuelva
     `(funcionario_id, dependencia_id, subgrupo_id)` cacheado.

2. **Definir el modelo de scope**. Dos caminos:
   - **B1 (recomendado, menos invasivo)**: un campo/flag por rol en
     `rol_meta` (p. ej. `alcance = 'global' | 'dependencia' | 'subgrupo' |
     'solo_lectura'`). DDL pequeño: 1 columna. 🚨 REQUIERE CONFIRMACIÓN ALEX
     (DDL, CLAUDE.md §9).
   - **B2**: módulos separados lectura/escritura (sin DDL pero duplica
     catálogo: `eventos` → `eventos_ver` + `eventos_editar`). Más ruido en
     `seed_modulos` y matriz.

3. **Nuevo permission/decorator de scope**. Crear
   `ScopedModuloPermission("codigo", scope="subgrupo")` que: pasa módulo Y,
   en POST/PATCH/DELETE, valida que el `subgrupo_id`/`dependencia_id` del
   objeto coincida con el del usuario (o que su rol sea `global`). Reusa la
   caché de permisos.

4. **Filtrar querysets de lectura** (si se decide restringir también
   lectura). Inyectar `.filter(subgrupo_id__in=mis_subgrupos)` en los
   `get()` de las list-views afectadas. Cada list-view se toca a mano
   (~10-15 endpoints).

5. **Caso Docente** (quick win independiente): en
   `CursoDetalleView`/`NotasEventoView`/`CursoInscritosView`, si el rol es
   Docente y `Evento.funcionario_id != mi_funcionario_id` → 403. ~0.5 día,
   sin DDL.

6. **Tests + matriz**. Actualizar `seed_modulos`/`rol_meta`, smoke tests por
   rol×área, doc de la matriz.

**Estimación gruesa**:
- Solo el caso Docente (panel de curso): ~0.5 día.
- Segmentación completa por dependencia con flag `alcance` (B1): ~3-5 días
  (1 DDL + servicio scope + permission nuevo + tocar ~15 endpoints +
  auditar/poblar vínculos usuario→funcionario + tests). El mayor riesgo no
  es el código sino **datos**: si los usuarios no tienen Funcionario/
  dependencia bien poblado, el filtro deja a gente fuera.

---

## 5. Recomendación

1. **No cambiar nada de inmediato.** El sistema actual NO es un bug de
   seguridad de autenticación; es una decisión de alcance. El "todo
   permitido" del QA se midió con superusuario (bypass por diseño).
2. **Confirmar primero la intención** con Alex (transparencia vs.
   menor-privilegio).
3. Si se quiere avanzar con bajo riesgo: empezar por **dos quick wins**
   independientes que casi nadie discutiría:
   - **Analista solo-lectura** (ya pendiente para Cultura): definir sus
     módulos de lectura/exports y sembrarlo. Sin tocar el resto.
   - **Docente restringido a sus cursos**: 0.5 día, alto valor, sin DDL.
4. Dejar la **segmentación completa por dependencia** como decisión
   posterior, condicionada a (a) que Alex la quiera y (b) auditar que el
   vínculo usuario→funcionario→dependencia esté bien poblado.

---

## 6. Preguntas concretas para Alex (desbloquean la decisión)

1. **¿La visibilidad transversal es intencional (transparencia interna) o
   quieres acotar por área?** Esta respuesta define todo lo demás.
2. Si acotas: **¿restringir solo la ESCRITURA por dependencia, o también la
   LECTURA?** (recomiendo restringir solo escritura, dejar lectura/dashboards
   transversales).
3. **¿Presupuesto se queda transversal** (solo Admin/Líder editan) o también
   por subgrupo?
4. **Rol Analista**: ¿solo-lectura TOTAL (todos los dashboards/insights/
   exports de todas las áreas) o limitado a Cultura?
5. **¿Aprobamos el quick win del Docente** (que solo vea/edite sus propios
   cursos) ya, independiente del resto?
6. Si vamos a segmentar: **¿todos los usuarios operativos ya tienen su
   Funcionario activo con dependencia/subgrupo correcto en BD?** (si no, hay
   que poblarlo antes — es la precondición real).
7. ¿Aceptas el **DDL mínimo** (1 columna `alcance` en `rol_meta`) como
   mecanismo, o prefieres módulos separados lectura/escritura sin DDL?
