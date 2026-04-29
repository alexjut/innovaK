# Refactor `crear_evento` — análisis técnico Fase 0

> Snapshot del **2026-04-20 (noche)** sobre la rama
> `feat/integracion-geo-eventos-dashboard`.
>
> Este documento registra el diagnóstico de solo-lectura realizado para
> planear el refactor. **No se ha tocado código**; pausamos antes de
> Fase 1 porque el análisis reveló dos bloqueadores estructurales (ver
> última sección).

---

## 1. View — `apps/login/views/eventos.py`

### Ubicación

- Decoradores en **líneas 221-222**.
- Función `crear_evento(request)` en **líneas 223-275** (53 líneas).

### Flujo actual

- **GET**: lista `Dependencia.objects.all().order_by('nombre')` y
  renderiza `templates/eventos/crear_evento.html`.
- **POST**: lee 6 campos, valida 5 obligatorios, abre
  `transaction.atomic()`, usa `connection.cursor()` para
  `SELECT COALESCE(MAX(id), 0) + 1 FROM evento` seguido de `INSERT`
  raw, recupera el funcionario con ORM, genera QR en base64 y renderiza
  el mismo template con `evento_info` y `qr_code`.

### Cosas BUENAS (conservar)

1. Decoradores `@login_required` + `@group_required('Admin', 'Lider')`.
2. `transaction.atomic()` ya envuelve la operación (línea 240).
3. Generación de QR con `qrcode.make(inscripcion_url)` → base64
   (líneas 258-261).
4. `Funcionario.objects.select_related('persona').get(id=…)` (línea 255).
5. `messages.success/error` para feedback al usuario.
6. UX "crear y mostrar QR" sin redirect — el mismo request muestra el
   resultado.

### Cosas MALAS (arreglar)

1. **`MAX(id)+1` + INSERT raw** (líneas 242-253): race condition
   (deuda S5). El modelo `Evento` ya existe con ORM.
2. **Campo `hora_inicio` se lee pero NO se guarda** (línea 232). El
   template lo marca como `required` pero desaparece silenciosamente.
3. **`except Exception as e`** con `messages.error(request, f"…: {e}")`
   (líneas 265-266): expone interno de BD al usuario.
4. **El INSERT no incluye** `descripcion`, `tipo_evento_codigo`,
   `lugar_incidencia_id`, `actividad_plan_id`, `created_at`,
   `updated_at` — columnas que ya existen en BD.
5. **Imports duplicados**: `import qrcode, io, base64` (líneas 4-6 y 13).
6. **Import no usado aquí**: `from datetime import datetime, date`
   (línea 25) — usado en otras funciones del archivo, no en
   `crear_evento`.
7. **`Funcionario.objects.get(id=…)`** sin try/except: un ID inválido
   hace raise dentro del atomic (rollbackea bien, pero el
   `DoesNotExist` llega al bloque genérico).

### Cosas FALTANTES (agregar)

1. Leer y guardar `actividad_plan_id` del POST (núcleo del refactor).
2. Leer y guardar `descripcion` (opcional, nullable).
3. Leer y guardar `tipo_evento_codigo` (FK a catálogo, opcional).
4. Diferenciar `fecha_inicio` y `fecha_fin` si el formulario va a
   soportar rangos. Hoy ambos reciben la misma fecha.
5. (Para más adelante) `lugar_incidencia_id` — viene con el modal
   Leaflet, fuera de este refactor.

### Campos que lee del POST

| Campo POST | Uso actual | Columna del modelo |
|------------|------------|--------------------|
| `nombre_evento` | `evento.nombre` (opcional) | `nombre` TextField |
| `fecha_realizacion` | `evento.fecha_inicio` **y** `evento.fecha_fin` | `fecha_inicio`/`fecha_fin` DateField |
| `hora_inicio` | **ignorado** | — (el modelo no tiene columna de hora) |
| `dependencia` | `evento.dependencia_id` | FK |
| `subgrupo` | `evento.subgrupo_id` | FK |
| `funcionario` | `evento.funcionario_id` | FK |

