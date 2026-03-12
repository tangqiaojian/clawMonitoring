# One-Key Deploy and Start

## Windows one-click

1. Double click `onekey-deploy-start.bat`
2. Wait for build + dependency install + service startup
3. Open `http://127.0.0.1:5173`

Or run in PowerShell:

```powershell
.\scripts\onekey-deploy-start.ps1
```

## What the script does

- Build frontend (`npm run build`)
- Create backend virtual env (`backend/.venv`) if missing
- Install backend dependencies (`pip install -r requirements.txt`)
- Start backend (uvicorn, default port `8000`)
- Start frontend preview server (default port `5173`)
- Record process ids to `.runtime/backend.pid` and `.runtime/frontend.pid`

## Stop services

Double click `stop-services.bat`, or run:

```powershell
.\scripts\stop-services.ps1
```

## Optional ports

```powershell
.\scripts\onekey-deploy-start.ps1 -BackendPort 8001 -FrontendPort 5174
```
