#!/usr/bin/env bash
# One-time setup of the VPS for the UnboxEd app (staging + production). Run ON THE SERVER as a sudo user:
#
#   curl -fsSL https://raw.githubusercontent.com/preeti-mlverse/unboxlearning/main/deploy/server-setup.sh -o setup.sh
#   sudo bash setup.sh you@example.com        # the email is for Let's Encrypt certificate notices
#
# It is safe to run again. It:
#   1. installs Docker, nginx, certbot and git (Ubuntu/Debian)
#   2. clones the repo to /srv/unboxed
#   3. creates /etc/unboxed/{staging,production}.env with fresh random secrets (SMTP and Google left blank for you)
#   4. adds nginx sites for app.unboxlearning.in and staging.unboxlearning.in and gets HTTPS certificates
#      (DNS A records for both names must already point at this server)
#   5. installs a nightly database backup
set -euo pipefail
EMAIL=${1:?usage: sudo bash server-setup.sh you@example.com}
REPO=https://github.com/preeti-mlverse/unboxlearning.git
APP_DIR=/srv/unboxed

echo "== 1/5 packages"
if ! command -v docker >/dev/null; then curl -fsSL https://get.docker.com | sh; fi
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx git openssl >/dev/null
systemctl enable --now docker nginx

echo "== 2/5 code"
if [ -d "$APP_DIR/.git" ]; then git -C "$APP_DIR" pull --ff-only; else git clone "$REPO" "$APP_DIR"; fi

echo "== 3/5 settings"
mkdir -p /etc/unboxed && chmod 700 /etc/unboxed
make_env() {  # name host api_port web_port cookie_domain site_url
  local f=/etc/unboxed/$1.env
  if [ -f "$f" ]; then echo "   $f exists, left as is"; return; fi
  cat > "$f" <<EOF
# UnboxEd $1 settings. Secrets live only here (chmod 600). Edit, then redeploy: deploy/deploy-app.sh
ENV_FILE=$f
ENVIRONMENT=$1
API_PORT=$3
WEB_PORT=$4
DB_PASSWORD=$(openssl rand -hex 24)
SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n=+/')
APP_URL=https://$2
SITE_URL=$6
COOKIE_DOMAIN=$5
COOKIE_SECURE=true
REQUIRE_EMAIL_VERIFICATION=true

# Email (see docs/foundation/EMAIL_AND_GOOGLE.md). Until filled in, emails are written to the storage volume.
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=UnboxEd <no-reply@unboxlearning.in>

# Sign in with Google (see docs/foundation/EMAIL_AND_GOOGLE.md). Leave blank to keep it off.
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
EOF
  chmod 600 "$f"
  echo "   created $f"
}
# production shares its session with the marketing site (.unboxlearning.in); staging keeps its cookies to itself
make_env production app.unboxlearning.in 8040 3010 .unboxlearning.in https://unboxlearning.in
make_env staging staging.unboxlearning.in 8041 3011 "" https://unboxlearning.in

echo "== 4/5 nginx + HTTPS"
site() {  # name host api_port web_port
  sed -e "s/app.unboxlearning.in/$2/" -e "s/127.0.0.1:8040/127.0.0.1:$3/" -e "s/127.0.0.1:3010/127.0.0.1:$4/" \
      "$APP_DIR/deploy/nginx-app.conf" > "/etc/nginx/sites-available/unboxed-$1"
  ln -sf "/etc/nginx/sites-available/unboxed-$1" "/etc/nginx/sites-enabled/unboxed-$1"
}
site production app.unboxlearning.in 8040 3010
site staging staging.unboxlearning.in 8041 3011
nginx -t && systemctl reload nginx
certbot --nginx --non-interactive --agree-tos -m "$EMAIL" --redirect -d app.unboxlearning.in -d staging.unboxlearning.in \
  || echo "!! certbot failed: check that both DNS names point here, then run: sudo certbot --nginx -d app.unboxlearning.in -d staging.unboxlearning.in"

echo "== 5/5 nightly backups"
install -m 755 "$APP_DIR/deploy/backup.sh" /usr/local/bin/unboxed-backup
echo "30 2 * * * root /usr/local/bin/unboxed-backup >> /var/log/unboxed-backup.log 2>&1" > /etc/cron.d/unboxed-backup

echo
echo "Done. Next: fill in SMTP (and Google) in /etc/unboxed/*.env, then from your laptop run deploy/deploy-app.sh."
