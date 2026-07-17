# Narrative.Rx — Docker install guide

Bring the whole app up on any machine (Mac, Linux, Windows) with **one command**.

---

## Prerequisites

- **Docker Desktop** — download from https://www.docker.com/products/docker-desktop
  (includes Docker + Docker Compose v2)
- **Emergent Universal LLM Key** — grab yours from https://app.emergent.sh → Profile → Universal Key.
  Keep it handy; you'll paste it into `.env`.

That's it. No Python, no Node, no MongoDB install required.

---

## First-time setup

```bash
# 1. Clone the repo
git clone <your-github-url> narrative-rx
cd narrative-rx

# 2. Create your local .env from the template
cp .env.example .env

# 3. Edit .env — set these two values at minimum
#    JWT_SECRET=<paste a 32-char random hex>
#    EMERGENT_LLM_KEY=sk-emergent-<your key>
#
# Generate a JWT secret with:
python3 -c "import secrets; print(secrets.token_hex(32))"
# (or on Windows PowerShell)
[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Max 256 }))

# 4. Build & start everything
docker compose up -d --build
```

The first build downloads Python, Node and Mongo images and takes ~3–5 minutes. Subsequent starts are ~5 seconds.

## Open the app

http://localhost:8080

**Demo account (change on production!):**
- Email: `admin@dental.com`
- Password: `admin123`

## Everyday commands

```bash
# See the logs
docker compose logs -f

# Stop everything
docker compose down

# Update to a new version of the code
git pull
docker compose up -d --build

# Wipe all data (⚠ destroys saved narratives)
docker compose down -v
```

## Backup your narratives

The MongoDB data lives in a docker volume called `narrative-rx_mongo-data`. To back it up:

```bash
docker exec narrative-rx-mongo mongodump \
    --archive --gzip --db narrative_rx > backup-$(date +%F).gz
```

Restore with:

```bash
docker exec -i narrative-rx-mongo mongorestore \
    --archive --gzip --db narrative_rx < backup-2026-02-14.gz
```

## Change the port

If port 8080 is taken, edit `.env`:

```
WEB_PORT=9000
CORS_ORIGINS=http://localhost:9000
```

Then `docker compose up -d`. Open http://localhost:9000.

## Deploy to a small server / VPS

The same `docker compose up -d` works on any Linux VPS (DigitalOcean, Hetzner, EC2, etc.). Put nginx or Caddy in front for HTTPS:

```
example.com  → Caddy (HTTPS) → :8080 (frontend container) → /api → backend container
```

Set `CORS_ORIGINS=https://your-domain.com` in `.env`.

## Troubleshooting

**"docker: command not found"** — install Docker Desktop and reopen your terminal.

**Backend won't start / "MONGO_URL not set"** — you didn't create `.env`. Copy from `.env.example`.

**LLM error: 401 / invalid key** — your `EMERGENT_LLM_KEY` is wrong or exhausted. Regenerate at Emergent → Profile → Universal Key and top up balance if needed.

**"Port 8080 already in use"** — change `WEB_PORT` in `.env` (see above).

**"Failed to connect to mongo"** — bring the stack down and up: `docker compose down && docker compose up -d`. Wait for the `mongo` service to report healthy in `docker compose ps`.

**Everything looks fine but login redirects to /login** — clear browser cookies for localhost and try again. If you upgraded from a dev version, old cookies with the wrong secure flag can linger.
