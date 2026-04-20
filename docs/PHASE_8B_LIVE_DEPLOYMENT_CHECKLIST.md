# Phase 8B Live Deployment Checklist

## Scope
This checklist turns the existing VoxaRisk deployment documentation into an execution-ready live deployment path for `voxarisk.com` without adding product scope or committing secrets.

This document is intentionally split into:
- deployment checklist complete
- live execution pending until real host/domain/runtime details are supplied and verified

## Current Assumptions and Missing Deployment Details
At the time of writing, the following live deployment details are not confirmed in the repository or current context:

- production host provider is not yet confirmed
- server IP is not yet confirmed
- DNS access is not yet confirmed
- TLS/reverse proxy path is not yet executed
- target Linux distribution and process manager are not yet confirmed
- live production URL has not yet been validated over HTTPS

Until those details exist, this phase can prepare the checklist and example configs, but it must not claim live deployment completion.

## Recommended Production Shape
- public domain: `voxarisk.com`
- reverse proxy: Nginx or Caddy terminating HTTPS
- frontend: Next.js production server on `127.0.0.1:3000`
- backend: FastAPI/Uvicorn on `127.0.0.1:8000`
- database: production `DATABASE_URL`, ideally PostgreSQL
- redis: optional/supporting runtime via `REDIS_URL`
- browser traffic should hit the frontend only
- frontend server route should forward analysis requests to backend using server-side env values

## Required Host / Server Prerequisites
- Ubuntu or comparable Linux host with sudo access
- Git installed
- Python version compatible with the existing virtual environment and requirements
- Node.js and npm installed for the frontend build/runtime
- reverse proxy package installed:
  - Nginx, or
  - Caddy
- open ports:
  - `80/tcp`
  - `443/tcp`
- outbound access for package installation and TLS issuance
- access to create secure runtime env files outside git

## Human-Provided Information Still Required
- hosting provider name
- server public IP
- SSH access method
- chosen Linux username for deployment
- final deployment path on server, for example `/srv/voxarisk/contract_scanner`
- DNS control for `voxarisk.com`
- whether `www.voxarisk.com` will be used or redirected
- production database connection details
- production API key generation/rotation plan
- whether Redis will be enabled in production
- chosen process manager:
  - systemd recommended
  - pm2 only if explicitly preferred

## Required DNS Records for `voxarisk.com`
- `A` record:
  - host: `@`
  - value: `<SERVER_PUBLIC_IP>`
- optional `A` record:
  - host: `www`
  - value: `<SERVER_PUBLIC_IP>`
- choose redirect policy:
  - `www` -> apex, or
  - apex -> `www`
- wait for propagation before requesting TLS certificates

## Production Environment Variables

### Backend
Create a real server-side `.env` or equivalent secret file outside git.

Required:
- `DATABASE_URL`
- `TEST_API_KEY`

Supported:
- `API_KEY_HASHES`
- `ENABLE_DOCS`
- `RATE_LIMIT_ENABLED`
- `RATE_LIMIT_CAPACITY`
- `RATE_LIMIT_REFILL_PER_SEC`
- `REDIS_URL`

Recommended production values:
- `ENABLE_DOCS=0`
- `RATE_LIMIT_ENABLED=1`
- `RATE_LIMIT_CAPACITY=60`
- `RATE_LIMIT_REFILL_PER_SEC=1.0`

### Frontend
Create a real server-side `voxa-frontend/.env.local` or platform secret file outside git.

Required:
- `VOXA_API_BASE_URL=http://127.0.0.1:8000`
- `VOXA_API_KEY=<REAL_BACKEND_API_KEY>`

Critical rule:
- `VOXA_API_KEY` must remain server-side only
- never expose it with `NEXT_PUBLIC_`

## Backend Deployment Steps
1. Clone or copy the repo to the target server
2. Create and activate the Python virtual environment
3. Install requirements:
   - `pip install -r requirements.txt`
4. Create the real backend `.env`
5. Load env values
6. Initialize schema:
   - `python init_db.py`
