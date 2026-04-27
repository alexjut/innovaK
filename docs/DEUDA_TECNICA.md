# Deuda técnica — innovaK

> Snapshot tomado el **2026-04-20** sobre la rama
> `feat/integracion-geo-eventos-dashboard` (commit `3ff93b2`).
>
> Cada entrada registra un hallazgo objetivo. **No se ha corregido ninguno
> en este trabajo**; este doc existe para priorizar y planificar.
>
> Severidades:
>
> - **CRÍTICA** — vulnerabilidad activa o riesgo de pérdida/corrupción de datos.
> - **ALTA** — problema funcional latente en producción o bloqueador de escalabilidad.
> - **MEDIA** — deuda que cuesta tiempo en cada mantenimiento.
> - **BAJA** — incoherencia cosmética o duplicación sin efecto runtime.

---

## 🔐 Seguridad

### S1 — `SECRET_KEY` hardcodeada en el código [CRÍTICA]

- **Ubicación:** `core/settings.py:42`
- **Descripción:** El `SECRET_KEY` está embebido como literal en el
  archivo (con prefijo `django-insecure-`). Existe `.env` con una clave
  distinta, pero `settings.py` **nunca la lee**. En el repositorio público
  (o en cualquier snapshot), el secret queda expuesto.
- **Recomendación:** `SECRET_KEY = os.environ["SECRET_KEY"]` (sin default),
  fallar al arrancar si no está definida. Rotar la clave actual: invalida
  todas las sesiones existentes.
- **Esfuerzo:** bajo (2 líneas + rotar + verificar).
- **Estado: RESUELTO 2026-04-20 en `fix/settings-env-loading` (commit `79a1c95`)**

### S2 — `DEBUG = True` hardcodeado [CRÍTICA]

- **Ubicación:** `core/settings.py:45`
- **Descripción:** `DEBUG = True` está en código. `docker-compose.yml` pasa
  `DEBUG=False` como variable de entorno, pero settings.py la ignora. En
  producción corre con stacktraces expuestos y sin whitenoise de prod.
- **Recomendación:** `DEBUG = os.getenv("DEBUG", "False").lower() == "true"`.
- **Esfuerzo:** bajo.
- **Estado: RESUELTO 2026-04-20 en `fix/settings-env-loading` (commit `79a1c95`)**

### S3 — `ALLOWED_HOSTS` hardcodeado y divergente con `.env` [ALTA]

- **Ubicación:** `core/settings.py:20-24` y `.env:5`
- **Descripción:** El archivo `.env` define `ALLOWED_HOSTS` pero
  `settings.py` define la lista literal. Cualquier nuevo dominio (staging,
  nueva URL ngrok) requiere edición de código en vez de env.
- **Recomendación:** Leer de env:
  `ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")`.
- **Esfuerzo:** bajo.
- **Estado: RESUELTO 2026-04-20 en `fix/settings-env-loading` (commit `79a1c95`)**

### S4 — `ONEDRIVE_TOKEN` placeholder en settings [ALTA]

- **Ubicación:** `core/settings.py:168-169`
- **Descripción:** `ONEDRIVE_TOKEN = "Bearer_Token_Aquí"`. Un placeholder
  visible sugiere que alguien intentó pegar el token real aquí. Si en
  algún commit pasado estuvo hardcodeado, puede estar en `git log`.
- **Recomendación:** Mover a `.env` (`ONEDRIVE_TOKEN=...`), usar refresh
  token dinámico, revisar `git log --all -p` por historial del valor.
- **Esfuerzo:** medio (si hay que rotar el token + migrar a refresh flow).
- **Estado: RESUELTO 2026-04-20 en `fix/settings-env-loading` (commit `79a1c95`)**
  (Auditoría `git log --all -p` confirmó que nunca hubo secret real en la
  historia — solo el placeholder `"Bearer_Token_Aquí"`. Variable queda en
  `.env` vacía para rellenar cuando OneDrive se use.)

### S5 — Race condition en generación manual de `id` [ALTA]

- **Ubicaciones:**
  - `apps/login/views/registro.py:32` — persona
  - `apps/login/views/eventos.py:242` — evento
  - `apps/login/views/eventos.py:442` — persona (en inscripción)
  - `apps/login/views/eventos.py:479` — participante
  - `apps/presupuesto/views/cdp.py:82-83` — cdp
  - `apps/login/views/admin_org.py:proveedor_nuevo` — proveedor (PR-H2, sin secuencia)
  - `apps/presupuesto/views/catalogo.py:contrato_nuevo` — contrato (PR-H3 detectó: SIN fallback aún, intentar crear desde UI fallará)
