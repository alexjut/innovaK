# Despliegue de InnovaK en Kubernetes (Oracle Cloud) — Dossier técnico

> Documento de entrega para el equipo de aprovisionamiento de infraestructura
> (nube Oracle / OKE). Recopila la información técnica del ambiente actual con
> cifras reales. Fecha de corte: 2026-06-24.
>
> **Nota de seguridad:** este documento NO contiene secretos (solo nombres de
> variables). La entrega de credenciales se hace por canal cifrado aparte.

---

## 1. Información de la aplicación

- **Repositorio:** GitHub `alexjut/innovaK` (privado). Acceso vía *collaborator*
  o *deploy key* de solo lectura.
- **Rama a desplegar:** `produccion` (flujo `desarrollo → Pruebas → produccion`).
- **Stack:** Django 4.2.11 / Python 3.10 + Gunicorn (3 workers, puerto **8032**)
  detrás de Nginx (publica **8034 → 80**). DRF + JWT. Frontend Angular (SPA)
  servida por Django bajo `/app/`. ~9 módulos, ~204 tablas.
- **Dockerfile:** base `python:3.10-slim`; deps de sistema para PDF (Cairo/Pango),
  `build-essential`, Node 18 para compilar SCSS con webpack. Arranque Gunicorn.
  - ⚠️ El Dockerfile **no compila la SPA Angular** (`frontend/`); hoy ese build se
    hace aparte en el server (`ng build --base-href=/app/`). Para k8s se recomienda
    integrarlo como *multi-stage build* (artefactos reproducibles).
- **docker-compose.yml:** servicios productivos `innova_k`, `innova_nginx`,
  `innova_redis`, `innova_mongo`. `adminer` y `mailhog` son **solo desarrollo**.
- **Nginx:** proxy reverso, gzip, rate limiting (general 60r/s, login 5r/s,
  endpoint público de cédula 10r/min), cabeceras de seguridad, estáticos/media,
  health-check `/healthz`, página de respaldo ante caída. **TLS hoy deshabilitado
  en Nginx** (terminación TLS externa); bloque HSTS listo para activar en HTTPS.

## 2. Variables de entorno

```
DEBUG, SECRET_KEY, ALLOWED_HOSTS, BEHIND_TLS, DJANGO_LOG_LEVEL
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
REDIS_URL
MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PASS, MONGO_DB
DOCUMENTOS_AES_KEY, DOCUMENTOS_MAX_UPLOAD_BYTES
OPENAI_API_KEY, OPENAI_MODEL
ONEDRIVE_TOKEN
QR_TOKEN_ENFORCE, RATE_LIMIT_ENABLED
```

**Secretos** (→ Kubernetes Secrets / vault, NO ConfigMap): nunca en texto plano en el repo ni en imágenes.

Entrega segura: gestor de secretos del cliente, sobre sellado o sesión presencial.
Nunca por correo.

## 3. Bases de datos y servicios externos

- **PostgreSQL (principal) — EXTERNA y COMPARTIDA:** `10.100.102.12:5432`, base
  `poblacion_kennedy`, auth usuario/contraseña. ≈ **26 MB**, ~204 tablas.
  `managed=False` (esquema administrado por la entidad dueña; compartida con
  otros sistemas de la Alcaldía).
- **Redis 7:** caché de app + caché de permisos (+ infraestructura channels).
  `maxmemory 256mb`, `allkeys-lru`. Uso real ínfimo (~7 MB).
- **MongoDB 7:** documentos **cifrados AES-256** (firmas, documentos de identidad
  capturados en campo). ≈ **542 MB**. Auth root. Requiere persistencia + respaldo.
- **APIs externas:** OpenAI (dashboard IA), OneDrive (token, opcional). SMTP: hoy
  MailHog en dev; producción **sin relay SMTP** (a definir).
- **Red:** el pod de la app **debe alcanzar `10.100.102.12:5432`** (PostgreSQL en
  red interna). Principal requisito de conectividad del clúster.

## 4. Persistencia y almacenamiento

