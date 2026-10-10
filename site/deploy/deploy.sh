#!/usr/bin/env bash
# Build the UnboxEd site and publish it to the VPS.
#
# Usage (from Git Bash, in the site folder):
#   SSH_TARGET=user@your.server.ip ./deploy/deploy.sh
# Optional: SSH_KEY=~/.ssh/your_key   (defaults to your normal SSH key / agent)
#
# Each release goes to /var/www/unboxlearning/releases/<timestamp>, and "current" is switched to it
# in one step, so visitors never see a half-uploaded site. The last 5 releases are kept for rollback.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SSH_TARGET:?Set SSH_TARGET, e.g. SSH_TARGET=ubuntu@203.0.113.10}"
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "${SSH_KEY:-}" ] && SSH_OPTS+=(-i "$SSH_KEY")

echo "1/4  Building and checking links"
python build.py --env production --check   # forms point at app.unboxlearning.in

STAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="unboxed-site-$STAMP.tar.gz"
echo "2/4  Packing public/ -> $ARCHIVE"
tar -czf "/tmp/$ARCHIVE" -C public .

echo "3/4  Uploading"
scp "${SSH_OPTS[@]}" "/tmp/$ARCHIVE" "$SSH_TARGET:/tmp/$ARCHIVE"

echo "4/4  Switching the live site to this release"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash -s -- "$STAMP" "$ARCHIVE" <<'REMOTE'
set -euo pipefail
STAMP=$1; ARCHIVE=$2; BASE=/var/www/unboxlearning
sudo mkdir -p "$BASE/releases/$STAMP"
sudo tar -xzf "/tmp/$ARCHIVE" -C "$BASE/releases/$STAMP"
sudo ln -sfn "$BASE/releases/$STAMP" "$BASE/current"
sudo chown -R www-data:www-data "$BASE" 2>/dev/null || true
rm -f "/tmp/$ARCHIVE"
ls -1dt "$BASE"/releases/* | tail -n +6 | xargs -r sudo rm -rf
sudo nginx -t >/dev/null && sudo systemctl reload nginx
echo "Live release: $STAMP"
REMOTE
rm -f "/tmp/$ARCHIVE"
echo "Done: https://unboxlearning.in"