### Objetos que crea en cadena

**Solo un objeto**: una fila en la tabla `evento`.

No se crean `Lugar`, `GeoReferenciacion` ni `LugarIncidencia`. La
"creación en cadena" percibida del dominio existe solo en el
**frontend**: selects dependientes `dependencia → subgrupo →
funcionario` con AJAX.

---

## 2. URL — `apps/login/urls.py`

- Línea 8: `from .views.eventos import … crear_evento …`
- Línea 36: `path('evento/crear/', crear_evento, name='crear_evento')`
- Sin decoradores a nivel URL; viven en la función.
- URL completa: `/evento/crear/` (app `login` montada en la raíz `/`).

---

## 3. Template — `templates/eventos/crear_evento.html`

- **Ubicación**: `templates/eventos/crear_evento.html` (221 líneas).
- **Campos del form**: `nombre_evento`, `fecha_realizacion`,
  `hora_inicio`, `dependencia`, `subgrupo`, `funcionario`.
- **Dropdowns dependientes**: JS en `<script>` (líneas 125-220).
  `dependencia` → `fetch /api/subgrupos/?area_id=X` → pobla `subgrupo`
  → `fetch /api/funcionarios/?subgrupo_id=X` → pobla `funcionario`.
- **Colores por dependencia** (líneas 171-218): diccionario JS `THEMES`
  con 5 paletas (1=Inspecciones azul, 2=Despacho violeta, 3=Inversión
  verde, 4=Admin y Financiera amarillo, 5=Policiva roja). Cambia las
  CSS vars `--theme*` al cambiar la dependencia. La dependencia 3
  muestra además un logo del subgrupo con slug.
- **Bloque QR** (104-121): visible solo si `qr_code` llega (POST
  exitoso), con link de inscripción y botón "Crear otro evento".
- **Faltan** dropdowns para `tipo_evento`, cascada
  `proyecto → meta → actividad_plan` y modal Leaflet para
  `lugar_incidencia`.

---

## 4. Modelos — estado actual

Todos los modelos necesarios existen en el código (`managed=False`):

| Modelo | Archivo | Campos clave |
|--------|---------|--------------|
| `Evento` | `apps/login/models/evento.py:37` | id, nombre, descripcion, tipo_evento (FK), dependencia, subgrupo, funcionario, lugar_incidencia, **actividad_plan**, fecha_inicio, fecha_fin, activo, created_at, updated_at |
| `TipoEvento` | `apps/login/models/evento.py:12` | codigo (PK varchar), nombre, descripcion |
| `LugarIncidencia` | `apps/georeferenciacion/models/models_localizacion.py:207` | id, geo_referenciacion (FK) |
| `GeoReferenciacion` | `…:156` | id, latitud/longitud Decimal(9,6), fuente CharField(10), precision CharField(20), lugar (FK) |
| `Lugar` | `…:52` | id, nombre, direccion, localidad/upz/barrio (FK to_field=codigo) |
| `ActividadPlan` | `apps/presupuesto/models/core.py:45` | id, proyecto (FK), actividad (FK), descripcion, unique_together(proyecto, descripcion) |
| `MetaProyectoBD` | `apps/presupuesto/models/indicadores.py:16` | id, meta (FK→MetaBD), proyecto (FK) |
| `Proyecto` | `apps/presupuesto/models/core.py:5` | id, codigo, nombre, programa (FK), subgrupo (FK) |

Hallazgo colateral: `apps/kactivo/models/kasistencia.py:112` tiene otra
clase `Lugar` apuntando a la misma `db_table='lugar'` (deuda M1 ya
documentada). No afecta este refactor si importamos desde
`georeferenciacion`.

---

## 5. Tests

Cero tests relacionados. `grep` sobre `apps/**/test*.py` por
`crear_evento` o `CrearEvento` no devuelve nada. `apps/login/tests.py`
es un stub.

---

