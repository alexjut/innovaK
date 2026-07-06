# innovaK · KennedyConecta

Sistema de información interno de la **Alcaldía Local de Kennedy** (Bogotá).
Gestiona la población atendida, las actividades culturales y deportivas, la
planeación presupuestal y la georreferenciación de los hechos en el territorio
de la localidad.

> **¿Eres nuevo en el proyecto?** Empieza por [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md)
> (arranque local paso a paso) y ten a mano el [`docs/GLOSARIO.md`](docs/GLOSARIO.md)
> para el vocabulario de dominio (SIPSE, Meta/KPI, CDP, subgrupo, vigencia…).

---

## Qué es

innovaK cubre cuatro grandes dominios, todos ligados a una misma cadena de
gestión pública:

- **Población atendida** — personas, beneficiarios y ~26 catálogos.
- **Actividades** — cursos, capacitaciones, eventos culturales/deportivos,
  caracterizaciones, entregas, banco de iniciativas, festivales.
- **Presupuesto** — proyectos, metas, indicadores (KPI), CDPs y contratos.
- **Territorio** — georreferenciación de lugares y actividades sobre el mapa
  de Kennedy (barrios, UPZ, UPL, escuelas, parques).

La **cadena de negocio central** que atraviesa todo el sistema:

```
Proyecto → MetaProyecto → Meta (KPI) ← Indicador ← ActividadPlan ← Evento → Beneficiario
   │                                                     ▲
   └── CDP → Contrato → ContratoActividadPlan ───────────┘   (lado financiero)
```

Toda captura de datos (un evento, una inscripción, una caracterización) queda
enganchada a esa cadena para poder derivar las matrices de reporte
presupuestal y de ejecución contractual. Ver [`docs/referencia/SIPSE.md`](docs/referencia/SIPSE.md).

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | **Django 4.2.11** + Python 3.10, vistas function-based + **DRF** para la API |
| Base de datos | **PostgreSQL externa** (`poblacion_kennedy`, compartida) — todos los modelos `managed=False` |
| PII cifrada | **MongoDB 7** (firmas y documentos sensibles, cifrado AES) |
| Caché / permisos | **Redis 7** |
| Frontend | **Angular** (SPA única servida por Django bajo `/app/*`) |
| Serving | **Gunicorn** :8032 detrás de **Nginx** :8034, todo en **Docker** |

La UI es **Angular** (`/app/*`). Django actúa como **API REST** (`/api/*`,
Swagger en `/api/docs/`), exports, kiosko de votaciones y `/admin`. Las vistas
HTML antiguas redirigen al SPA. Ver [`docs/frontend/DESPLIEGUE_FRONTEND.md`](docs/frontend/DESPLIEGUE_FRONTEND.md).

---

## Apps (Django)

11 apps activas en `INSTALLED_APPS`:

| App | Responsabilidad |
|-----|-----------------|
| `apps.login` | Persona, Usuario, Funcionario, **Evento** unificado (cursos/eventos/actividades), catálogos, roles dinámicos, cadena de inscripción. Núcleo del sistema. |
| `apps.presupuesto` | Proyectos, programas, metas, indicadores (KPI), CDPs, contratos y la cadena financiera. |
| `apps.georeferenciacion` | Lugares, barrios, UPZ, UPL, escuelas, parques y el mapa de Kennedy. |
| `apps.dashboard` | Hubs, insights y consultas inteligentes (OpenAI). |
| `apps.caracterizacion` | Wizards de caracterización poblacional (6 sectores). |
| `apps.banco_iniciativas` | Banco de Iniciativas Recreodeportivas (captura por QR). |
| `apps.jovenes_a_la_e` | Entrega de becas / Jóvenes a la E (Educación). |
| `apps.entregas` | Entrega de insumos a beneficiarios. |
| `apps.festivales` | Festivales culturales (agrupan N eventos multidía). |
| `apps.votaciones` | Flujo de votación con QR (kiosko, independiente). |
| `apps.documentos` | Almacenamiento cifrado de PII en MongoDB (firmas, soportes). |

> `apps/kordial` y `apps/VitalK` son scaffolds vacíos **no instalados**
> (código muerto pendiente de borrar).

Mapa completo de URLs/vistas/modelos: [`docs/arquitectura/MAPA_APLICACION.md`](docs/arquitectura/MAPA_APLICACION.md).
Arquitectura de alto nivel: [`docs/arquitectura/ARQUITECTURA.md`](docs/arquitectura/ARQUITECTURA.md).

---

## Arranque rápido

```bash
docker compose up -d                              # backend + nginx + redis + mongo
cd frontend && npm run build -- --base-href=/app/ # build del SPA (lo lee Django)
# entra a http://localhost:8034/app/
```

Detalle completo (variables `.env`, requisitos, primer login):
[`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md).

---

## Flujo de trabajo (git)

Staging ascendente: `feat/*` → `desarrollo` → `Pruebas` → `produccion`.
`main` es histórica, **no se usa**. Nunca merge directo a las troncales sin
pasar por las fases previas; nunca `--force` a ramas compartidas. Detalle en
[`CLAUDE.md`](CLAUDE.md) §5.

---

## Documentación

Todo vive en [`docs/`](docs/README.md) (índice maestro). Puntos de entrada:

- **Arranque:** [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md)
- **Vocabulario:** [`docs/GLOSARIO.md`](docs/GLOSARIO.md)
- **Arquitectura:** [`docs/arquitectura/`](docs/arquitectura/)
- **Frontend:** [`docs/frontend/`](docs/frontend/)
- **Manuales por módulo / por rol:** [`docs/manuales_modulos/`](docs/manuales_modulos/README.md) · [`docs/manuales_uso/`](docs/manuales_uso/README.md)
- **Infraestructura / despliegue:** [`docs/infra/`](docs/infra/)
- **Memoria operativa y bitácora del proyecto:** [`CLAUDE.md`](CLAUDE.md)

---

<sub>Alcaldía Local de Kennedy · Bogotá · Owner técnico: Alex (`alexjut`).</sub>
