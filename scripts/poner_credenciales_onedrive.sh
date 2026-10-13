#!/usr/bin/env bash
# Pone las credenciales de OneDrive en .env, sin que pasen por el chat ni
# queden en el historial del shell.
#
# Existe por lo que pasó con la clave de Kenny: tres intentos fallidos seguidos,
# y los tres por mis instrucciones —un comando con huecos que había que editar—.
# Uno se pegó con la indentación del mensaje adentro y dos dejaron el texto de
# ejemplo literal. Un script que PREGUNTA no tiene esos tres modos de fallar.
#
#   bash scripts/poner_credenciales_onedrive.sh
#
# Qué hace falta antes de correrlo: una app registrada en Entra ID del tenant de
# la Alcaldía, con permiso de APLICACIÓN `Files.ReadWrite.All` y el
# consentimiento del administrador dado. Eso lo emite quien administre el
# tenant; no se puede sacar desde acá.

set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
    echo "✗ No encuentro .env en $(pwd). Abortado."
    exit 1
fi

echo
echo "Credenciales de OneDrive (espejo de soportes del Banco)"
echo "───────────────────────────────────────────────────────"
echo "Lo que se escriba NO se muestra en pantalla."
echo "Enter en blanco deja la variable como está."
echo

leer() {                       # leer VAR "pregunta" [oculto]
    local var="$1" pregunta="$2" oculto="${3:-si}" valor=""
    if [ "$oculto" = "si" ]; then
        read -r -s -p "  $pregunta: " valor
        echo
    else
        read -r -p "  $pregunta: " valor
    fi
    # Se limpian espacios y comillas: pegar desde el portal de Azure los arrastra
    # y un secreto con un espacio al final da 401 sin decir por qué.
    valor="$(printf '%s' "$valor" | tr -d '\r' | sed -e 's/^[[:space:]"'"'"']*//' \
             -e 's/[[:space:]"'"'"']*$//')"
    printf '%s' "$valor"
}

TENANT="$(leer ONEDRIVE_TENANT_ID 'Tenant ID (GUID del directorio)' no)"
CLIENT="$(leer ONEDRIVE_CLIENT_ID 'Client ID (GUID de la aplicación)' no)"
SECRET="$(leer ONEDRIVE_CLIENT_SECRET 'Client secret (el VALOR, no el id)')"
echo
echo "  El destino: UNO de los dos basta."
USUARIO="$(leer ONEDRIVE_USUARIO 'Correo cuyo OneDrive recibe los soportes' no)"
DRIVE=""
if [ -z "$USUARIO" ]; then
    DRIVE="$(leer ONEDRIVE_DRIVE_ID 'Drive ID (GUID), si no dio correo' no)"
fi

# ── Validaciones, antes de tocar el archivo ───────────────────────────────
problemas=()
[ -n "$TENANT" ] || problemas+=("falta el Tenant ID")
[ -n "$CLIENT" ] || problemas+=("falta el Client ID")
[ -n "$SECRET" ] || problemas+=("falta el Client secret")
[ -n "$USUARIO" ] || [ -n "$DRIVE" ] || problemas+=("falta el destino (correo o drive id)")

# El error más común: pegar el ID del secreto en vez de su VALOR. El id es un
# GUID; el valor no lo es y es más largo.
if [ -n "$SECRET" ] && printf '%s' "$SECRET" \
   | grep -qiE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
    problemas+=("el secreto tiene forma de GUID: parece el ID del secreto y no su VALOR")
fi
if [ -n "$SECRET" ] && [ "${#SECRET}" -lt 20 ]; then
    problemas+=("el secreto tiene ${#SECRET} caracteres; los de Entra ID son más largos")
fi
if [ -n "$USUARIO" ] && ! printf '%s' "$USUARIO" | grep -q '@'; then
    problemas+=("el correo no tiene @")
fi
for v in "$TENANT" "$CLIENT"; do
    if [ -n "$v" ] && ! printf '%s' "$v" \
       | grep -qiE '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'; then
        problemas+=("«${v:0:8}…» no tiene forma de GUID")
    fi
done

if [ "${#problemas[@]}" -gt 0 ]; then
    echo
    echo "✗ No se escribió nada:"
    for p in "${problemas[@]}"; do echo "   · $p"; done
    exit 1
fi

# ── Respaldo y escritura ──────────────────────────────────────────────────
RESPALDO=".env.bak.$(date +%Y%m%d_%H%M%S)"
cp "$ENV_FILE" "$RESPALDO"
echo
echo "  respaldo: $RESPALDO"

poner() {                      # poner CLAVE VALOR
    local clave="$1" valor="$2"
    [ -n "$valor" ] || return 0
    if grep -qE "^[[:space:]]*${clave}=" "$ENV_FILE"; then
        # Se reescribe el archivo entero y se mueve encima: con `sed -i` sobre un
        # bind-mount de archivo ÚNICO se cambia el inodo y el contenedor se queda
        # sirviendo el viejo. Ya pasó con nginx.conf.
        grep -vE "^[[:space:]]*${clave}=" "$ENV_FILE" > "$ENV_FILE.tmp"
        printf '%s=%s\n' "$clave" "$valor" >> "$ENV_FILE.tmp"
        cat "$ENV_FILE.tmp" > "$ENV_FILE"
        rm -f "$ENV_FILE.tmp"
    else
        printf '%s=%s\n' "$clave" "$valor" >> "$ENV_FILE"
    fi
    echo "  ✓ $clave (${#valor} caracteres)"
}

poner ONEDRIVE_TENANT_ID     "$TENANT"
poner ONEDRIVE_CLIENT_ID     "$CLIENT"
poner ONEDRIVE_CLIENT_SECRET "$SECRET"
poner ONEDRIVE_USUARIO       "$USUARIO"
poner ONEDRIVE_DRIVE_ID      "$DRIVE"

echo
echo "  reiniciando el contenedor…"
docker compose restart innova_k >/dev/null 2>&1 || docker restart innova_k >/dev/null
sleep 12

echo
echo "  verificando…"
echo
docker exec innova_k python manage.py verificar_onedrive 2>&1 | grep -vE '^ts='