- **Descripción:** Patrón
  `SELECT COALESCE(MAX(id), 0) + 1 FROM <tabla>` seguido de `INSERT`.
  Aunque va dentro de `transaction.atomic()`, PostgreSQL con nivel de
  aislamiento por defecto (READ COMMITTED) **no** bloquea la tabla — dos
  transacciones concurrentes pueden leer el mismo MAX y colisionar en el
  INSERT. Riesgo: `IntegrityError` esporádico o, peor, duplicados si la
  PK no fuerza unicidad.
- **Recomendación (por orden de preferencia):**
  1. Agregar `DEFAULT nextval('tabla_id_seq'::regclass)` a la columna id
     en la BD y retirar el patrón manual. (El comentario en `cdp.py:88`
     ya lo señala.)
  2. Si no se puede: usar `SELECT MAX(id) FOR UPDATE` sobre un registro
     sentinel, o `INSERT ... RETURNING id` con una secuencia aislada.
  3. Último recurso: lock explícito con `LOCK TABLE ... IN EXCLUSIVE MODE`.
- **Esfuerzo:** medio (requiere acceso a BD para crear secuencias +
  refactor de las 5 vistas).

### S6 — SQL con concatenación f-string en insert dinámico [MEDIA]

- **Ubicación:** `apps/login/views/eventos.py:472-474`
- **Descripción:**
  ```python
  sql_persona = f"""INSERT INTO persona ({",".join(cols)}, ...)
                    VALUES ({placeholders}, NOW(), NOW())"""
  cursor.execute(sql_persona, vals)
  ```
  Las listas `cols` y `placeholders` se construyen desde `request.POST`,
  filtradas contra un diccionario de columnas esperadas. Los valores sí
  están parametrizados con `%s`, pero los **nombres de columna** entran
  por f-string. Hoy es seguro porque hay un allowlist, pero basta con que
  alguien relaje el filtro para abrir una inyección.
- **Recomendación:** Usar un mapeo explícito de columnas permitidas a
  placeholders; si ya existe, validarlo contra un set literal en el código
  en vez de derivarlo de POST.
- **Esfuerzo:** medio.

### S7 — Vistas sin `@login_required` en endpoints potencialmente sensibles [MEDIA]

- **Ubicaciones:**
  - `apps/login/views/home.py:3` — `home_view`
  - `apps/georeferenciacion/views/mapa_kennedy.py:5` — `mapa_kennedy`
  - `apps/georeferenciacion/views/mapas.py:43` — `mapa_escuelas_view`
  - `apps/login/views/eventos.py:*` — al menos 50% de las funciones sin
    decorador (inscripción pública es intencional, pero revisar caso a caso).
- **Descripción:** Cobertura estimada del decorador ~62% (110 usos sobre
  178 funciones en views/). Los mapas y el home son razonables públicos si
  el contenido no expone PII, pero vale la pena confirmar.
- **Recomendación:** Auditar una por una: decidir explícitamente qué es
  público (inscripción, landing) y decorar el resto. Considerar un
  middleware que haga login obligatorio por defecto y anotar con
  `@public` las excepciones.
- **Esfuerzo:** medio.

### S8 — No hay Django REST Framework, pero tampoco CSRF en algunos POST AJAX [BAJA]

- **Ubicación:** AJAX endpoints en varios `views/api.py`
- **Descripción:** Las "APIs" internas son views con `JsonResponse`. Si
  alguna recibe `POST` sin `@csrf_exempt` sí lleva protección CSRF por
  default (bien). Si alguna usa `@csrf_exempt`, revisar que no exponga
  mutaciones sin validación.
- **Recomendación:** Listar todos los `@csrf_exempt` y validar caso a caso.
- **Esfuerzo:** bajo (auditoría).

### S9 — `DATABASE_URL` y `DB_PASSWORD` ambos en `.env` [BAJA]

- **Ubicación:** `.env:8-14`
- **Descripción:** `.env` define variables separadas (`DB_HOST`, `DB_NAME`,
  `DB_USER`, `DB_PASSWORD`) **y** además `DATABASE_URL` con la contraseña
  embebida. La librería `dj-database-url` está en requirements pero no se
  usa en settings. La doble fuente puede divergir.
- **Recomendación:** Elegir una: o variables separadas, o `DATABASE_URL`
  con `dj_database_url.parse()` en settings. Eliminar la redundancia.
- **Esfuerzo:** bajo.

---

## 🚀 Performance

### P1 — Ausencia sistemática de paginación en listados [ALTA]

- **Ubicaciones afectadas:** solo 3 archivos usan `Paginator`:
  `apps/presupuesto/views/concepto_gasto.py`,
  `apps/login/views/eventos.py`,
  `apps/dashboard/views.py`.
- **Descripción:** Listados masivos (participantes, personas, eventos
  históricos, inscripciones, avances) devuelven todo el queryset al
  template. Con 50k+ personas en la tabla `persona`, esto **escalará
  mal** en consultas tipo `consulta_participantes_cultura`.
