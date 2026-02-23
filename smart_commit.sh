#!/usr/bin/env bash
set -euo pipefail

# ===========================
# Smart Commit Script (Git)
# ===========================

# Colores (opcionales)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ---- Helpers ----
print_header() {
  echo -e "${BLUE}"
  echo "=============================================="
  echo "      ASISTENTE INTELIGENTE DE COMMITS"
  echo "=============================================="
  echo -e "${NC}"
}

print_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
  local prompt="${1:-¿Continuar?} [s/N]: "
  read -r -p "$prompt" ans
  case "${ans,,}" in
    s|si|sí|y|yes) return 0 ;;
    *) return 1 ;;
  esac
}

require_git_repo() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    print_error "Este directorio no es un repositorio Git."
    exit 1
  fi
}

get_current_branch() {
  git rev-parse --abbrev-ref HEAD
}

show_context() {
  local branch
  branch="$(get_current_branch)"

  echo
  print_info "Rama actual / ambiente detectado: ${branch}"
  echo

  print_info "Branches disponibles:"
  git branch --all || true
  echo

  print_info "Último commit (versión actual visible):"
  git log -1 --pretty=format:'%C(yellow)%h%Creset | %C(cyan)%ad%Creset | %C(green)%an%Creset | %s' --date=short || true
  echo -e "\n"

  print_info "Estado actual del repositorio:"
  git status --short || true
  echo
}

normalize_type() {
  local raw="${1,,}"
  case "$raw" in
    desarrollo|dev) echo "feature" ;;
    estilos|style|css|scss|ui) echo "style" ;;
    fix|bug|error|hotfix) echo "fix" ;;
    docs|documentacion|documentación) echo "docs" ;;
    refactor) echo "refactor" ;;
    test|tests) echo "test" ;;
    chore|infra|docker|ops) echo "chore" ;;
    *) echo "$raw" ;;
  esac
}

detect_env_from_branch() {
  local branch="$1"
  local env_guess="desarrollo"

  case "${branch,,}" in
    main|master) env_guess="produccion" ;;
    pruebas|qa|test) env_guess="pruebas" ;;
    desarrollo|dev) env_guess="desarrollo" ;;
    *) env_guess="desarrollo" ;;
  esac

  echo "$env_guess"
}

main() {
  require_git_repo
  print_header
  show_context

  local current_branch
  current_branch="$(get_current_branch)"

  local default_env
  default_env="$(detect_env_from_branch "$current_branch")"

  # ---- Inputs ----
  echo "Completa los datos del commit:"
  echo

  read -r -p "Tipo de cambio (desarrollo/estilos/fix/docs/refactor/test/chore): " tipo_cambio
  tipo_cambio="$(normalize_type "${tipo_cambio:-feature}")"
  [[ -z "$tipo_cambio" ]] && tipo_cambio="feature"

  read -r -p "Módulo o nombre corto (ej: docker, certificado-intranet): " modulo
  [[ -z "${modulo:-}" ]] && modulo="general"

  read -r -p "Versión (ej: v-1.2): " version
  [[ -z "${version:-}" ]] && version="v-1.0"

  read -r -p "¿Por qué se hizo este cambio?: " motivo
  [[ -z "${motivo:-}" ]] && motivo="ajustes generales"

  read -r -p "¿Quién lo hizo?: " autor
  [[ -z "${autor:-}" ]] && autor="$(git config user.name || echo 'SinNombre')"

  read -r -p "Ambiente (desarrollo/pruebas/produccion) [${default_env}]: " ambiente
  ambiente="${ambiente:-$default_env}"

  # Commit principal (como tu formato deseado)
  local commit_title="${tipo_cambio}_${modulo} ${version}"

  # Commit extendido (con metadata)
  local commit_body
  commit_body=$(
    cat <<EOF
Ambiente: ${ambiente}
Autor: ${autor}
Motivo: ${motivo}
Rama: ${current_branch}
EOF
  )

  echo
  print_info "Resumen del commit a crear:"
  echo "--------------------------------------------------"
  echo "Título : ${commit_title}"
  echo "Cuerpo :"
  echo "${commit_body}"
  echo "--------------------------------------------------"
  echo

  if ! confirm "¿Confirmas que estos datos están bien?"; then
    print_warn "Cancelado por el usuario."
    exit 0
  fi

  # ---- Paso 1: git status ----
  echo
  print_info "Paso 1/6 -> git status"
  git status
  echo

  if ! confirm "¿Continuar con git add . ?"; then
    print_warn "Proceso cancelado antes de agregar cambios."
    exit 0
  fi

  # ---- Paso 2: git add . ----
  print_info "Paso 2/6 -> git add ."
  git add .
  echo

  print_info "Estado después de git add:"
  git status --short
  echo

  if ! confirm "¿Crear commit ahora?"; then
    print_warn "Proceso cancelado antes de commit."
    exit 0
  fi

  # ---- Paso 3: git commit ----
  print_info "Paso 3/6 -> git commit"
  # Usamos commit con título + cuerpo
  git commit -m "${commit_title}" -m "${commit_body}" || {
    print_warn "No se creó commit (posiblemente no hay cambios para commitear)."
    exit 0
  }
  echo

  # ---- Paso 4: git branch ----
  print_info "Paso 4/6 -> git branch (verificación de rama)"
  git branch
  echo

  if ! confirm "¿Hacer git pull de la rama actual (${current_branch})?"; then
    print_warn "Saltando git pull por decisión del usuario."
  else
    # ---- Paso 5: git pull ----
    print_info "Paso 5/6 -> git pull origin ${current_branch}"
    git pull origin "${current_branch}"
    echo
  fi

  if ! confirm "¿Hacer git push origin ${current_branch}?"; then
    print_warn "Push cancelado. El commit quedó local."
    exit 0
  fi

  # ---- Paso 6: git push ----
  print_info "Paso 6/6 -> git push origin ${current_branch}"
  git push origin "${current_branch}"
  echo

  print_info "✅ Proceso completado con éxito."
  print_info "Último commit:"
  git log -1 --pretty=fuller --stat --no-color
}

main "$@"