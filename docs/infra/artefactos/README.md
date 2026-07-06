# Artefactos de infraestructura — InnovaK

Archivos solicitados por el equipo de aprovisionamiento (nube Oracle / Kubernetes).
Corresponden a la rama `produccion`. Ver el análisis completo en
[`../despliegue_kubernetes.md`](../despliegue_kubernetes.md).

| Archivo | Descripción |
|---|---|
| `Dockerfile` | Construcción de la imagen (Python 3.10-slim + Gunicorn 8032). **No** compila la SPA Angular (`frontend/`): ese build hoy es manual en el server (`ng build --base-href=/app/`). Para k8s se recomienda integrarlo como *multi-stage build*. |
| `docker-compose.yml` | Topología actual. **Solo productivos:** `innova_k`, `nginx`, `redis`, `innova_mongo`. ⚠️ `adminer` y `mailhog` son **solo desarrollo — NO desplegar en producción**. |
| `nginx.conf` | Proxy reverso: gzip, rate limiting, cabeceras de seguridad, estáticos/media, `/healthz`, failover. TLS deshabilitado (terminación externa hoy). |
| `requirements.txt` | Dependencias Python (rangos). |
| `requirements-lock.txt` | Versiones fijadas (build determinístico). |

## No incluido (a propósito)

- **`.env` / secretos:** no se versionan ni se adjuntan. Las variables requeridas
  están listadas (solo nombres) en el dossier; los valores se entregan por canal
  cifrado aparte. Secreto crítico: `DOCUMENTOS_AES_KEY` (cifra la PII en MongoDB;
  si se pierde, los documentos son irrecuperables).
- **PostgreSQL:** externa y compartida (`10.100.102.12:5432`), fuera del clúster.