## 6. Recomendación técnica

### 6.1 Qué conservar tal cual

- Decoradores en el mismo orden.
- Contrato GET: listar dependencias, render del template.
- Generación de QR.
- Render en el mismo request (sin redirect).
- Template **completo** sin tocar — el JS de temas y la cascada AJAX se
  quedan como están.

### 6.2 Qué envolver con `transaction.atomic`

Ya está envuelto. Mantener el `with transaction.atomic():` y mover
adentro cualquier creación futura de `LugarIncidencia` cuando se
agregue.

### 6.3 Qué reemplazar (`MAX(id)+1` → ???)

Propuesta: usar ORM puro `Evento.objects.create(...)` y confiar en que
PostgreSQL asigne el id por `DEFAULT nextval()`. Si la tabla **no**
tiene la secuencia, fallback al patrón de `apps/presupuesto/views/cdp.py:75-90`
(try `save()`, catch `IntegrityError`, reintento con `MAX(id)+1` y
`force_insert=True` + `messages.warning` pidiendo DDL a Alex).

### 6.4 Cómo recibir `actividad_plan_id`

```python
actividad_plan_id = request.POST.get('actividad_plan_id') or None
```

Validación explícita contra BD antes del `create`:

```python
if actividad_plan_id and not ActividadPlan.objects.filter(id=actividad_plan_id).exists():
    raise ValueError("Actividad de plan inválida.")
```

Pasarlo al create como `actividad_plan_id=actividad_plan_id`. El modelo
lo acepta nullable: si el form no lo envía (transición), el evento se
crea sin él. Lo mismo para `tipo_evento_codigo` y `descripcion`.

### 6.5 Dónde agregar logs / error handling

Reemplazar `except Exception as e: messages.error(request, f"…: {e}")`
por manejadores específicos:

```python
import logging
logger = logging.getLogger(__name__)
# ...
except ActividadPlan.DoesNotExist:
    messages.error(request, "La actividad seleccionada ya no existe.")
except Funcionario.DoesNotExist:
    messages.error(request, "El funcionario responsable no se pudo encontrar.")
except IntegrityError:
    logger.exception("IntegrityError al crear evento")
    messages.error(request, "Hubo un conflicto guardando el evento. Vuelve a intentarlo.")
except Exception:
    logger.exception("Error inesperado al crear evento")
    messages.error(request, "Ocurrió un error inesperado. Revisa los logs.")
```

Nada de `str(exc)` al usuario. El proyecto no tiene logger configurado
(deuda M11); `logging.getLogger(__name__)` escribe a stderr de gunicorn,
suficiente por ahora.

### 6.6 ¿EventoForm (ModelForm) o `request.POST` crudo?

**Sugerencia: quedarnos con `request.POST` crudo por ahora**, con
validación explícita en la view.

Razones:
- El proyecto no usa `ModelForm` ni `forms.Form` en ningún módulo de
  eventos. Introducirlo aquí rompe la convención local.
- Los nombres del HTML (`nombre_evento`, `fecha_realizacion`) no
  matchean con los del modelo (`nombre`, `fecha_inicio`). Un ModelForm
  requeriría campos custom o renombrar el HTML.
- Con 3 campos nuevos (`actividad_plan_id`, `tipo_evento_codigo`,
  `descripcion`) la view sigue siendo pequeña.

Cuándo sí valdría la pena: si aparece un `editar_evento` con las mismas
reglas de negocio + una variante en otra app, entonces un ModelForm
compartido tiene sentido.

### 6.7 Estructura propuesta

