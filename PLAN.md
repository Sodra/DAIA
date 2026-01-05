# DAIA Rebuild Plan (Draft)

## Goals
- Rebuild LAALA as a clean Dockerized app inside `DAIA/` only.
- Use the UV Python package manager (`uv`) for dependency sync.
- Auto-update from GitHub every ~30 seconds, rebuilding/restarting on changes.
- Avoid GitHub Actions; updater must work via polling or webhooks on the host.

## High-Level Architecture
- **App container**: runs the Discord bot.
- **Updater container**: polls GitHub and triggers rebuild/restart on changes.
- **Shared repo volume**: updater pulls new code into a shared volume for rebuilds.
- **Docker Compose**: orchestrates app + updater, exposes required env/secrets.

## Update Strategy (Initial Choice)
- **Polling** every 30s via `git ls-remote` against `https://github.com/Sodra/DAIA.git`.
- When the remote HEAD changes:
  1) `git pull` into shared repo volume.
  2) `docker compose build daia`.
  3) `docker compose up -d --no-deps --force-recreate daia`.
- This avoids Docker-in-Docker inside the app container; updater alone needs Docker socket.

## Planned Project Structure
```
DAIA/
  src/                # bot runtime
  config/             # settings + templates
  scripts/            # helper + updater scripts
  docker/             # docker-specific files
  pyproject.toml      # uv-managed dependencies
  uv.lock
  docker-compose.yml
  Dockerfile
  README.md
```

## Phase 1: Scaffold
- Create minimal Python entrypoint in `src/`.
- Add `pyproject.toml` + `uv.lock` (convert deps from LAALA).
- Write Dockerfile that installs `uv` and runs the app.
- Add `docker-compose.yml` with app + updater.

## Phase 2: Port LAALA Features
- Settings manager (`settings.json`, `laala_prompt.txt` equivalent).
- Discord bot + OpenAI integration.
- Per-channel history storage.
- Token counting + image handling.

## Phase 3: Updater
- Implement a small bash/python updater in `scripts/`.
- Poll every 30s, compare remote hash vs local.
- Trigger rebuild/restart via docker socket (bind-mount `/var/run/docker.sock`).

## Phase 4: Docs + Validation
- Document local run, Docker run, and update behavior.
- Add `.env.example` with required keys (no secrets committed).
- Manual test: run bot in a Discord test channel.

## Open Questions
- Confirm whether polling interval should be configurable via env.
- Confirm desired default branch (`main`).
- Confirm if we should support webhook-triggered updates as a future option.
