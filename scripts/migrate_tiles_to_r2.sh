#!/usr/bin/env bash
#
# Migra public/data/tiles (412 MB / ~73.8k archivos) a Cloudflare R2 con rclone.
# Sube en paralelo, es reanudable (rclone copy salta lo ya subido) y NO borra nada local.
#
# Requisitos previos (una sola vez):
#   1) brew install rclone
#   2) En Cloudflare dashboard -> R2 -> "Manage R2 API Tokens" -> crear token con
#      permiso Object Read & Write. Anota: Access Key ID, Secret Access Key y el
#      Account ID (lo ves en la URL del dashboard o en R2 -> Overview).
#   3) Exporta las credenciales antes de correr este script:
#        export R2_ACCOUNT_ID="xxxxxxxxxxxxxxxx"
#        export R2_ACCESS_KEY_ID="xxxxxxxx"
#        export R2_SECRET_ACCESS_KEY="xxxxxxxx"
#
# Uso:
#   bash scripts/migrate_tiles_to_r2.sh            # sube de verdad
#   DRY_RUN=1 bash scripts/migrate_tiles_to_r2.sh  # simula, no sube
#
set -euo pipefail

BUCKET="${R2_BUCKET:-crisis-damage-intelligence}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/public/data/tiles"
DEST_PREFIX="data/tiles"   # => objetos quedan como  data/tiles/<aoi>/<kind>/<z>/<x>/<y>.webp

: "${R2_ACCOUNT_ID:?Falta R2_ACCOUNT_ID}"
: "${R2_ACCESS_KEY_ID:?Falta R2_ACCESS_KEY_ID}"
: "${R2_SECRET_ACCESS_KEY:?Falta R2_SECRET_ACCESS_KEY}"

ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

DRY=""
[ "${DRY_RUN:-0}" = "1" ] && DRY="--dry-run"

echo ">> Origen : $SRC  ($(find "$SRC" -type f | wc -l | tr -d ' ') archivos)"
echo ">> Destino: r2://$BUCKET/$DEST_PREFIX   (endpoint $ENDPOINT)"
echo ">> DRY_RUN: ${DRY_RUN:-0}"

rclone copy "$SRC" ":s3:$BUCKET/$DEST_PREFIX" \
  $DRY \
  --s3-provider Cloudflare \
  --s3-endpoint "$ENDPOINT" \
  --s3-access-key-id "$R2_ACCESS_KEY_ID" \
  --s3-secret-access-key "$R2_SECRET_ACCESS_KEY" \
  --s3-no-check-bucket \
  --header-upload "Content-Type: image/webp" \
  --transfers 32 \
  --checkers 64 \
  --fast-list \
  --progress \
  --stats 5s

echo ">> Listo. Verifica un objeto:"
echo "   curl -sI https://assets.respuestavenezuela.org/${DEST_PREFIX}/emsr884-aoi12-caraballeda/after/16/20555/30824.webp | head -1"
