# Retiro de Templates Django — Plan ordenado

**Estado:** Plan documentado, **NO ejecutado** todavía.
**Bloquea ejecución:** cierre completo de Etapa D + validación E2E del
frontend Angular en producción.

---

## Por qué este documento existe

Etapa D del Plan Frontend migró las funcionalidades del organizador a
Angular (`/app/*`). Una vez que Angular reemplace el flujo cotidiano
de los usuarios autenticados, los templates Django correspondientes
quedan obsoletos y pueden retirarse para reducir deuda.

**Pero NO se retiran todavía**:
- Etapa D vive en una rama feat sin cascadear (`feat/etapa-d-pr5-1-spa-served-from-django`).
- Producción sigue sirviendo todo el flujo viejo HTML — los usuarios
  reales no han migrado.
- Borrar templates antes de validar Angular en producción dejaría a
  los usuarios sin sistema.

Cuando se cascadee Etapa D a producción y se valide el flujo Angular
end-to-end durante una semana, este documento se vuelve la guía de
ejecución del PR-16 final.

## Reglas duras del retiro

1. **Formularios públicos NO se retiran.** Quedan en HTML Django
   (regla B del Plan Frontend) para funcionar en 2G con teléfonos
   viejos sin JS:
   - `templates/banco_iniciativas/form_publico*.html`
   - `templates/jovenes_a_la_e/form_publico*.html`
   - `templates/caracterizacion/wizard_*.html`
   - `templates/eventos/inscripcion_evento.html`
   - `templates/votaciones/scan.html`, `templates/votaciones/voter_*.html`

2. **Mapa Kennedy NO se retira.** Angular lo sirve como iframe del
   Django legacy. Si se retira el template Django, el iframe queda
   roto.
   - Mantener: `templates/geo-mapas/mapa_kennedy.html` y assets de
     Leaflet en `apps/georeferenciacion/static/`.

3. **Admin Django (Jazzmin) NO se toca.** Sigue siendo útil para
   debug, gestión avanzada de modelos y exports puntuales. Templates
   bajo `admin/` y `jazzmin/` quedan intactos.

4. **Eventos / Cursos del docente quedan PARCIALMENTE.** Angular tiene
   placeholders con link al legacy. Templates del organizador HTML
   siguen vivos hasta que se construyan los endpoints DRF
   correspondientes y se reemplace el placeholder por componente
   completo.

## Lista de retiro (cuando Etapa D cascadeé a producción)

### Confirmado para retiro

```
templates/banco_iniciativas/inscripciones_list.html
templates/banco_iniciativas/inscripcion_detalle.html
templates/banco_iniciativas/inscripcion_validar.html
templates/banco_iniciativas/insights.html

templates/jovenes_a_la_e/entregas_list.html
templates/jovenes_a_la_e/entrega_detalle.html
templates/jovenes_a_la_e/insights.html

templates/caracterizacion/list_*.html      (organizador, NO wizards)
templates/caracterizacion/detalle_*.html
templates/dashboard/caracterizaciones_por_evento.html

templates/presupuesto/proyecto_*.html
templates/presupuesto/cdp_*.html
templates/presupuesto/contrato_*.html
templates/presupuesto/indicador_*.html
templates/presupuesto/meta_*.html
templates/presupuesto/avance_*.html

templates/dashboard/hub.html
templates/dashboard/hub_presupuesto.html
templates/dashboard/hub_actividades.html
templates/dashboard/hub_admin.html
templates/dashboard/index.html

templates/login/dashboard.html              (reemplazado por /app/)
templates/login/formulario/index.html       (reemplazado)

templates/votaciones/organizer_*.html
templates/votaciones/dashboard.html
```

### NO retirar (mantener)

```
templates/base.html                         ← layout base de TODO Django
templates/login/login.html                  ← login Django (paralelo a /app/auth/login)
templates/login/logout.html
templates/_partials/*                       ← reutilizado por base.html
templates/perfil/*                          ← Mi perfil Django

templates/banco_iniciativas/form_publico*.html   ← REGLA B
templates/jovenes_a_la_e/form_publico*.html      ← REGLA B
templates/caracterizacion/wizard_*.html          ← REGLA B
templates/eventos/inscripcion_evento.html        ← REGLA B
templates/votaciones/scan.html                   ← REGLA B
templates/votaciones/voter_*.html                ← REGLA B
templates/geo-mapas/mapa_kennedy.html            ← embebido en /app/mapa
templates/eventos/lista_eventos.html             ← organizador, hasta PR Eventos completo
templates/eventos/crear_evento.html              ← idem
templates/eventos/editar_evento.html             ← idem
templates/eventos/insights.html                  ← idem
templates/curso_docente/*                        ← hasta PR Cursos completo
templates/roles/*                                ← hasta PR Admin completo
templates/admin_org/*                            ← hasta PR Admin completo
admin/*, jazzmin/*                                ← Django admin
```

### Apps cuyos templates pueden borrarse al completo

Una vez retirados los templates del organizador, las vistas Django
que los renderizan también se eliminan. Esto reduce ~1500–2000 LOC
y simplifica el routing.

```
apps/banco_iniciativas/views/organizador.py         ← endpoints HTML
apps/jovenes_a_la_e/views/organizador.py
apps/dashboard/views.py::dashboard_home             ← parte solamente
apps/dashboard/views.py::caracterizaciones_por_evento
apps/presupuesto/views/*.py                          ← organizer views
apps/votaciones/views/organizer.py
```

Los **services** y **APIs DRF** correspondientes se conservan — son
los que Angular consume.

## Plan de ejecución (PR-16 cuando aplique)

1. **Validar Angular en producción 7 días.** Toda función del
   organizador probada en `/app/*` con datos reales.

2. **Cascadear** `feat/etapa-d-pr5-1-spa-served-from-django` →
   `desarrollo` → `Pruebas` → `producción`.

3. **Crear rama** `feat/limpieza-templates-etapa-d`.

4. **Borrar en lotes** (un commit por lote, cada uno cascadeado y
   verificado):

   Lote 1: templates de Banco organizador.
   Lote 2: templates de Jóvenes organizador.
   Lote 3: templates de Caracterización organizador.
   Lote 4: templates de Presupuesto organizador.
   Lote 5: templates de Dashboard hub.
   Lote 6: templates de Votaciones organizador.

5. **Quitar las URLs** Django de los templates retirados.

6. **Quitar las views** Django que renderizaban esos templates.

7. **Quitar dependencias muertas** (`django-bootstrap4`,
   `widget_tweaks`, etc. si ya nadie las usa).

8. **Smoke tests** después de cada lote: 329/329 deben seguir
   pasando. Si algún test rompe, el lote se revierte.

## Impacto estimado

- Templates retirados: ~80 archivos.
- Vistas Django retiradas: ~40 funciones.
- LOC retirados: ~3.500–5.000 (templates + views + URLs).
- Dependencias retiradas: 2–3 paquetes Python.
- Build size frontend: sin cambio (Angular ya no comparte código con
  Django HTML).

## Notas de Cascade

Cada lote requiere cascada feat → desarrollo → Pruebas → producción
con sus 329 smoke tests. **No se hace cascada masiva** porque si
alguna URL rota queda referenciada desde un template no retirado,
el sistema rompe. Lote por lote, cada uno verificado.

Cuando todo termine, este documento se archiva en
`docs/_historico/` y se anota en la bitácora de `CLAUDE.md`.
