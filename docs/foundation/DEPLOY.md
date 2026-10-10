# Deploying UnboxEd to the VPS

| Environment | Address | What it's for |
|---|---|---|
| local | http://localhost:3010 | coding, tests (`docker compose up --build` or the three dev commands in README) |
| **staging** | https://staging.unboxlearning.in | try every change here first; its own database and files |
| **production** | https://app.unboxlearning.in | real users |
| site | https://unboxlearning.in | marketing site; its sign-up/log-in forms talk to production |

Both app environments run on the same VPS as Docker Compose stacks (`unboxed-staging`, `unboxed-production`). Each
has its own Postgres, file volume and secrets. The host's nginx terminates HTTPS and forwards to them:
`/api/*` to the API, everything else to the web app.

## Step 1: DNS (at your domain registrar)

Add these records for `unboxlearning.in`. "Name" is sometimes called "Host".

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `app` | your VPS's IPv4 address | 3600 (or the default) |
| A | `staging` | your VPS's IPv4 address | 3600 |
| AAAA | `app`, `staging` | the VPS's IPv6 address *(only if it has one)* | 3600 |

Check them from your laptop: `nslookup app.unboxlearning.in` should return the VPS address. This can take from a
few minutes to a couple of hours. Add the email provider's records at the same time (see EMAIL_AND_GOOGLE.md).

## Step 2: one-time server setup

Requirements: Ubuntu 22.04/24.04 (or Debian 12) with **at least 2 GB RAM** (4 GB is comfortable for both
environments and image builds), and an SSH user with sudo.

```bash
ssh <user>@<vps-ip>
curl -fsSL https://raw.githubusercontent.com/preeti-mlverse/unboxlearning/main/deploy/server-setup.sh -o setup.sh
sudo bash setup.sh <your-email-for-certificate-notices>
```

This installs Docker, nginx and certbot, clones the repo to `/srv/unboxed`, writes `/etc/unboxed/staging.env` and
`/etc/unboxed/production.env` with fresh random secrets, sets up both nginx sites with HTTPS, and schedules nightly
database backups to `/var/backups/unboxed` (14 days kept).

Then fill in email (and optionally Google) in both env files, as described in EMAIL_AND_GOOGLE.md.

If unboxlearning.in (the site) isn't on this server yet, `site/deploy/server-setup.sh` prepares it. Then deploy
the site with `site/deploy/deploy.sh`.

## Step 3: each release (from your laptop)

```bash
git push                                                               # the server deploys what's on GitHub
SSH_TARGET=<user>@<vps-ip> ./deploy/deploy-app.sh                      # staging (default)
SSH_TARGET=<user>@<vps-ip> TARGET=production ./deploy/deploy-app.sh    # production (runs the tests first)
cd site && SSH_TARGET=<user>@<vps-ip> ./deploy/deploy.sh               # the marketing site, if it changed
```

The server checks out that exact commit and rebuilds the images. The API applies any new database migrations
before it starts. The script then waits for `https://<host>/api/health`.

**Roll back:** `REF=<older commit sha> SSH_TARGET=… TARGET=production ./deploy/deploy-app.sh`. Migrations only
move forward, so to undo a schema change, write a new migration.

## Looking after it

```bash
cd /srv/unboxed
C="sudo docker compose -p unboxed-production -f docker-compose.prod.yml --env-file /etc/unboxed/production.env"
$C ps                       # are the four services up?
$C logs -f api              # JSON lines: request_id, user_id, path, status, duration
$C logs -f worker           # background jobs
$C exec db psql -U unboxed  # the database
sudo unboxed-backup         # take a backup now
```

- Health: `https://app.unboxlearning.in/api/health` (database, stuck jobs, failed jobs in the last 24h).
- Admin → the counters (server errors, uploads refused or failed) and the **Errors & uploads** tab. Each row's
  reference matches `request_id` in the API logs.
- Make the first platform admin, after signing up normally:
  `$C exec db psql -U unboxed -c "update users set is_platform_admin = true where email = 'you@example.com'"`
