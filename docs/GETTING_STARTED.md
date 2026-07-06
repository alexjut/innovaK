# Arranque local — innovaK

Guía paso a paso para levantar el sistema en tu máquina. Consolida los
comandos que estaban dispersos en [`/CLAUDE.md`](../CLAUDE.md) §4 y en
[`frontend/DESPLIEGUE_FRONTEND.md`](frontend/DESPLIEGUE_FRONTEND.md).

> **Antes de empezar:** familiarízate con el [`GLOSARIO.md`](GLOSARIO.md) y con
> la [`arquitectura/ARQUITECTURA.md`](arquitectura/ARQUITECTURA.md). El sistema
> se conecta a una **base de datos PostgreSQL externa compartida** — no es una
> BD local que puedas recrear con migraciones (todos los modelos son
> `managed=False`).

---

## 1. Requisitos

- **Docker** + **Docker Compose**.
- **Node 20+** y **npm** (para construir el frontend Angular).
- Acceso de red a la base de datos externa `poblacion_kennedy`
  (`10.100.102.12:5432`) — pídelo a Alex si no lo tienes.
- El archivo **`.env`** con los secretos. **No está en el repo** (gitignored).
  Pídeselo a Alex por canal seguro (nunca por correo).

---

## 2. Variables de entorno (`.env`)

El `.env` vive en la raíz del repo y **nunca se versiona**. Variables que
espera el sistema (valores reales los entrega Alex):

```
DEBUG, SECRET_KEY, ALLOWED_HOSTS, DJANGO_LOG_LEVEL, BEHIND_TLS
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD      # PostgreSQL externa
MONGO_PASS, DOCUMENTOS_AES_KEY                       # MongoDB + cifrado PII
OPENAI_API_KEY, OPENAI_MODEL                         # dashboard IA (opcional)
ONEDRIVE_TOKEN                                       # soportes (opcional)
QR_TOKEN_ENFORCE, RATE_LIMIT_ENABLED                 # hardening
```

`DOCUMENTOS_AES_KEY` es **crítica**: cifra la PII (firmas, documentos) en
MongoDB. Sin ella no se pueden leer los documentos cifrados existentes.

Referencia completa de variables y despliegue en producción:
[`infra/despliegue_kubernetes.md`](infra/despliegue_kubernetes.md).

---

## 3. Levantar el backend

```bash
# Desde la raíz del repo
docker compose up -d
```

Esto levanta 4 contenedores:

| Contenedor | Rol | Puerto |
|------------|-----|--------|
| `innova_k` | Django + Gunicorn | 8032 (interno) |
| `innova_nginx` | Reverse proxy | **8034** (expuesto) |
| `innova_redis` | Caché y permisos | 6379 (interno) |
| `innova_mongo` | PII cifrada | 27017 (interno) |

Comprueba que arrancó:

```bash
docker logs -f innova_k          # logs en vivo
curl -I http://localhost:8034/   # debe responder 302 (redirect a /app/)
```

---

## 4. Construir el frontend (Angular)

El SPA se sirve desde Django bajo `/app/*`. **Siempre** se construye con
`--base-href=/app/` (si no, los assets se piden en la raíz y dan 404):

```bash
cd frontend
npm ci                              # primera vez
npm run build -- --base-href=/app/
```

El resultado queda en `frontend/dist/` y Django lo lee directo del
filesystem — **no** necesitas reiniciar el container ni correr
`collectstatic`.

> Desarrollo interactivo con recarga: `npm start` levanta el dev-server de
> Angular en `:4200`. Nota: el firewall del servidor remoto bloquea `:4200`,
> por eso en el servidor la única vía es el build servido bajo `/app/*`.

---

## 5. Entrar

| URL | Qué sirve |
|-----|-----------|
| `http://localhost:8034/app/` | **La aplicación** (Angular SPA) |
| `http://localhost:8034/app/auth/login` | Login (JWT) |
| `http://localhost:8034/api/docs/` | Swagger UI de la API |
| `http://localhost:8034/admin/` | Django admin (solo superuser) |

Cada usuario cambia su contraseña en `/app/perfil`. Los roles y módulos
visibles se calculan por permisos dinámicos (ver [`GLOSARIO.md`](GLOSARIO.md)
→ *Roles y módulos*).

---

## 6. Comandos frecuentes

```bash
# Shell de Django
docker exec -it innova_k python manage.py shell

# Management commands (seeds, etc.)
docker exec -it innova_k python manage.py <comando>

# Smoke tests (los corre también el hook pre-push)
docker exec -it innova_k python scripts/run_smoke_tests.py

# Reiniciar solo Django
docker compose restart innova_k
```

---

## 7. Cosas que NO debes hacer sin confirmar con Alex

- Ejecutar **DDL/DML** contra la BD externa (es compartida con otros sistemas).
- Tocar `docker-compose.yml`, `nginx.conf`, `Dockerfile` o `.env`.
- `git push` a ramas compartidas o merge directo a `produccion`/`Pruebas`/`desarrollo`.
- Correr scripts en `apps/*/scripts/` o `management/commands/` que modifiquen datos.

Reglas completas de aprobación en [`/CLAUDE.md`](../CLAUDE.md) §9.
