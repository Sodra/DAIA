# DAIA

```
    ____  ___    ____    _    _
   / __ \/   |  /  _/   / \  (_)
  / / / / /| |  / /    / _ \ / / 
 / /_/ / ___ |_/ /    / ___ / /  
/_____/_/  |_/___/   /_/  |_/_/   
```

Discord AI Assistant — a rebuild of LAALA with a clean, container-first setup.

## Goals
- Run as a Dockerized service
- Use `uv` for Python dependency management
- Auto-update from GitHub (poll + rebuild)

## Status
- Initial planning in `PLAN.md`
- Implementation coming next

## Quick Notes
- Secrets (API keys, tokens) must never be committed
- Docker + updater design will be documented here as it lands
