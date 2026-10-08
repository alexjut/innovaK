#!/usr/bin/env bash
# Pone la credencial del asistente KENNY y lo deja verificado.
#
#   bash scripts/poner_clave_kenny.sh
#
# Existe porque pegar la clave a mano salió mal tres veces seguidas el
# 2026-10-08: una con espacios al inicio —que `load_dotenv` no lee— y dos
# dejando el TEXTO DE EJEMPLO del comando en lugar de la llave. Acá no hay
# nada que sustituir: el script pregunta.
#
# La clave se lee OCULTA y nunca se imprime, ni se queda en el historial del
# shell. Se valida antes de escribir nada.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV="$RAIZ/.env"
[ -f "$ENV" ] || { echo "No encuentro $ENV"; exit 1; }

echo
echo "  Credencial del asistente KENNY"
echo "  ──────────────────────────────"
echo "  Saque una gratis en console.groq.com -> API Keys -> Create API Key."
echo "  No piden tarjeta. Empieza por 'gsk_'."
echo
read -r -s -p "  Pegue la clave (no se va a ver): " CLAVE
echo
CLAVE="$(printf '%s' "$CLAVE" | tr -d '[:space:]')"

# ── Validaciones, para no repetir los errores de hoy ──────────────────
if [ -z "$CLAVE" ]; then
    echo "  No pegó nada. No se tocó el archivo."; exit 1
fi
if [ ${#CLAVE} -lt 30 ]; then
    echo "  Esa clave mide ${#CLAVE} caracteres y es demasiado corta."
    echo "  Las de Groq pasan de 50. Parece un texto de ejemplo."
    echo "  No se tocó el archivo."; exit 1
fi
case "$CLAVE" in
    *LA_QUE_LE_DIO*|*la_clave_que*|*PEGUE*|*AQUI*|*su_clave*)
        echo "  Eso es un texto de ejemplo, no una llave. No se tocó el archivo."
        exit 1;;
esac

# ── Escribir: reemplaza la línea si existe, la agrega si no ───────────
cp "$ENV" "$ENV.bak.$(date +%Y%m%d%H%M%S)"
if grep -q '^[[:space:]]*MISTRAL_API_KEY=' "$ENV"; then
    # El `|` como separador: una clave puede traer `/`.
    sed -i "s|^[[:space:]]*MISTRAL_API_KEY=.*|MISTRAL_API_KEY=$CLAVE|" "$ENV"
else
    printf '\nMISTRAL_API_KEY=%s\n' "$CLAVE" >> "$ENV"
fi
# La URL y el modelo, solo si faltan: no se pisa lo que ya haya elegido.
grep -q '^MISTRAL_API_URL=..*' "$ENV" || \
    printf 'MISTRAL_API_URL=https://api.groq.com/openai/v1\n' >> "$ENV"
grep -q '^MISTRAL_MODEL=..*' "$ENV" || \
    printf 'MISTRAL_MODEL=openai/gpt-oss-20b\n' >> "$ENV"
# Por si quedó sangría de un pegado anterior: con espacio delante no se lee.
sed -i -E 's/^[[:space:]]+(MISTRAL_[A-Z_]+=)/\1/' "$ENV"

echo "  Guardada: ${#CLAVE} caracteres. Respaldo del .env hecho."
echo
echo "  Reiniciando el contenedor para que la lea..."
docker compose -f "$RAIZ/docker-compose.yml" restart innova_k >/dev/null 2>&1
sleep 12
echo
docker exec innova_k python manage.py verificar_kenny 2>&1 | grep -v '^ts='
