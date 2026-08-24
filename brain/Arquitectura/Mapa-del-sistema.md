# Mapa del sistema

innovaK es el sistema de información de la **Alcaldía Local de Kennedy**.
Django (API) + Angular (toda la UI, bajo `/app/`) + PostgreSQL externa.

> El HTML de Django murió el 2026-06-11. Django quedó como **API, exports,
> kiosko de votación y `/admin`**. Lo único que aún se renderiza en el servidor
> es `votaciones/scan.html`. No agregar templates.

## Las 13 apps y para qué son

| App | De qué se ocupa | Nota |
|---|---|---|
| `login` | Persona, Usuario, Funcionario, Evento, cursos, catálogos, **permisos** | el corazón: casi todo cuelga de acá |
| `presupuesto` | proyectos, metas, KPIs, CDP, contratos, [[Mi-Area]], [[Dashboard-360]] | ver [[Contrato]] |
| `georeferenciacion` | Lugar, Barrio, UPZ, estratos, colegios, CAI, mapa | ver [[Territorio]] |
| `caracterizacion` | 6 wizards por sector (cultura, deporte, mujer, salud, poblacional, participación) | [[Captura-ciudadana]] |
| `banco_iniciativas` | inscripciones recreodeportivas + rúbrica de puntaje | [[Captura-ciudadana]] |
| `jovenes_a_la_e` | becas y dotación (convenios 773/955-2025) | [[Captura-ciudadana]] |
| `entregas` | entrega de insumos a personas, con firma | [[Captura-ciudadana]] |
| `festivales` | festivales de Cultura + encuesta de percepción | [[Captura-ciudadana]] |
| `educacion` | colegios distritales e insumos entregados | 48 colegios / 79 sedes |
| `dashboard` | hub, cockpit, Dash/Plotly, **asistente Kenny (LLM)** | |
| `documentos` | **librería de servicios**: Mongo, OneDrive, cifrado, PDF | sin `urls.py` a propósito; la consumen 10+ módulos |
| `votaciones` | votación con QR — independiente | única en **inglés**, y el único `render()` vivo |
| `onboarding` | tour guiado de Kenny | |

## La cadena que atraviesa todo

```
Proyecto → Meta → KPI ← ActividadPlan ← Evento → Beneficiarios
   │                          ↑
   └→ CDP → Contrato ─────────┘
```

Toda captura ciudadana termina alimentando un KPI por esta vía. Ver
[[Captura-ciudadana]].

## Reglas transversales del código

- **Todo `managed=False`.** BD externa y compartida: ningún modelo dispara
  migraciones. Ver [[Ambientes-y-despliegue]].
- **Español** en modelos, campos, URLs y vistas. Excepción: `votaciones`.
- **`db_column` explícito** en toda FK.
- **Dos capas de API conviven**: vistas AJAX viejas (función + `JsonResponse`) y
  **DRF** para todo lo nuevo. Mirar en cuál se está antes de tocar.
- **Lógica de negocio en `services/`**, no en las vistas.

Relacionado: [[Permisos-y-roles]] · [[Captura-ciudadana]] · [[Territorio]] · [[Mi-Area]]
