# Publishing Docker images to GHCR

This repo ships a GitHub Actions workflow (`.github/workflows/docker-publish.yml`) that automatically builds & publishes multi-arch container images to GitHub Container Registry.

## One-time setup

1. **Push this repo to GitHub** (public or private, either works).
2. **Enable Actions** — Settings → Actions → General → Allow all actions and reusable workflows.
3. **Grant workflow package permissions** — Settings → Actions → General → Workflow permissions → select **"Read and write permissions"**. (Or leave `GITHUB_TOKEN` scoped and rely on the `permissions: packages: write` block in the workflow file — that also works.)

That's it. No Docker Hub account, no separate registry credentials. `GITHUB_TOKEN` handles authentication automatically.

## What gets published

Every push to `main` and every `v*.*.*` tag triggers a build. The images end up at:

- `ghcr.io/<your-username>/narrative-rx-backend`
- `ghcr.io/<your-username>/narrative-rx-frontend`

Both images are **multi-arch** (linux/amd64 + linux/arm64) so they run on Intel/AMD servers, Apple Silicon Macs, and Raspberry Pi 4+.

## Tag scheme

| Trigger | Tags produced |
|---|---|
| Push to `main` | `latest`, `sha-<7char>` |
| Push tag `v1.2.3` | `1.2.3`, `1.2`, `1`, `sha-<7char>` |
| Manual dispatch | `sha-<7char>` |

## Consuming the images (self-host)

On any target machine:
```bash
git clone <this-repo>
cd narrative-rx
cp .env.example .env
# Fill in JWT_SECRET, EMERGENT_LLM_KEY, GHCR_OWNER, IMAGE_TAG

docker compose -f docker-compose.yml -f docker-compose.ghcr.yml pull
docker compose -f docker-compose.yml -f docker-compose.ghcr.yml up -d
```

## Cutting a release

```bash
git tag v1.0.0 -m "First public release"
git push origin v1.0.0
```

Actions will build & publish `1.0.0`, `1.0`, `1`, and update `latest`. About 4–6 minutes end-to-end (multi-arch adds ~2 min over single-arch).

## Making the images public

By default GHCR packages inherit the repo's visibility. If your repo is private but you want the images public:

1. GitHub profile → **Packages** → click each image (`narrative-rx-backend`, `narrative-rx-frontend`)
2. Package settings → **Change visibility** → **Public**

Once public, anyone can `docker pull ghcr.io/<owner>/narrative-rx-backend:latest` without authentication.

## Pulling private images

If you keep the images private:
```bash
# One-time on each host that pulls:
echo <YOUR_GITHUB_PAT> | docker login ghcr.io -u <your-username> --password-stdin
```

Create the PAT at https://github.com/settings/tokens (classic) with scope `read:packages`.

## Troubleshooting

**"denied: installation not allowed to Create organization package"** — the workflow needs `packages: write` permission. Re-check step 3 of the one-time setup above.

**"manifest unknown" when pulling** — the tag doesn't exist yet. Push to `main` at least once and let the workflow finish, then retry.

**Multi-arch build fails on `qemu`** — GitHub-hosted runners already have QEMU installed; the `docker/setup-qemu-action@v3` step just wires it up. If you self-host runners, `apt install qemu-user-static`.

**Image size larger than expected** — check `.dockerignore` in `backend/` and `frontend/` — those exclude `node_modules`, `venv`, `tests`, etc. The frontend image should end up ~50 MB (nginx + static build), backend ~250 MB (Python + reportlab + motor + emergentintegrations).