```python
@login_required
@group_required('Admin', 'Lider')
def crear_evento(request):
    dependencias = Dependencia.objects.all().order_by('nombre')
    qr_base64 = inscripcion_url = evento_info = None

    if request.method == 'POST':
        # 1) lectura
        nombre = request.POST.get('nombre_evento') or None
        descripcion = request.POST.get('descripcion') or None
        fecha = request.POST.get('fecha_realizacion')
        dependencia_id = request.POST.get('dependencia') or None
        subgrupo_id = request.POST.get('subgrupo') or None
        funcionario_id = request.POST.get('funcionario') or None
        actividad_plan_id = request.POST.get('actividad_plan_id') or None
        tipo_evento_codigo = request.POST.get('tipo_evento') or None

        # 2) validación mínima
        if not (fecha and dependencia_id and subgrupo_id and funcionario_id):
            messages.error(request, "⚠ Fecha, dependencia, subgrupo y funcionario son obligatorios.")
        else:
            try:
                with transaction.atomic():
                    evento = Evento.objects.create(
                        nombre=nombre,
                        descripcion=descripcion,
                        fecha_inicio=fecha,
                        fecha_fin=fecha,
                        activo=True,
                        dependencia_id=dependencia_id,
                        subgrupo_id=subgrupo_id,
                        funcionario_id=funcionario_id,
                        actividad_plan_id=actividad_plan_id,
                        tipo_evento_id=tipo_evento_codigo,  # to_field=codigo
                    )
                    funcionario = Funcionario.objects.select_related('persona').get(id=funcionario_id)
                    # … generación de QR igual a hoy, usando evento.id …
                messages.success(request, "✅ Evento creado correctamente.")
            except IntegrityError as exc:
                # fallback MAX(id)+1 si falta secuencia (como cdp.py)
                ...
            except Funcionario.DoesNotExist:
                messages.error(request, "El funcionario responsable no existe.")
            except Exception:
                logger.exception("Error inesperado al crear evento")
                messages.error(request, "Error inesperado. Revisa logs.")

    return render(request, 'eventos/crear_evento.html', {
        'dependencias': dependencias,
        'qr_code': qr_base64,
        'inscripcion_url': inscripcion_url,
        'evento_info': evento_info,
    })
```

---

## 7. Decisiones abiertas (pendientes de Alex)

1. **Fallback `MAX(id)+1`**: ¿lo mantengo como `cdp.py` (funciona sin
   DDL), o primero creamos `evento_id_seq` y dejamos solo ORM puro?
2. **`hora_inicio`**: el modelo no tiene columna de hora. Opciones:
   - (a) Dejar el input en HTML por UX pero ignorarlo en la view
         (documentado como "UI-only, no persiste").
   - (b) Combinar fecha+hora en un `DateTimeField` (requiere DDL).
   - (c) Quitar el input del template.
3. **Validación de `actividad_plan_id`**: `.filter(id=…).exists()`
   antes de crear (doble roundtrip pero da error claro) o confiar en la
   FK de BD (IntegrityError genérico).
4. **Template**: el refactor de hoy sería **solo backend** (sin
   dropdown de actividad_plan en HTML todavía), ¿cierto? El endpoint
   en cascada proyecto→meta→actividad_plan y el dropdown visual son
   otro PR.

---

## Bloqueadores descubiertos 2026-04-20 (noche)

Durante el diagnóstico detallado se identificaron DOS bloqueadores
grandes para completar el refactor de `crear_evento` según el modelo de
negocio real:

1. **La BD no tiene tablas de KPIs ni avances**
   (`presu_indicador_meta_proyecto` y `presu_avance_ind_periodo` **NO
   existen**). Ver [`HALLAZGO_BD_INCOMPLETA.md`](./HALLAZGO_BD_INCOMPLETA.md).

2. **La BD no relaciona actividad con meta**
   (`actividad_plan.proyecto_id` apunta directo a `proyecto`, NO hay FK
   a `meta_proyecto`). Ver [`MODELO_NEGOCIO_SIPSE.md`](./MODELO_NEGOCIO_SIPSE.md).

**Consecuencia**: el refactor actual puede SEGUIR adelante para
limpiar el código y agregar `actividad_plan_id` al evento, pero NO
podrá alimentar avance de KPIs hasta que se complete la BD.

Las 4 preguntas técnicas originales del refactor (sección 7) quedan
vigentes.