- **Recomendación:** Añadir paginación por defecto (Django `Paginator` o
  un helper común) a todas las listas con >N filas potenciales. Exportar
  vía CSV/XLSX cuando se necesite "todo".
- **Esfuerzo:** medio.

### P2 — Queries N+1 latentes en listados sin `select_related` [MEDIA]

- **Ubicaciones con `.all()` sin prefetch:**
  - `apps/votaciones/views/organizer.py:131`
  - `apps/votaciones/views/registro.py:178`
  - `apps/georeferenciacion/views/apis.py:380,392,406,454,476`
  - `apps/presupuesto/services/metrics.py:140,152`
- **Descripción:** Algunas vistas ya usan `select_related` (correcto, p.ej.
  `kactivo/views/formulario_participante.py:281`), pero otras iteran
  sobre QuerySets accediendo a atributos FK en el template, lo que
  dispara una consulta por fila.
- **Recomendación:** Instalar `django-debug-toolbar` en dev y auditar
  vistas con más de 1s de respuesta. Para cada caso, agregar
  `select_related()` o `prefetch_related()` según la cardinalidad.
- **Esfuerzo:** bajo por caso, medio en conjunto.

### P3 — `.all()` + filtrado en Python detectado en forms [BAJA]

- **Ubicación:** `apps/presupuesto/forms.py:119`,
  `apps/presupuesto/views/catalogo.py:444`
- **Descripción:** `qs = Actividad.objects.all()` seguido de lógica de
  filtro en Python. Pierde beneficios del ORM.
- **Recomendación:** Refactorizar a `.filter(...)` cuando sea posible.
- **Esfuerzo:** bajo.

### P4 — Índices de dashboard creados en BD pero no declarados en modelos [BAJA]

- **Ubicación:** cualquier modelo relevante del dashboard
  (probablemente en `Evento`, `ActividadPlan`, `AvanceIndicador`).
- **Descripción:** Los 6 índices que se crearon para el dashboard viven
  solo en PostgreSQL. Si algún día alguien recrea la BD desde Django
  (aunque sea managed=False, `inspectdb` no los detectará como `Meta.indexes`),
  los índices se pierden.
- **Recomendación:** Declarar `class Meta: indexes = [...]` correspondientes
  como documentación, aunque `managed=False` no los cree.
- **Esfuerzo:** bajo.

---

## 🧹 Mantenibilidad

### M1 — Modelos duplicados apuntando a la misma `db_table` [ALTA]

- **Ubicaciones:**
  | Tabla | Clase A | Clase B |
  |-------|---------|---------|
  | `evento` | `apps/kactivo/models/kasistencia.py` — `Evento` | `apps/login/models/evento.py` — `Evento` |
  | `actividad` | `apps/kactivo/models/kasistencia.py` — `Actividad` | `apps/presupuesto/models/core.py` — `Actividad` |
  | `programas` | `apps/kactivo/models/kasistencia.py` — `Programa` | `apps/presupuesto/models/core_catalogos.py` — `Programa` |
  | `zona` | `apps/login/models/models_auxiliares.py` — `Zona` | `apps/georeferenciacion/models/models_localizacion.py` — `Zona` |
- **Descripción:** Django permite dos clases apuntando a la misma tabla,
  pero cada una define su propia lista de campos y relaciones. Los
  desarrolladores tienen que saber cuál importar y confundirse es fácil.
  El caso de `Evento` es la refactorización en curso (login.Evento es el
  nuevo, kactivo.Evento el legacy que debe retirarse).
- **Recomendación:**
  - Para `Evento`: completar la migración al nuevo modelo y **borrar** la
    clase legacy en `kactivo`, o convertirla en un alias `from apps.login.models import Evento`.
  - Para `Actividad` y `Programa`: decidir dueño (probablemente
    presupuesto) y hacer que kactivo importe desde allí.
  - Para `Zona`: borrar la duplicada en `login` (es un catálogo
    geográfico, pertenece a `georeferenciacion`).
- **Esfuerzo:** alto (requiere auditoría de todos los usos + coordinación
  con el refactor de eventos en curso).

### M2 — App `apps/documento/` abandonada pero en el repo [ALTA]

- **Ubicación:** `apps/documento/` (588 líneas)
- **Descripción:** La app no está en `INSTALLED_APPS`, no está en
  `core/urls.py`, no es importada desde ningún otro código del proyecto.
  Tiene sus propias URLs (`documento:gridfs_archivos`) referenciadas solo
  en su propio template. Implementa MongoDB/GridFS en paralelo a
  `apps/kactivo/services/mongo_upload.py`.
