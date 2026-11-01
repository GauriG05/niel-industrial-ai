# NIEL Industrial Intelligence AI - Application Security Policy

## 1. Secrets Management
- **Zero Secrets in Frontend**: The frontend build bundle (`frontend/dist/`) contains zero API keys or administrative secrets. All communication with AI providers occurs through the backend.
- **Git Shielding**: `.env`, `.env.*`, `data/docs/*`, and `data/index/*` are strictly blocked in `.gitignore`. Only `.env.example` with safe placeholder strings is checked in.

## 2. Administrative Authentication
- Privileged endpoints (`POST /api/v1/documents/upload` and `DELETE /api/v1/documents/{doc_id}`) require the `X-Admin-Key` HTTP header.
- Privileged Human Escalation management endpoints (`GET /api/v1/escalations`, `GET /api/v1/escalations/{session_id}/messages`, `POST /api/v1/escalations/{session_id}/reply`, and `POST /api/v1/escalations/{session_id}/resolve`) share this exact administrative trust boundary and strictly require the `X-Admin-Key` header.
- Unauthorized requests fail immediately with `401 Unauthorized` or `403 Forbidden`.

## 3. Protective HTTP Security Headers
Every HTTP response is guarded by the `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff` (Defends against MIME confusion attacks)
- `X-Frame-Options: SAMEORIGIN` (Defends against unauthorized framing & clickjacking)
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

## 4. Input Bounding & DoS Prevention
- User questions are capped at 500 characters.
- In-memory rate limiting enforces 30 requests per minute per client IP.
- Emergency Kill Switch (`KILL_SWITCH_ENABLED=true`) can pause LLM requests immediately without taking down the server.

