#!/usr/bin/env bash
# Uso: tools/subir_largo.sh <ID> <ruta/video.mp4>
# Sube el vídeo troceado a la rama temporal subida-<ID>; la Action "Publicar vídeo largo" lo une,
# crea la release y escribe largos/<ID>/url.txt en main.
set -euo pipefail
ID="$1"; VID="$(realpath "$2")"; NOMBRE="$(basename "$VID")"
TMP="$(mktemp -d)"; cd "$TMP"
git init -q; git checkout -q -b "subida-$ID"
git remote add origin https://github.com/shortshistoricos1/videos_terror
git config user.name "Claude"; git config user.email "noreply@anthropic.com"
mkdir partes; split -b 90m -d -a 2 "$VID" partes/parte_
for p in partes/parte_*; do
  git add "$p"; git commit -q -m "Parte $(basename "$p") de $ID"
  git push -q origin "subida-$ID"
  echo "subida $p"
done
echo "$NOMBRE" > nombre.txt
( cd "$(dirname "$VID")" && sha256sum "$NOMBRE" ) > sha256.txt
git add nombre.txt sha256.txt; git commit -q -m "Subida completa de $ID"
git push -q origin "subida-$ID"
echo "Subida completa: subida-$ID"