| Recurso | Tamaño actual | Persistencia | Respaldo |
|---|---|---|---|
| MongoDB (`/data/db`) | ~542 MB | **PVC requerido** | A implementar (hoy sin backup) |
| Media (`/app/media`) | ~4.8 MB | PVC / object storage | — |
| Static + SPA (`/app/staticfiles`) | ~89 MB | Generado en build | — |
| Redis (`/data`) | ~2 MB | Opcional (caché) | No requiere |
| PostgreSQL | ~26 MB | **Externa** | `pg_dump` cron 2:00 AM (diario/semanal/mensual ~2 MB) |

**Brecha:** MongoDB hoy sin respaldo automático y contiene PII cifrada → incluir
en el plan de backup del clúster.

## 5. Infraestructura requerida

- **Consumo actual (reposo):** `innova_k` ~357 MiB / ~0% CPU; `innova_mongo`
  ~101 MiB; `innova_redis` ~7 MiB; `innova_nginx` ~4 MiB.
- **Requests/limits sugeridos:** App `requests` 0.25 vCPU / 512 MiB, `limits`
  1 vCPU / 1 GiB por pod (Gunicorn 3 workers). Mongo 0.25–0.5 vCPU / 512 MiB–1 GiB
  + PVC. Redis 256 MiB.
- **Concurrencia:** uso interno (Localidad de Kennedy), del orden de **decenas de
  usuarios concurrentes**, con picos en jornadas de campo.
- **HA / escalamiento:** app *stateless* (JWT + Redis/PostgreSQL) → **2–3 réplicas**
  tras `Service`. Mongo/Redis instancia única con PVC o servicios gestionados OCI.
  HPA opcional.

## 6. Seguridad y acceso

- **TLS/SSL:** requerido (hoy túnel temporal). Certificado para el dominio
  definitivo (cert-manager/Let's Encrypt o certificado de la Alcaldía).
- **Dominio:** actual `intranet-public-alk.ngrok.app` (temporal). **Pendiente el
  subdominio definitivo.**
- **Acceso:** uso interno; formularios públicos de captura ciudadana por QR
  protegidos con token HMAC (`QR_TOKEN_ENFORCE`, hoy modo suave). Conviene
  restringir el panel admin por lista blanca de IP/VPN.

## 7. Automatización y despliegue

- **CI/CD:** sin pipeline formal. Flujo `feat/* → desarrollo → Pruebas →
  produccion`. Hook `pre-push` corre **415 pruebas de humo** antes del push.
- **Despliegue actual:** `git pull` + reconstrucción/reinicio del contenedor
  (`docker compose restart innova_k`). Build de la SPA manual.
- **Rollback:** retorno a commit anterior + reinicio (las 4 ramas mantienen
  historial sincronizado).

## 8. Respuestas a las consultas del equipo de nube

1. **¿BD dentro o fuera del clúster?** → **Fuera.** PostgreSQL compartida
   (`managed=False`); no se conteneriza. El clúster requiere ruta de red a
   `10.100.102.12:5432`.
2. **¿Redis/Mongo en clúster o existentes?** → Hoy autogestionados. Propuesta:
   desplegar **dentro del clúster** (Redis Deployment; **MongoDB StatefulSet +
   PVC**) o usar gestionados OCI. Mongo requiere persistencia + respaldo.
3. **¿Clúster existente o aprovisionar?** → **No existe.** Se requiere apoyo para
   aprovisionar (idealmente OKE).
4. **¿Manifiestos/Helm?** → **No.** Solo `docker-compose.yml`. A construir
   Deployment/Service/Ingress/ConfigMap/Secret/PVC (o Helm Chart).
5. **¿DR / monitoreo?** → Hoy básico (healthchecks + página de respaldo + backup
   diario PostgreSQL). Deseable: probes liveness/readiness, logs centralizados,
   métricas, **respaldo de MongoDB** (hoy ausente), TLS gestionado.

---

## Anexo: artefactos a compartir

- `Dockerfile`, `docker-compose.yml`, `nginx.conf` (en el repositorio).
- `requirements.txt` (Django 4.2.11, DRF 3.15, simplejwt 5.3, channels 4,
  redis 5.3, pymongo 4.6, psycopg2, cryptography, reportlab, openpyxl, qrcode,
  openai 1.10, entre otros).
