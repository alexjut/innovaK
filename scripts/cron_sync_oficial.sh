#!/usr/bin/env bash
# Sincroniza a diario las fuentes oficiales (SDP-PDL + SECOP II) en innovaK.
# Idempotente: solo trae lo nuevo/cambiado (upsert por hash).
#
# Instalar en el cron del HOST (no dentro del contenedor), como los backups.
# Ejemplo (todos los días 03:30, después del backup de las 02:00):
#
#   crontab -e
#   30 3 * * *  /home/innova/Proyectos/innovaK/scripts/cron_sync_oficial.sh >> /home/innova/Proyectos/innovaK/logs/sync_oficial.log 2>&1
#
# Requiere que el contenedor innova_k esté arriba.
set -euo pipefail

CONTAINER="innova_k"
LOGTS="$(date '+%Y-%m-%d %H:%M:%S')"

echo "[$LOGTS] Iniciando sync de fuentes oficiales…"
docker exec "$CONTAINER" python manage.py sync_fuentes_oficiales --desde-anio 2024
echo "[$LOGTS] Sync finalizado."
