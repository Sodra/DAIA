# DAIA

```
__/\\\\\\\\\\\\________/\\\\\\\\\_____/\\\\\\\\\\\_____/\\\\\\\\\____        
 _\/\\\////////\\\____/\\\\\\\\\\\\\__\/////\\\///____/\\\\\\\\\\\\\__       
  _\/\\\______\//\\\__/\\\/////////\\\_____\/\\\______/\\\/////////\\\_      
   _\/\\\_______\/\\\_\/\\\_______\/\\\_____\/\\\_____\/\\\_______\/\\\_     
    _\/\\\_______\/\\\_\/\\\\\\\\\\\\\\\_____\/\\\_____\/\\\\\\\\\\\\\\\_    
     _\/\\\_______\/\\\_\/\\\/////////\\\_____\/\\\_____\/\\\/////////\\\_   
      _\/\\\_______/\\\__\/\\\_______\/\\\_____\/\\\_____\/\\\_______\/\\\_  
       _\/\\\\\\\\\\\\/___\/\\\_______\/\\\__/\\\\\\\\\\\_\/\\\_______\/\\\_ 
        _\////////////_____\///________\///__\///////////__\///________\///__
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
