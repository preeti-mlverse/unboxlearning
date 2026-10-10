#!/usr/bin/env bash
# Release the UnboxEd app to the VPS. Run from your laptop (Git Bash), in the repo:
#
#   SSH_TARGET=ubuntu@203.0.113.10 ./deploy/deploy-app.sh              # staging (the default)
#   SSH_TARGET=ubuntu@203.0.113.10 TARGET=production ./deploy/deploy-app.sh
#
# What happens: tests run here; the server pulls this exact commit from GitHub; Docker rebuilds the images;
# the API container applies database migrations before it starts; then /api/health is checked.
# Rollback: run it again with REF=<older commit sha>.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SSH_TARGET:?Set SSH_TARGET, e.g. SSH_TARGET=ubuntu@203.0.113.10}"
TARGET=${TARGET:-staging}
case "$TARGET" in staging) HOST=staging.unboxlearning.in ;; production) HOST=app.unboxlearning.in ;;
  *) echo "TARGET must be staging or production"; exit 1 ;; esac
SSH_OPTS=(-o StrictHostKeyChecking=accept-new)
[ -n "${SSH_KEY:-}" ] && SSH_OPTS+=(-i "$SSH_KEY")

REF=${REF:-$(git rev-parse HEAD)}
if [ -z "${REF_OVERRIDE_OK:-}" ] && [ -n "$(git status --porcelain)" ]; then
  echo "You have uncommitted changes; the server deploys from GitHub. Commit and push first."; exit 1
fi
if ! git branch -r --contains "$REF" | grep -q origin/; then
  echo "Commit $REF isn't on GitHub yet. Run: git push"; exit 1
fi

if [ "$TARGET" = production ] && [ -z "${SKIP_TESTS:-}" ]; then
  echo "1/3  Tests"
  PY=.venv/Scripts/python; [ -x "$PY" ] || PY=.venv/bin/python
  (cd apps/api && "../../$PY" -m pytest -q -p no:logging)
fi

echo "2/3  Deploying $REF to $TARGET ($HOST)"
ssh "${SSH_OPTS[@]}" "$SSH_TARGET" bash -s -- "$TARGET" "$REF" <<'REMOTE'
set -euo pipefail
TARGET=$1; REF=$2; ENV=/etc/unboxed/$TARGET.env
cd /srv/unboxed
sudo git fetch -q origin && sudo git checkout -q --detach "$REF"
sudo docker compose -p "unboxed-$TARGET" -f docker-compose.prod.yml --env-file "$ENV" up -d --build --remove-orphans
sudo docker image prune -f >/dev/null
REMOTE

echo "3/3  Health check"
for i in $(seq 1 30); do
  if curl -fsS "https://$HOST/api/health"; then echo; echo "Live on https://$HOST ($REF)"; exit 0; fi
  sleep 4
done
echo "!! https://$HOST/api/health didn't answer. On the server: sudo docker compose -p unboxed-$TARGET -f /srv/unboxed/docker-compose.prod.yml logs --tail 100"
exit 1
