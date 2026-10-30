# NIEL Industrial Intelligence AI - Production Deployment Guide

## 1. Local Testing Before Deployment
Ensure that all unit and RAG tests pass:
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
.\.venv\Scripts\python.exe evaluation/evaluate.py
```

## 2. Production Environment Configuration
On your production Linux or cloud server:

1. Clone repository:
   ```bash
   git clone <repo-url> niel-ai
   cd niel-ai
   ```

2. Setup virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r backend/requirements.txt
   ```

3. Create production `.env`:
   ```bash
   cp .env.example .env
   ```
   Configure:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - `OPENAI_API_KEY=sk-prod-...`
   - `ADMIN_API_KEY=<generate-strong-random-token>`
   - `ALLOWED_ORIGINS=https://newindiaelectricals.com,https://www.newindiaelectricals.com`
   - `RATE_LIMIT_PER_MINUTE=20`

4. Run with Gunicorn/Uvicorn under Systemd:
   ```bash
   uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
   ```

## 3. Frontend Static Hosting
Build the optimized static bundle:
```bash
cd frontend
npm install
npm run build
```
Deploy the generated `frontend/dist/` contents to an Nginx webroot or Cloudflare Pages.

