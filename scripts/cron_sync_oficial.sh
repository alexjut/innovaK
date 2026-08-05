#!/usr/bin/env bash
# Sincroniza a diario las fuentes oficiales de innovaK (RUMBO §1.1).
# Idempotente: solo trae lo nuevo/cambiado (upsert por hash).
#
# El orquestador `sync_fuentes_oficiales` es SECO POR DEFECTO: sin --write no
# escribe nada. El cron es el que persiste, por eso pasa --write aquí abajo. Una
# corrida manual sin --write solo muestra qué traería (útil para revisar).
#
# NO incluye las fuentes pesadas (placas domiciliarias: 1,77M filas / horas):
# ésas se refrescan aparte, a mano o en un cron mensual con --incluir-pesadas.
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
REPO="/home/innova/Proyectos/innovaK"
LOGTS="$(date '+%Y-%m-%d %H:%M:%S')"

# logs/ no existe en un checkout limpio; el comando también escribe su propio
# log fechado ahí dentro.
mkdir -p "$REPO/logs"

echo "[$LOGTS] Iniciando sync de fuentes oficiales…"
docker exec "$CONTAINER" python manage.py sync_fuentes_oficiales --write --desde-anio 2024
echo "[$LOGTS] Sync finalizado."
