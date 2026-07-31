# Production Deployment (free-tier VM)

This app deploys as the existing docker-compose stack (Postgres + backend + frontend) onto a
single VM you control, fronted by [Caddy](https://caddyserver.com/) for automatic HTTPS. This
keeps local file storage and the Chroma vector store working exactly as they do in development —
no re-architecture onto managed PaaS/object storage — which is what makes a **free, persistent**
VM the right fit here (most free serverless/PaaS tiers don't offer persistent local disks).

## 1. Get a free persistent VM

[Oracle Cloud's Always Free tier](https://www.oracle.com/cloud/free/) is the most generous
option that's free indefinitely (not a trial): an Ampere A1 (ARM) shape with up to 4 OCPU/24GB
RAM, or an x86 micro shape with 1GB RAM, plus up to 200GB block storage. Any Ubuntu 22.04+ VM
works equally well if you have one elsewhere.

- Provision the VM, note its public IP.
- Open inbound TCP 80 and 443 in the cloud provider's security list/firewall (Oracle Cloud:
  both the VCN's Security List **and** the instance's `iptables`/`ufw` need the ports open).
- Point a DNS `A` record for your domain at the VM's public IP.

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out/in after this
```

Confirm the Docker daemon starts on boot (default on most distros via systemd):
```bash
sudo systemctl is-enabled docker   # should print "enabled"
```
Combined with each service's `restart: unless-stopped` in `docker-compose.yml`, this means the
whole stack comes back up automatically after a VM reboot.

## 3. Clone and configure

```bash
git clone <your-repo-url>
cd "Reverse File Search"

cp .env.example .env
# edit .env: set POSTGRES_PASSWORD (openssl rand -base64 32) and DOMAIN

cp backend/.env.example backend/.env
# edit backend/.env — at minimum:
#   ENVIRONMENT=production
#   DEBUG=false
#   BACKEND_CORS_ORIGINS=["https://your-domain.com"]
#   FRONTEND_BASE_URL=https://your-domain.com
#   GROQ_API_KEY=... (optional, for AI features)
#   SMTP_* (for verification/password-reset emails)

mkdir -p backend/keys
docker compose -f docker-compose.yml -f docker-compose.prod.yml build backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm --no-deps \
  --entrypoint python backend scripts/generate_jwt_keys.py
```

`ENVIRONMENT=production` is what enables the refresh-token cookie's `Secure` flag and HSTS
(`backend/app/auth/middleware.py`) — without it, session cookies get sent over what should be an
HTTPS-only deployment. `backend/keys/` must persist across deploys (it's volume-mounted); losing
it invalidates every user's session.

## 4. Start the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This does **not** load `docker-compose.override.yml` (that only auto-applies to plain
`docker compose up`, used for local dev). In this configuration, only Caddy publishes ports
(80/443); Postgres, the backend, and the frontend are reachable solely over the internal Docker
network. Caddy requests and renews the Let's Encrypt certificate for `DOMAIN` automatically —
first request may take a few seconds while the certificate is issued.

Verify:
```bash
curl https://your-domain.com/api/v1/health
```

## 5. Migrations on future deploys

Already automatic: `backend/docker-entrypoint.sh` runs `alembic upgrade head` every time the
backend container starts, before uvicorn boots. Nothing extra to run manually.

## 6. Redeploying after changes

```bash
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker image prune -f
```

The `.github/workflows/deploy.yml` workflow automates exactly this over SSH, triggered manually
from the Actions tab (not on every push — deploying to prod is left as a deliberate action). To
use it, add these repository secrets: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DEPLOY_PATH`.

## 7. Backups

```bash
./scripts/backup.sh
```

Dumps Postgres, tars `backend/storage/` (Chroma vector store) and `backend/keys/` (JWT keypair)
into `backups/backup-<timestamp>.tar.gz`. Add a daily cron job:

```bash
crontab -e
# 0 3 * * * /full/path/to/reverse-file-search/scripts/backup.sh
```

This writes backups to the same VM's disk — copy them offsite periodically (e.g. `scp` to your
own machine) if you want protection against losing the VM itself; no cloud backup target is
wired up by default, to avoid reintroducing a paid dependency on a free-hosting setup.

## 8. Resource sizing note

Argon2id password hashing (`backend/app/auth/security.py`) uses 64MB of memory per concurrent
hash operation. On the smallest free VM shapes (~1GB RAM), a burst of concurrent logins alongside
Postgres, the backend, and the sentence-transformers embedding model in memory can add real
pressure — prefer the Ampere A1 shape (24GB RAM) if available, or watch memory usage
(`docker stats`) under load if stuck on a 1GB instance.

## 9. CI

`.github/workflows/ci.yml` runs backend tests (against a real Postgres service container) and
frontend lint/build on every push and pull request. `deploy.yml` is the separate, manual
promotion step described above.