7. Seed the backend API key if your auth flow still depends on that script:
   - `python seed_api_key.py`
8. Start the backend on localhost only:
   - `uvicorn main:app --host 127.0.0.1 --port 8000`
9. Confirm backend root health returns JSON before exposing the frontend publicly

## Frontend Deployment Steps
1. Install Node dependencies in `voxa-frontend`
2. Create the real `voxa-frontend/.env.local`
3. Build the frontend:
   - `npm run build`
4. Start the frontend:
   - `npm run start`
5. Keep it bound behind the reverse proxy, ideally on `127.0.0.1:3000`
6. Confirm:
   - `/`
   - `/pricing`
   - `/dashboard`
   all load locally on the server before enabling public traffic

## Reverse Proxy / HTTPS Setup Checklist
- choose Nginx or Caddy
- point `voxarisk.com` DNS to the server IP
- configure HTTP -> HTTPS redirect
- proxy requests for `/` to `127.0.0.1:3000`
- forward headers:
  - `Host`
  - `X-Forwarded-Proto`
  - `X-Forwarded-For`
- enable certificate issuance and renewal
- verify certificate is valid before external review access

Important current application note:
- backend CORS is currently narrow and assumes browser traffic goes through the Next.js server route
- do not expose browser clients directly to backend API routes unless CORS is intentionally revisited

## Process Manager Approach
Recommended:
- `systemd` for backend
- `systemd` for frontend
- Nginx for reverse proxy

Why:
- simple Ubuntu fit
- good restart behavior
- clean separation between services and proxy
- easier logging and restart operations than adding speculative container tooling

## Firewall / Security Checklist
- allow inbound `80/tcp` and `443/tcp`
- keep `3000` and `8000` bound to localhost only where possible
- do not expose database or Redis publicly
- keep `.env` and `.env.local` readable only by the deployment user or root
- rotate any temporary or test API key before external reviewer access
- keep FastAPI docs disabled in production unless intentionally required

## Smoke Test Checklist
After services and HTTPS are live:

1. Open `https://voxarisk.com/`
2. Open `https://voxarisk.com/pricing`
3. Open `https://voxarisk.com/dashboard`
4. Confirm certificate is valid
5. Confirm homepage loads without broken public navigation
6. Paste the known sample contract into the dashboard
7. Confirm analysis completes successfully
8. Confirm findings, priorities, and report/export appear
9. Confirm no browser-visible API key appears in source or network requests
10. Confirm decision-boundary wording remains visible

Suggested sample contract:

```text
This agreement is governed by the laws of California. The supplier may suspend services at any time without liability. The supplier may increase prices on 30 days notice. The customer shall indemnify and hold harmless the supplier from all claims, losses, damages, and expenses arising out of this agreement. Either party may terminate this agreement for convenience without cause.
```

## Rollback Checklist
- keep the previous frontend build available
- keep the previous backend virtualenv/release available
- stop frontend and backend services
- restore previous release or artifact
- restart backend service
- restart frontend service
- reload reverse proxy
- rerun the smoke test checklist

## Do Not Proceed Conditions
- no server IP is available
- DNS access is unavailable
- no secure place exists for production env files
- HTTPS cannot be issued or renewed safely
- backend tests or frontend build fail
- real secrets would need to be committed to proceed
- operator cannot confirm restart/rollback path
- live domain resolves to the wrong host

## Exact Server-Side Next Commands Once Host Details Exist

### Backend
```bash
cd <DEPLOY_PATH>/contract_scanner
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# replace placeholders in .env with real production values
set -a
source .env
set +a
python init_db.py
python seed_api_key.py
uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd <DEPLOY_PATH>/contract_scanner/voxa-frontend
npm install
cp .env.example .env.local
# replace placeholders in .env.local with real production values
npm run build
npm run start
```

## Phase 8B Completion Rule
- checklist/documentation complete: yes, once this document is reviewed
- live execution complete: only after `voxarisk.com` is live over HTTPS and the smoke test passes

Current state:
- Phase 8B is deployment checklist complete, live execution pending