- **Recomendación:** Decidir con el dueño (Alex): ¿se retoma o se borra?
  Si se borra, eliminar la carpeta completa y el `utils/mongo_conexion.py`
  si `kactivo` no lo usa. Si se retoma, agregarla a INSTALLED_APPS y
  definir el alcance.
- **Esfuerzo:** bajo (si se borra), medio-alto (si se reintegra).

### M3 — Apps `kordial` y `VitalK` vacías en INSTALLED_APPS [MEDIA]

- **Ubicación:** `apps/kordial/`, `apps/VitalK/`
- **Descripción:** Ambas apps tienen `__init__.py` vacíos en `models/` y
  `views/`, no tienen `urls.py` útiles, y aun así están registradas en
  `INSTALLED_APPS`. Django las carga cada arranque aunque no hagan nada.
- **Recomendación:** Si son scaffolds para futuros módulos, dejarlas pero
  documentar el plan (añadir un `README.md` dentro con el objetivo). Si no,
  eliminar del INSTALLED_APPS y borrar el código.
- **Esfuerzo:** bajo.

### M4 — `apps/login/models.py` duplica lo que ya exporta el paquete `models/` [MEDIA]

- **Ubicación:** `apps/login/models.py` (archivo) coexiste con
  `apps/login/models/` (paquete).
- **Descripción:** Django resuelve primero el paquete, así que
  `models.py` es código muerto. Solo hace re-imports desde el paquete.
  Si alguien edita ese archivo creyendo que es la fuente, nada pasa.
- **Recomendación:** Borrar `apps/login/models.py`.
- **Esfuerzo:** muy bajo.

### M5 — `apps/votaciones/` no tiene `apps.py` [BAJA]

- **Ubicación:** `apps/votaciones/`
- **Descripción:** Funciona porque Django genera una AppConfig por
  defecto, pero rompe la convención. No hay `verbose_name`, no hay ganchos
  de `ready()`.
- **Recomendación:** Agregar `apps.py` siguiendo el patrón de las demás
  apps.
- **Esfuerzo:** muy bajo.

### M6 — Archivos de views con >500 líneas [MEDIA]

- **Ubicaciones:**
  - `apps/votaciones/views/api.py` — 647 líneas
  - `apps/georeferenciacion/views/apis.py` — 598 líneas
  - `apps/login/views/eventos.py` — 580 líneas
  - `apps/presupuesto/views/catalogo.py` — 540 líneas
- **Descripción:** No son funciones únicas gigantes, son agregaciones
  de muchos endpoints en un archivo. Dificulta navegación y review.
- **Recomendación:** Dividir por subdominio. En `eventos.py` sobre todo,
  separar `crear_evento`, `inscribir`, `asistencia` en archivos propios.
- **Esfuerzo:** medio.

### M7 — `LANGUAGE_CODE` y `TIME_ZONE` declarados dos veces [BAJA]

- **Ubicación:** `core/settings.py:135,137` y `core/settings.py:165-166`
- **Descripción:** Primero se declaran `en-us` / `UTC`, más abajo se
  sobreescriben a `es` / `America/Bogota`. Funciona pero es confuso.
- **Recomendación:** Eliminar la primera declaración.
- **Esfuerzo:** muy bajo.

### M8 — `Dockerfile` incoherente con `docker-compose.yml` [MEDIA]

- **Ubicación:** `Dockerfile:46`, `docker-compose.yml:27`
- **Descripción:** Dockerfile expone 8000 y arranca `runserver`;
  compose ignora el CMD y usa `gunicorn --bind 0.0.0.0:8032`. Si alguien
  hace `docker run innova_k` directamente, obtiene un dev server en 8000.
- **Recomendación:** Alinear. El CMD del Dockerfile debe ser el de
  producción (gunicorn 8032), y compose puede sobrescribirlo si lo
  necesita para dev.
- **Esfuerzo:** bajo.

### M9 — Django 4.2 con comentarios de documentación de Django 5.2 [BAJA]

- **Ubicación:** `core/settings.py:39,109,115,133,145`
- **Descripción:** Los comentarios `# See https://docs.djangoproject.com/en/5.2/...`
  son de un template de Django 5.2, pero `requirements.txt` fija 4.2.11.
  No afecta runtime, pero confunde la lectura.
- **Recomendación:** Actualizar a Django 5.2 (cambio no trivial) o
  corregir los enlaces a `/en/4.2/`.
- **Esfuerzo:** bajo (comentarios) o alto (upgrade).

### M10 — Ausencia completa de tests [ALTA]

- **Ubicación:** todos los `apps/*/tests.py` existen pero son stubs.
- **Descripción:** No hay pruebas unitarias, de integración ni de
  regresión. No hay fixtures. Cada refactor es una apuesta manual.
- **Recomendación:** Empezar con smoke tests (login, crear persona, crear
  evento) y factories (`factory_boy`) para los modelos centrales.
