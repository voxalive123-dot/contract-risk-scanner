# Phase 8 Deployment Runbook

## Purpose
This runbook prepares VoxaRisk for safe live deployment behind `voxarisk.com` without expanding product scope. It covers production architecture, environment handling, build validation, HTTPS/reverse proxy notes, rollout steps, and smoke tests.

## Production Architecture Summary
- Frontend: Next.js app in `voxa-frontend`
- Backend: FastAPI app exposed from `main.py` via `api.py`
- Browser traffic: `https://voxarisk.com`
- Frontend server runtime: handles browser requests and forwards analysis requests through `voxa-frontend/app/api/analyze/route.ts`
- Backend runtime: private HTTP service reachable by the frontend server and reverse proxy
- TLS/HTTPS: terminate at a reverse proxy such as Nginx, Caddy, or Traefik
- Database: `DATABASE_URL`-driven SQLAlchemy backend
- Redis: optional/supporting runtime via `REDIS_URL`

Recommended deployment shape:
1. Reverse proxy receives `https://voxarisk.com`
2. Reverse proxy serves the Next.js app on port `3000`
3. Next.js server-side route forwards to the FastAPI app on port `8000`
4. Database and Redis remain private to the server/network

## Environment Variables

### Backend
Use a real `.env` on the server. Do not commit it.

Required:
- `DATABASE_URL`
- `TEST_API_KEY`

Supported runtime flags:
- `API_KEY_HASHES`
- `ENABLE_DOCS`
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_CAPACITY`
- `RATE_LIMIT_REFILL_PER_SEC`
- `REDIS_URL`

Suggested production defaults:
- `ENABLE_DOCS=0`
- `RATE_LIMIT_ENABLED=1`

Notes:
- `TEST_API_KEY` is currently used by `seed_api_key.py` and tests. Treat it as a secret.
- `API_KEY_HASHES` can be used for hash-driven auth scenarios if your deployment chooses that path.

### Frontend
Use a real `voxa-frontend/.env.local` or platform secret store. Do not commit it.

Required:
- `VOXA_API_BASE_URL`
- `VOXA_API_KEY`

Important:
- `VOXA_API_KEY` is used only in the server-side Next.js route and must never be exposed with `NEXT_PUBLIC_`.
- Do not create any `NEXT_PUBLIC_` secret values for the backend API key.

## Secret Handling Rules
- Never commit `.env`, `.env.local`, API keys, database passwords, or live domains with secrets embedded.
- Keep `VOXA_API_KEY` server-side only.
- Use secret managers or deployment platform environment settings where possible.
- Restrict database and Redis access to private interfaces/security groups only.
- Rotate the API key after deployment if any test or temporary key has been used during validation.

## Local Production Validation Commands

### Backend tests
From repo root:

```bash
source .venv/bin/activate
set -a
source .env
set +a
pytest -q
```

### Backend import smoke test
From repo root:

```bash
source .venv/bin/activate
set -a
source .env
set +a
python -c "from main import app; print(app.title)"
```

Expected output includes:

```text
VoxaRisk_INTELLIGENCE
```

### Frontend lint

```bash
cd voxa-frontend
npm run lint
```

### Frontend production build

```bash
cd voxa-frontend
npm run build
```

### Frontend production start

```bash
cd voxa-frontend
npm run start
```

Default port:
- `3000`

## Backend Start Command
Use a production-oriented Uvicorn command instead of the local reload script.

```bash
source .venv/bin/activate
set -a
source .env
set +a
python init_db.py
python seed_api_key.py
uvicorn main:app --host 127.0.0.1 --port 8000
```

For systemd/process manager usage, the command should stay non-reload and bind to localhost or a private interface.

## Frontend Production Build and Start

```bash
cd voxa-frontend
cp .env.example .env.local  # replace placeholders with real values
npm run build
npm run start
```

Recommended bind strategy:
- Keep Next.js behind the reverse proxy
- Bind on `127.0.0.1:3000` if your process manager supports it

## Docker Deployment Option
No current Dockerfile or compose file exists in this repository.

Recommendation:
- Do not add speculative Docker runtime files unless the deployment target requires them.
- Use the run commands in this runbook first.
- If containerization becomes mandatory later, add:
  - one backend Dockerfile
  - one frontend Dockerfile
  - one production compose file
  only after the hosting target is confirmed.

## Reverse Proxy and HTTPS Notes for `voxarisk.com`
Use Nginx, Caddy, or Traefik to terminate HTTPS and route traffic.

Recommended proxy behavior:
- `https://voxarisk.com` -> Next.js at `127.0.0.1:3000`
- Optional direct backend health path -> FastAPI at `127.0.0.1:8000`
- Forward:
  - `Host`
  - `X-Forwarded-Proto`
  - `X-Forwarded-For`
  - `X-Request-ID` if you want upstream request continuity

