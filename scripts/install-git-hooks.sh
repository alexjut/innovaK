#!/usr/bin/env bash
# Instala los hooks de git de innovaK como symlinks.
# Si reinstalas el repo (clone fresco), corre esto una vez.
#
# Uso:
#   bash scripts/install-git-hooks.sh
#
# Para desinstalar:
#   rm .git/hooks/pre-push

set -e
ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="${ROOT}/scripts/git-hooks"
HOOKS_DST="${ROOT}/.git/hooks"

mkdir -p "${HOOKS_DST}"

for hook in "${HOOKS_SRC}"/*; do
    name=$(basename "$hook")
    target="${HOOKS_DST}/${name}"
    chmod +x "$hook"
    ln -sf "$hook" "$target"
    echo "✅ hook instalado: ${name}  →  ${hook}"
done

echo ""
echo "Listo. Próximo 'git push' va a correr smoke tests automáticamente."
echo "Para saltarse en una emergencia: git push --no-verify"