- **Esfuerzo:** alto (camino largo), pero cada test temprano paga mucho.

### M11 — Sin logger estructurado [BAJA]

- **Ubicación:** generalizado
- **Descripción:** Solo `apps/dashboard/apps.py` usa `logging` en forma
  estándar. El resto depende de `print()` o no reporta. No hay
  configuración de handlers en `settings.py`.
- **Recomendación:** Definir `LOGGING = {...}` mínimo (stream handler +
  formato con timestamp + nivel por app). Reemplazar `print()` por
  `logger.info/warning/error`.
- **Esfuerzo:** medio.

### M12 — Template faltante `mapa_kennedy_standalone.html` [MEDIA]

- **Ubicación:** `apps/georeferenciacion/views/mapa_kennedy_view.py:182`
- **Descripción:** El endpoint `/geo/mapa-kennedy/` intenta renderizar
  `geo-mapas/mapa_kennedy_standalone.html` pero el template no existe
  en `templates/`. Cada acceso a la URL genera `TemplateDoesNotExist`
  en logs. Endpoint efectivamente roto en producción.
- **Recomendación:** Crear el template o eliminar el endpoint.
  Determinar primero si la URL se usa (grep en templates por
  `mapa-kennedy`).
- **Severidad:** MEDIA (no bloquea otros flujos, pero enmascara errores
  reales en logs).
- **Esfuerzo:** bajo (determinar alcance) + medio (implementar o borrar).

### M13 — Doble consulta a `os.environ` para `DEBUG` en settings.py [BAJA]

- **Ubicación:** `core/settings.py` líneas 22 y 47
- **Descripción:** `ALLOWED_HOSTS` valida presencia consultando
  `os.environ` directamente en vez de usar la variable `DEBUG` definida
  26 líneas después. Funcionalmente correcto pero confuso para lectores
  futuros.
- **Recomendación:** Reordenar para que `DEBUG` se defina antes de
  `ALLOWED_HOSTS`, o extraer ambos a una función helper.
- **Severidad:** BAJA (cosmético).
- **Esfuerzo:** muy bajo.

### M17 — Mejorar geocoding con API IDECA [MEDIA]

- **Contexto:** el form `crear_evento` usa Nominatim (OpenStreetMap)
  para autocompletar direcciones. OSM tiene cobertura limitada en
  numeración catastral colombiana — sugiere tramos de calle pero no
  siempre números específicos (`Calle 26 Sur` aparece pero `# 93-40` no).
  Mitigado hoy con UX transparente: el hint dice al usuario "el
  autocompletar es orientativo, haga click en el mapa para la ubicación
  exacta", y al seleccionar sugerencia se muestra feedback verde 5s
  recordando ajustar el marcador.
- **Propuesta:** integrar API IDECA (Infraestructura de Datos
  Espaciales del Distrito Capital de Bogotá, `www.ideca.gov.co`) que
  tiene datos catastrales oficiales precisos.
- **Pre-requisitos de investigación:**
  1. Verificar URL actual del endpoint de geocoding en IDECA.
  2. Confirmar si requiere registro / API key.
  3. Probar CORS desde frontend o evaluar proxy backend.
  4. Documentar rate limits.
  5. Comparar calidad vs Nominatim en una muestra de 20 direcciones
     de Kennedy.
- **Beneficio:** direcciones catastralmente exactas sin depender de
  click manual del usuario.
- **Estado actual mitigado con:** UX transparente (ver hint y feedback
  en `templates/eventos/crear_evento.html`).
- **Esfuerzo:** 1–2 días de investigación + implementación.

### M22 — Mismatch de códigos entre `barrios_kennedy.geojson` y tabla `barrio` [MEDIA]

- **Ubicación:** `apps/georeferenciacion/data/barrios_kennedy.geojson`
  vs. tabla `barrio` en la BD externa.
- **Contexto:** Fase C4.3c del refactor mapa-kennedy (commit `447b098`
  creó los scripts, ejecución el 2026-04-23). El importer
  `import_01_geometries.py` actualiza `barrio.geometry` buscando por
  `codigo` entero. El GeoJSON trae `BAR_COD` con valores tipo `105103`,
  `6511`, `105203`, `6307`… — solo **32 de los 111** hicieron match
  con la tabla `barrio` (325 rows totales). Los otros 79 quedaron con
  `geometry = NULL`.
- **Causa probable:** el `BAR_COD` del GeoJSON proviene de IDECA
  (Infraestructura de Datos Espaciales de Bogotá) con un esquema de
  códigos distinto al usado internamente por `innovaK` en su tabla
  `barrio`. Ambas fuentes son válidas pero usan catastros diferentes.
- **Impacto:**
  - En el mapa, el checkbox "Barrios" solo pinta 32 polígonos.
  - Los otros 79 barrios del GeoJSON existen como polígono en disco
    pero sin fila espejo en BD; la UX no los ve.
  - No rompe nada (endpoint filtra por `geometry IS NOT NULL`).
