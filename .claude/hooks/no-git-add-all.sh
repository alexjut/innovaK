#!/bin/bash
# Bloquea `git add -A`, `git add .`, `git add --all` y `git commit -a`.
#
# POR QUÉ EXISTE: en esta máquina hay UN solo checkout del repositorio y
# trabajan dos personas a la vez (dos perfiles de Claude Code). Un `git add -A`
# no distingue de quién es cada archivo: se lleva al índice el trabajo sin
# commitear del otro.
#
# Ya pasó. El 2026-08-24, un `git add -A` en un commit de DOCUMENTACIÓN arrastró
# 380 líneas sin commitear del panel de subgrupo —el buscador y los filtros que
# estaba escribiendo Anderson— a un commit que no tenía nada que ver. Se
# rescataron en `wip/anderson-subgrupo-panel`, pero se pudieron haber perdido.
#
# El arreglo es barato: nombrar los archivos que uno sí escribió.
#     git add docs/nota.md brain/
#
# Si de verdad hace falta agregar todo (por ejemplo, en un repo donde se trabaja
# solo), córrelo en una terminal fuera de Claude Code.
set -uo pipefail

entrada="${CLAUDE_TOOL_INPUT:-}"

RX='(^|[;&|]|&&|\|\|)[[:space:]]*git[[:space:]]+(add|commit)[[:space:]]+([^;&|]*[[:space:]])?(-[A-Za-z]*[aA][A-Za-z]*|--all|\.)([[:space:]]|$)'

if grep -qE "$RX" <<< "$entrada"; then
  cat >&2 <<'MSG'
BLOQUEADO: `git add -A` / `git add .` / `git commit -a` en este repositorio.

Acá trabajan dos personas sobre el MISMO árbol, así que "todo" incluye el
trabajo sin commitear del otro. Ya se arrastraron 380 líneas ajenas una vez.

Usa rutas explícitas — sólo lo que tú escribiste:
    git add docs/mi-nota.md brain/
    git commit -m "..."

Para ver qué hay suelto antes de decidir:
    git status --short
MSG
  exit 2
fi
exit 0
