# Production Hardening Walkthrough (Query Clash)

I have performed a comprehensive "A to Z" audit and hardening of the **Query Clash** system to ensure it is ready for production hosting on AWS.

## Hardening Measures Implemented

### 1. Session & Cookie Security
- **HttpOnly**: Cookies are now inaccessible to client-side scripts, mitigating XSS risks.
- **Secure**: Cookies are only sent over HTTPS in production (controlled by `FLASK_ENV=production`).
- **SameSite=Lax**: Prevents CSRF attacks while maintaining user experience.
- **Session Timeout**: Sessions are limited to 1 hour of inactivity.

### 2. Application Integrity
- **Structured Logging**: All logs are now sent to `stdout` in a structured format, compatible with AWS CloudWatch.
- **Global Error Handlers**: 404 and 500 errors now return clean, user-friendly responses (JSON for API, HTML for UI) without leaking stack traces.
- **Security Headers**: Added `Content-Security-Policy`, `X-Frame-Options`, and `X-Content-Type-Options` to every response.

### 3. SQL & Data Security
- **Hardened Query Filtering**: Strengthened the read-only query enforcement with more robust regex and forbidden keyword checks.
- **Attempted Query Monitoring**: Forbidden commands are now logged with the user's name for audit purposes.

### 4. Container Security
- **Non-root User**: The application now runs as `appuser` inside the container, following the principle of least privilege.
- **Health Check**: Added a `/health` endpoint for infrastructure monitoring.

## Updated Deployment Guide

To deploy the hardened version:

1. **Set Environment Variables**:
   - `FLASK_ENV=production` (Enables secure cookies)
   - `SECRET_KEY=[random_long_string]`
   - `DB_PATH=database.db`
2. **Build and Run (Local Test)**:
   ```bash
   docker build -t query-clash-prod .
   docker run -p 8080:8080 -e FLASK_ENV=production query-clash-prod
   ```

## Final Verification
- ✅ **Local Run**: Application starts correctly and serves the UI.
- ✅ **Security Check**: `/health` returns 200 OK.
- ✅ **Error Handling**: Navigating to a non-existent route returns a clean 404.
- ✅ **SQL Enforcement**: Attempting an `UPDATE` query is blocked and logged.
