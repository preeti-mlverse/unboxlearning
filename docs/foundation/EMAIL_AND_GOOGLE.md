# Email and Google sign-in setup

Both are switched on only by settings in `/etc/unboxed/staging.env` and `/etc/unboxed/production.env` on the
server (and `.env` on your laptop). **Put secrets only in those files. Don't paste them into chat, email or git.**
After editing a file, redeploy that environment (`deploy/deploy-app.sh`) so the containers pick up the change.

---

## 1. Email (confirmation codes, password resets)

### Which provider to start with

| Provider | Free / entry tier | Good for | Watch out for |
|---|---|---|---|
| **Resend** (recommended to start) | 3,000 emails/month, 100/day free | Simplest setup, very good deliverability, plain SMTP | 100/day cap on free; sending only (no inbox) |
| Brevo | 300/day free | Higher free daily volume | Busier dashboard; marketing upsells |
| Zoho ZeptoMail | Pay as you go, low cost per 10,000 | India-based billing, transactional only | Small up-front credit purchase |
| Amazon SES | About $0.10 per 1,000 | Cheapest at scale | AWS account, and you must apply to leave "sandbox" mode |

**Recommendation:** start with **Resend**. A pilot will send far fewer than 100 emails a day (sign-up codes and
resets only). Switching later is just a change of the five `SMTP_*` settings; nothing in the code changes. Move to
ZeptoMail or SES when you outgrow the free tier.

None of these gives you an inbox. To *receive* email at `hello@unboxlearning.in`, use Zoho Mail (free plan) or
Google Workspace. That's separate and optional.

### Setting up Resend (about 15 minutes)

1. Create an account at resend.com with the email you want as the owner.
2. **Domains → Add domain** → `unboxlearning.in`. Choose a region close to your users (Mumbai/ap-south-1 if offered).
3. Resend shows 3–4 DNS records (an SPF `TXT`, a DKIM `TXT`, and an `MX` for bounce handling, usually on a
   `send.` subdomain). Add each one exactly as shown at your domain registrar, in the same place you add the
   `app`/`staging` A records.
4. Also add this DMARC record. It tells inboxes your mail is protected, which keeps you out of spam:
   - Type `TXT`, Name `_dmarc`, Value `v=DMARC1; p=none; rua=mailto:<your email>`
5. Back in Resend, click **Verify**. It can take a few minutes to an hour for DNS to update.
6. **API Keys → Create API key** with "Sending access" only, for the domain `unboxlearning.in`. Copy it.
7. On the server, edit both env files (`sudo nano /etc/unboxed/staging.env`, then `production.env`):
   ```
   SMTP_HOST=smtp.resend.com
   SMTP_PORT=587
   SMTP_USER=resend
   SMTP_PASSWORD=<the API key from step 6>
   SMTP_FROM=UnboxEd <no-reply@unboxlearning.in>
   ```
8. Redeploy staging, sign up with your own email and check that the 6-digit code arrives (and not in spam).

Until SMTP is filled in, emails aren't lost. They're written into the `storage` volume under `outbox/`, and you can
read them on the server:

```
sudo docker compose -p unboxed-staging -f /srv/unboxed/docker-compose.prod.yml --env-file /etc/unboxed/staging.env exec api sh -c 'ls -t /data/storage/outbox | head -3'
```

---

## 2. Sign in with Google

The code is already built and tested. The "Continue with Google" button appears on the app's and site's log-in and
sign-up pages as soon as the two settings below are filled in.

### Create the credentials (Google Cloud Console, about 20 minutes)

1. Go to **console.cloud.google.com**, signed in with the Google account that should own this (ideally a shared
   company account, not a personal one).
2. Top bar → project picker → **New project** → name it `UnboxEd` → Create, then select it.
3. Left menu → **APIs & Services → OAuth consent screen** (newer consoles call it **Google Auth Platform**) → Get started:
   - **App name:** `UnboxEd`. **User support email:** your email.
   - **Audience:** **External**.
   - **Contact email:** your email → Create.
4. **Branding** (same section):
   - Upload the logo `site/src/assets/icon-512.png`.
   - App home page `https://unboxlearning.in`, privacy policy `https://unboxlearning.in/privacy/`, terms `https://unboxlearning.in/terms/`.
   - **Authorised domains:** `unboxlearning.in`. Save.
5. **Data access → Add or remove scopes:** tick `openid`, `.../auth/userinfo.email` and `.../auth/userinfo.profile`.
   These are "non-sensitive", so Google doesn't need to review the app. Save.
6. **Audience → Publish app** (moves it from "Testing" to "In production"). While it's in Testing, only the test
   users you list can sign in.
7. **Clients → Create client:**
   - **Application type:** Web application. **Name:** `UnboxEd web`.
   - **Authorised JavaScript origins:**
     `https://app.unboxlearning.in`, `https://staging.unboxlearning.in`, `http://localhost:3010`
   - **Authorised redirect URIs** (these must match exactly):
     ```
     https://app.unboxlearning.in/api/auth/google/callback
     https://staging.unboxlearning.in/api/auth/google/callback
     http://localhost:3010/api/auth/google/callback
     ```
   - Create. Google shows a **Client ID** (ends in `.apps.googleusercontent.com`) and a **Client secret**.
8. Put them in both server env files (and your laptop's `.env` to try it locally):
   ```
   GOOGLE_CLIENT_ID=<client id>
   GOOGLE_CLIENT_SECRET=<client secret>
   ```
9. Redeploy. The Google button appears, and `https://staging.unboxlearning.in/api/auth/providers` returns `{"google":true}`.

You can share the **Client ID** with me (it isn't secret) so I can check the setup. Keep the **secret** only in
the env files.

### How it behaves
- A new Google user gets an account just like the sign-up form. Choosing "Educator" first also creates their
  workspace. Their email counts as confirmed, so no code is needed.
- If the Google email matches an existing account, the Google login is linked to that account.
- People who signed up with Google and later want a password use "Forgot password".
