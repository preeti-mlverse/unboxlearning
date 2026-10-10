#!/usr/bin/env bash
# Build the UnboxEd app + API locally and release it to the VPS.
#
#   SSH_TARGET=user@server ./deploy/deploy-app.sh            (production)
#   SSH_TARGET=user@server TARGET=staging ./deploy/deploy-app.sh
#
# Server layout (one-time setup in docs/foundation/DEPLOY.md):
#   /srv/unboxed[-staging]/releases/<stamp>   each release
#   /srv/unboxed[-staging]/current            symlink to the live release
#   /srv/unboxed[-staging]/venv               Python virtualenv
#   /etc/unboxed/<target>.env                 secrets and settings (never in git)
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SSH_TARGET:?Set SSH_TARGET, e.g. SSH_TARGET=ubuntu@203.0.113.10}"
TARGET=${TARGET:-production}
SUFFIX=$([ "$TARGET" = production ] && echo "" || echo "-$TARGET")
SITE=$([ "$TARGET" = production ] && echo "https://unboxlearning.in" || echo "https://staging.unboxlearning.in")
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "${SSH_KEY:-}" ] && SSH_OPTS+=(-i "$SSH_KEY")

echo "1/5  Tests"
(cd apps/api && python -m pytest -q)
npm --prefix apps/web run typecheck

echo "2/5  Building the web app for $TARGET"
NEXT_PUBLIC_SITE_URL=$SITE npm --prefix apps/web run build
cp -r apps/web/.next/static apps/web/.next/standalone/.next/static
cp -r apps/web/public apps/web/.next/standalone/public

STAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="unboxed-app-$STAMP.tar.gz"
echo "3/5  Packing release $STAMP"
tar -czf "/tmp/$ARCHIVE" apps/api/unboxed_api apps/api/requirements.txt database workers apps/web/.next/standalone

echo "4/5  Uploading"
scp "${SSH_OPTS[@]}" "/tmp/$ARCHIVE" "$SSH_TARGET:/tmp/$ARCHIVE"

echo "5/5  Migrating and switching"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash -s -- "$STAMP" "$ARCHIVE" "$TARGET" "$SUFFIX" <<'REMOTE'
set -euo pipefail
STAMP=$1; ARCHIVE=$2; TARGET=$3; SUFFIX=$4; BASE=/srv/unboxed$SUFFIX
sudo -u unboxed mkdir -p "$BASE/releases/$STAMP"
sudo -u unboxed tar -xzf "/tmp/$ARCHIVE" -C "$BASE/releases/$STAMP"
sudo -u unboxed "$BASE/venv/bin/pip" install -q -r "$BASE/releases/$STAMP/apps/api/requirements.txt"
cd "$BASE/releases/$STAMP"
sudo -u unboxed env $(sudo cat /etc/unboxed/$TARGET.env | grep -v '^#' | xargs) PYTHONPATH=apps/api \
  "$BASE/venv/bin/python" -m alembic -c database/alembic.ini upgrade head
sudo ln -sfn "$BASE/releases/$STAMP" "$BASE/current"
sudo systemctl restart unboxed-api$SUFFIX unboxed-worker$SUFFIX unboxed-web$SUFFIX
rm -f "/tmp/$ARCHIVE"
ls -1dt "$BASE"/releases/* | tail -n +6 | xargs -r sudo rm -rf
echo "Live ($TARGET): $STAMP"
REMOTE
