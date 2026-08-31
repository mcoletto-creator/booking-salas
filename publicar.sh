#!/usr/bin/env bash
# Sube esta carpeta al repo de GitHub. Correlo desde tu máquina, no desde el chat.
#
#   ./publicar.sh "v1.4 inventario real de 47 salas en 8 sedes"
#
# La primera vez, creá el repo vacío en GitHub y exportá su URL:
#   export REPO=git@github.com:usuario/landing-salas.git
set -euo pipefail
MSG="${1:-actualizacion del prototipo}"

if [ ! -d .git ]; then
  echo "Inicializando repo"
  git init -b main
  if [ -n "${REPO:-}" ]; then git remote add origin "$REPO"; fi
fi

git add -A
if git diff --cached --quiet; then
  echo "No hay cambios para subir."
  exit 0
fi
git commit -m "$MSG"
git push -u origin main
echo
echo "Listo. Para publicar la página: Settings -> Pages -> Source main, carpeta / (root)."