Important FastAPI note:
- Current CORS config allows `http://localhost:3000` only.
- Because browser traffic should hit the Next.js site and the frontend calls the backend through the Next.js server route, this is acceptable for now.
- If you later expose backend routes directly to the browser from `voxarisk.com`, CORS will need to be updated intentionally.

## DNS Checklist
- Point `A` record for `voxarisk.com` to the deployment server IP
- Point `A` record for `www.voxarisk.com` if required
- Decide whether `www` redirects to apex or vice versa
- Verify DNS propagation before TLS issuance

## Health-Check Checklist

### Backend
- `GET /` returns JSON health payload
- database migrations run successfully
- seeded API key exists
- analysis endpoints respond with valid authentication

### Frontend
- landing page loads
- pricing page loads
- dashboard loads
- server-side analyze route can reach backend

## Post-Deployment Smoke Test Checklist
After deployment to `voxarisk.com`:

1. Open `/`
2. Open `/pricing`
3. Open `/dashboard`
4. Paste a known risk-heavy contract into the dashboard
5. Confirm analysis completes
6. Confirm report/export still appears after a result
7. Confirm browser console shows no secret leakage
8. Confirm network requests do not expose `VOXA_API_KEY`
9. Confirm HTTPS certificate is valid
10. Confirm primary navigation works across public pages

Suggested sample contract:

```text
This agreement is governed by the laws of California. The supplier may suspend services at any time without liability. The supplier may increase prices on 30 days notice. The customer shall indemnify and hold harmless the supplier from all claims, losses, damages, and expenses arising out of this agreement. Either party may terminate this agreement for convenience without cause.
```

## Rollback / Restart Checklist
- Keep the previous frontend build artifact or release reference available
- Keep the previous backend virtualenv/image/reference available
- Restart backend process
- Restart frontend process
- Reload reverse proxy
- Re-run the smoke test checklist
- If deployment health fails, revert DNS/proxy routing to the previous known-good release

## Exact Local Commands for a Human Operator

### Backend

```bash
cd ~/voxa/PC_MIGRATION_OLD_TO_NEW/01_VOXARISK_INTELLIGENCE/Contract_Risk_Scanner_FULL/'Contract Risk Scanner'/contract_scanner
source .venv/bin/activate
set -a
source .env
set +a
python init_db.py
python seed_api_key.py
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd ~/voxa/PC_MIGRATION_OLD_TO_NEW/01_VOXARISK_INTELLIGENCE/Contract_Risk_Scanner_FULL/'Contract Risk Scanner'/contract_scanner/voxa-frontend
npm run build
VOXA_API_BASE_URL=http://127.0.0.1:8000 VOXA_API_KEY=CHANGE_ME npm run start
```

## Current Deployment Blockers / Follow-ups
- Real production secrets still need to be created and stored outside git
- Reverse proxy configuration for `voxarisk.com` still needs to be written on the target host
- No Docker deployment files currently exist; deployment is documented as process-manager/reverse-proxy based
- Consider replacing the development SQLite path with a production PostgreSQL database before live deployment