- **Recomendación:**
  1. Auditar con un join heurístico por `NOMB_BARR` ↔ `barrio.nombre`
     (normalizado, sin tildes) para cuántos rescata por nombre.
  2. Si el match por nombre es alto (>80 %), agregar columna
     `barrio.codigo_ideca` y usarla como clave alterna del importer.
  3. Para los restantes, decidir con datos: crear filas nuevas en
     `barrio` con el código IDECA, o aceptar que quedan fuera.
- **Severidad:** MEDIA — visible en UX pero parcial, no bloquea
  funcionalidad principal.
- **Esfuerzo:** 2–4 horas de análisis + ~100 líneas de migración.

---

## 📐 Convenciones

### C1 — Uso inconsistente del prefijo `public.` en `db_table` [BAJA]

- **Ubicación:** `apps/presupuesto/models/core.py:69,77,85`
- **Descripción:** Solo `Contrato`, `ContratoProyecto` y `ContratoActividad`
  usan `db_table = "public.contrato"` (etc). El resto (>50 clases) usa
  `db_table = "contrato"` sin prefijo. En PostgreSQL con search_path por
  defecto apuntando a `public`, ambos funcionan idénticamente.
- **Recomendación:** Estandarizar — retirar el prefijo `public.` de los
  tres casos o agregarlo a todos. Preferir retirarlo (es redundante).
- **Esfuerzo:** muy bajo.

### C2 — `db_column` declarado a veces sí, a veces no [BAJA]

- **Ubicación:** `apps/kactivo/models/kregistro.py` (EvaluacionParticipante,
  NotaMedica) no declara `db_column` en sus FKs, mientras que otras clases
  de la misma app sí lo hacen.
- **Descripción:** Django infiere `<campo>_id` como columna por defecto,
  así que mientras el nombre coincida funciona. Pero declararlo explícito
  es la convención de este proyecto (por ser BD externa).
- **Recomendación:** Agregar `db_column` explícito a todas las FKs por
  consistencia.
- **Esfuerzo:** bajo.

### C3 — Mix de `IntegerField` y `BigAutoField` como PKs [BAJA]

- **Ubicación:** muchos catálogos en `login/models/models_auxiliares.py`
  usan `IntegerField` como PK manual; otros usan `BigAutoField`.
- **Descripción:** Heredado del schema. No afecta runtime pero
  confunde: algunos catálogos esperan que el programador asigne el ID,
  otros no.
