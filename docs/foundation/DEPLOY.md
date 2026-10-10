# Deploying UnboxEd

Three environments: **local** (your machine), **staging** (`staging.unboxlearning.in`) and **production**
(`app.unboxlearning.in`). The marketing site stays at `unboxlearning.in` (see `site/README.md`).
Never develop against production.

## One-time server setup (Ubuntu VPS, alongside the site's nginx)

```bash
sudo apt install -y postgresql nginx python3.12-venv nodejs certbot python3-certbot-nginx
sudo useradd --system --create-home unboxed
sudo -u postgres psql -c "CREATE ROLE unboxed LOGIN PASSWORD '<strong password>'" -c "CREATE DATABASE unboxed OWNER unboxed"
sudo mkdir -p /srv/unboxed/releases /etc/unboxed /var/lib/unboxed/storage && sudo chown -R unboxed /srv/unboxed /var/lib/unboxed
sudo -u unboxed python3.12 -m venv /srv/unboxed/venv
```

`/etc/unboxed/production.env` (mode 600, owned by root):

```
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg://unboxed:<strong password>@localhost:5432/unboxed
APP_URL=https://app.unboxlearning.in
SITE_URL=https://unboxlearning.in
SECRET_KEY=<48+ random characters>
COOKIE_DOMAIN=.unboxlearning.in
COOKIE_SECURE=true
REQUIRE_EMAIL_VERIFICATION=false
STORAGE_DIR=/var/lib/unboxed/storage
SMTP_HOST=… SMTP_USER=… SMTP_PASSWORD=… SMTP_FROM=UnboxEd <no-reply@unboxlearning.in>
```

The API refuses to start in staging/production if `SECRET_KEY` is weak, `COOKIE_SECURE` is off, or the database
still uses the development password.

Then install `deploy/systemd/*.service` into `/etc/systemd/system/`, `sudo systemctl enable unboxed-api
unboxed-worker unboxed-web`, and the nginx file `deploy/nginx-app.conf` (then `certbot --nginx -d app.unboxlearning.in`).

For **staging**, repeat with `/srv/unboxed-staging`, a separate `unboxed_staging` database,
`/etc/unboxed/staging.env` (with its own `SECRET_KEY`, `APP_URL=https://staging.unboxlearning.in`) and copies
of the service files named `unboxed-*-staging` on other ports (e.g. 8041/3011).

## Each release

```bash
SSH_TARGET=ubuntu@<server> TARGET=staging ./deploy/deploy-app.sh     # try it on staging first
SSH_TARGET=ubuntu@<server> ./deploy/deploy-app.sh                    # then production
cd site && SSH_TARGET=ubuntu@<server> ./deploy/deploy.sh             # site: forms point at app.unboxlearning.in
```

The release script runs the tests, builds the app, uploads a timestamped release, runs `alembic upgrade head`,
switches the `current` symlink and restarts the services. The last five releases are kept for rollback
(re-point `current` and restart).

## Checks after a release
- `https://app.unboxlearning.in/api/health` → `{"status":"ok", …}`, including counts of stuck and failed jobs.
- `journalctl -u unboxed-api -f` shows JSON lines with `request_id`, `user_id`, path, status and duration. The
  same `request_id` appears in any error a user sees ("Reference: …").
- Admin → Failed jobs should be empty.
