#!/usr/bin/env bash
# Mantenimiento diario de innovaK: deja al día lo que hoy dependía de que
# alguien se acordara de correrlo.
#
#   1. Avance de los KPI de becas, por vigencia.
#   2. Catálogo de instituciones desde los beneficiarios cargados.
#   3. Purga de borradores del Banco vencidos (habeas data: llevan cédulas).
#
# Todo es IDEMPOTENTE y RECALCULA en vez de acumular: si un día no corre, el
# siguiente se pone al día solo. Por eso se puede programar sin miedo.
#
# El comando es SECO POR DEFECTO; el cron es el que persiste, por eso pasa
# --aplicar aquí abajo. Correrlo a mano sin la bandera muestra qué haría.
#
# Instalar en el cron del HOST (no dentro del contenedor), como los backups y
# el sync de fuentes oficiales:
#
#   crontab -e
#   0 4 * * * /usr/bin/flock -n -E 0 /tmp/innovak_mantenimiento.lock \
#     /home/innova/Proyectos/innovaK/scripts/cron_mantenimiento_diario.sh \
#     >> /home/innova/Proyectos/innovaK/logs/mantenimiento_diario.log 2>&1
#
# 04:00: después del backup (02:00) y del sync de fuentes oficiales (03:30),
# que es de donde salen los datos que esto recalcula. El `flock` evita que dos
# corridas se solapen si una se demora; `-E 0` hace que salirse por el lock no
# cuente como error y no llene el correo del cron.
#
# Requiere que el contenedor innova_k esté arriba.
set -euo pipefail

CONTAINER="innova_k"
REPO="/home/innova/Proyectos/innovaK"

mkdir -p "$REPO/logs"

if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "[$(date '+%F %T')] ⚠ El contenedor ${CONTAINER} no está corriendo. Se omite."
    exit 0
fi

echo "[$(date '+%F %T')] ── Mantenimiento diario ──"
docker exec "$CONTAINER" python manage.py mantenimiento_diario --aplicar
echo "[$(date '+%F %T')] ── Fin ──"