- **Recomendación:** Documentar la convención (quizás: "si el código del
  catálogo es semántico, IntegerField; si no, BigAutoField"). Aplicar
  en refactors futuros.
- **Esfuerzo:** bajo (documentar) — medio (migrar).

### C4 — UPZ y Barrio usan `IntegerField` como FK lógica sin constraint [MEDIA]

- **Ubicación:** `apps/georeferenciacion/models/models_localizacion.py`
- **Descripción:** `UPZ.localidad_codigo` y `Barrio.upz_codigo` son
  `IntegerField` que guardan la referencia por valor, sin `ForeignKey`
  formal. En consecuencia la BD no fuerza integridad referencial y Django
  no puede hacer `select_related` ni joins automáticos.
- **Recomendación:** Convertir a `ForeignKey('UPZ', to_field='codigo',
  db_column='upz_codigo', on_delete=models.DO_NOTHING)`. Verificar que
  la BD ya tenga la FK (si no, agregarla con Alex).
- **Esfuerzo:** medio.

### C5 — Mezcla de idiomas en `votaciones` [BAJA]

- **Ubicación:** `apps/votaciones/models/*.py`
- **Descripción:** Modelos se llaman `Event`, `Candidate`, `Voter`, `Vote`
  con campos mezclando inglés y español (`identidades`, `derechos`,
  `candidato_id`). Choca con el resto del proyecto que es 100% español.
- **Recomendación:** No urgente. Si se tiene que hacer refactor amplio,
  renombrar a `Evento`, `Candidato`, `Votante`, `Voto` (cuidado: colisión
  con `Evento` de login — esta app debería quedarse con su namespace).
- **Esfuerzo:** alto si se renombran tablas, bajo si solo se alias.

### C6 — Sin convención uniforme de `on_delete` [BAJA]

- **Ubicación:** transversal
- **Descripción:** `CASCADE`, `SET_NULL`, `PROTECT`, `DO_NOTHING` se
  mezclan según preferencia del archivo. `DO_NOTHING` es común en
  presupuesto (dejaría filas huérfanas silenciosas).
- **Recomendación:** Documentar la política: CASCADE solo en relaciones
  de composición, PROTECT para catálogos referenciados, SET_NULL para
  relaciones opcionales, DO_NOTHING solo si la BD maneja la cascada.
- **Esfuerzo:** bajo documentar, medio refactorizar.

---

## 📊 Resumen ejecutivo

| Categoría | CRÍTICA | ALTA | MEDIA | BAJA | Total |
|-----------|--------:|-----:|------:|-----:|------:|
| Seguridad | 0 | 1 | 2 | 2 | 5 |
| Performance | 0 | 1 | 1 | 2 | 4 |
| Mantenibilidad | 0 | 2 | 5 | 6 | 13 |
| Convenciones | 0 | 0 | 1 | 5 | 6 |
| **Total** | **0** | **4** | **9** | **15** | **28** |

### Top 3 si tuviéramos 1 sprint

1. **S1 + S2 + S3 + S4** (settings.py → `.env`) — un PR de 1 hora que
   cierra los 2 CRÍTICOS de seguridad. **[✅ HECHO 2026-04-20]**
2. **S5** (secuencias en BD + retirar MAX(id)+1) — habilita crecer sin
   race conditions. Coordinar con Alex para crear `nextval` en
   `persona`, `evento`, `participante`, `cdp`.
3. **M1** (modelos duplicados) — el refactor de `Evento` ya está en
   curso. Aprovechar para limpiar también `Actividad`, `Programa`, `Zona`.

### Quick wins (< 30 min cada uno)

- M4 — borrar `apps/login/models.py`.
- M5 — agregar `apps.py` a `votaciones`.
- M7 — quitar declaraciones duplicadas en settings.
- ~~C1 — quitar prefijo `public.` de los 3 contratos.~~ ✅ **RESUELTO PR-H3** (`868e758`).
- S9 — unificar la estrategia de `.env` (DATABASE_URL vs variables).

---

## 📋 Deuda detectada en sesión 2026-04-25/26 (post PR-A→H4)

### N1 — `Contrato.id` sin secuencia, `contrato_nuevo` sin fallback MAX+1 [ALTA]

- **Ubicación:** `apps/presupuesto/views/catalogo.py` (función `contrato_nuevo`).
- **Problema:** Detectado en PR-H3. La tabla `contrato` NO tiene `DEFAULT nextval()`.
  Intentar crear un contrato desde la UI lanza `null value in column "id"`.
- **Fix:** Aplicar patrón `MAX(id)+1` (ver `apps/presupuesto/views/cdp.py:82`).
  O preferiblemente DDL: `CREATE SEQUENCE contrato_id_seq; ALTER TABLE contrato ALTER COLUMN id SET DEFAULT nextval('contrato_id_seq');`.
- **Workaround actual:** los 96 contratos existentes vienen pre-cargados desde SIPSE, así que no es bloqueante.

### N2 — `proveedor.id` sin secuencia [MEDIA]

- **Ubicación:** Tabla `proveedor` (0 filas, modelo en PR-H2).
- **Problema:** Mismo patrón S5. `proveedor_nuevo` ya tiene fallback MAX+1.
- **Fix canónico:** `CREATE SEQUENCE proveedor_id_seq; ALTER TABLE proveedor ALTER COLUMN id SET DEFAULT nextval('proveedor_id_seq');`.

### N3 — `ContratoProyecto`/`ContratoActividad` sin `id` propio en BD [MEDIA]

- **Ubicación:** Tablas `contrato_proyecto`, `contrato_actividad`.
- **Problema:** Las tablas NO tienen columna `id`. PR-H3 mapeó `contrato` como
  `primary_key=True` (1:1 efectivo en datos actuales — 96/96 contratos a un solo
  proyecto, 98 a actividades 1:1). Si en el futuro un contrato tuviera múltiples
  proyectos/actividades, Django no podría representarlo correctamente.
- **Fix:** `ALTER TABLE contrato_proyecto ADD COLUMN id BIGSERIAL PRIMARY KEY;`
  + ajuste del modelo. Genera 2 warnings W342 cosméticos hoy.

### N4 — FKs sueltas sin declaración formal [BAJA]

- **Ubicaciones:**
  - `Beneficiario.tipo_documento_codigo` (`IntegerField` en `apps/login/models/contratos.py`).
  - `ContratoActividadPlan.meta_proyecto_id` y `concepto_gasto_id` (`IntegerField` en `apps/presupuesto/models/sql.py`).
- **Problema:** Validación a nivel ORM no aplica. Permite IDs inexistentes.
- **Fix:** Convertir a `ForeignKey` con `db_column` apropiado.

### N5 — Selects sin paginación cargando ~7000 personas [MEDIA]

- **Ubicaciones:** `FuncionarioForm` (PR-F), `BeneficiarioForm` (PR-H2).
- **Problema:** El select de `persona` carga `Persona.objects.all()` (6938 filas).
  Funciona pero es pesado en render y UX.
- **Fix recomendado:** Select2 con autocompletado AJAX, o filtrar a personas
  sin Funcionario/Beneficiario activo.

### N6 — `verbose_name_plural` copy-paste en modelos organizativos [BAJA]

- **Ubicación:** `apps/login/models/funcionario.py` líneas 40, 65, 84.
- **Problema:** `Dependencia`, `Subgrupo` y `Cargo` declaran `verbose_name_plural = "Funcionarios"`.
- **Impacto:** Cosmético. Solo afecta Django admin si se activa.

### N7 — `Proyecto.__str__` y `ActividadPlan.__str__` no definidos [BAJA]

- **Ubicación:** `apps/presupuesto/models/core.py`.
- **Problema:** `<select>` muestran representación por defecto. PR-E debió
  usar `label_from_instance` para que se vieran legibles en forms.
- **Fix:** Agregar `__str__` que devuelva `f"{codigo} {nombre[:60]}"`.

### N8 — Tabla `metas` con secuencia oculta sin DEFAULT [BAJA]

- **Ubicación:** Tabla `metas`.
- **Problema:** PR-D detectó que `metas_codigo_seq` existe y está operativa
  pero la columna `codigo` no tiene `DEFAULT nextval()`. Django funciona porque
  el modelo es `AutoField` y llama `nextval()` explícito, pero confunde.
- **Fix trivial:** `ALTER TABLE metas ALTER COLUMN codigo SET DEFAULT nextval('metas_codigo_seq');`.

### N9 — Hub presupuesto y topbar densos [BAJA]

- **Ubicación:** `apps/dashboard/views.py` `hub_presupuesto`, `templates/presupuesto/_topbar.html`.
- **Problema:** Hub con 12 cards y topbar con 13 tabs — sobrecarga cognitiva.
- **Fix:** Agrupar en sub-secciones colapsables: "Plan" (proyectos/programas/objetivos),
  "Dinero" (CDPs/contratos/conceptos), "Resultados" (metas/KPIs/avances/vinculación).

---

## ✅ Deuda RESUELTA en sesión 2026-04-25/27

- ~~**C1** — `db_table = "public.contrato"`~~ ✅ PR-H3 (`868e758`).
  Sin este fix las queries de Contrato fallaban con `relation "public.contrato"
  does not exist` porque Django comilla los nombres. Mismo fix aplicado a
  `ContratoProyecto` y `ContratoActividad`.
- **Bug colateral**: `Lower()` sin importar en `actividad_nueva`
  (`apps/presupuesto/views/catalogo.py:311`) ✅ PR-G (`a91c22c`).
- **Cache permanente de CSS viejo en browsers** ✅ PR-H1 (`a8a3557`):
  cache-buster con mtime de `base.css` inyectado como `?v=N` en base.html.
- ~~**N1** — `Contrato.id` sin fallback en `contrato_nuevo`~~ ✅ Fix `b48a0dd`.
- ~~**N2** — `proveedor.id` sin secuencia~~ ✅ DDL aplicado 2026-04-27:
  `CREATE SEQUENCE proveedor_id_seq` + `ALTER TABLE proveedor ALTER COLUMN id
  SET DEFAULT nextval(...)`. Modelo simplificado (`AutoField`, sin fallback MAX+1).
- ~~**N4** — IntegerField sueltos sin FK formal~~ ✅ Fix `427ec36`.
- ~~**N5** — Selects sin paginación cargando 6938 personas~~ ✅ Fix `70a67c5`
  (Select2 + endpoint AJAX).
- ~~**N6** — `verbose_name_plural` copy-paste~~ ✅ Fix `427ec36`.
- ~~**N7** — `__str__` faltantes en Proyecto/ActividadPlan~~ ✅ Fix `427ec36`.
- ~~**N8** — `metas.codigo` sin DEFAULT nextval~~ ❌ FALSA ALARMA. La columna
  es `IDENTITY ALWAYS` (PostgreSQL 10+) — nativa, no acepta DEFAULT externo.
  No existía deuda real.

## ⚠️ Deuda PENDIENTE (post sesión)

- **N3** — `ContratoProyecto`/`ContratoActividad` sin `id` propio:
  intento de `ALTER ADD COLUMN id BIGSERIAL PRIMARY KEY` falló porque ambas
  tablas tienen PK compuesta `(contrato_id, proyecto_id)` / `(contrato_id,
  actividad_id)`. Solución alternativa requiere agregar `id BIGSERIAL UNIQUE
  NOT NULL` (sin reemplazar PK compuesta) y ajustar modelos para usar `id`
  como PK lógica. Pospuesto: 1:1 efectivo en datos actuales (96/96, 98/98).
- **N9** — Hub presupuesto con 12 cards y topbar con 13 tabs (densidad UX).
