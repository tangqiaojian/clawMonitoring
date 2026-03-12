# Backend

## Start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## APIs

- `GET /api/health`
- `GET /api/nodes`
- `POST /api/nodes`
- `DELETE /api/nodes/{id}`
- `GET /api/history/{metric}`
- `WS /ws`
