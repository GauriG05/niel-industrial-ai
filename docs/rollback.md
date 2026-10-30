# NIEL Industrial Intelligence AI - Rollback & Deactivation Plan

## 1. Instant 1-Step Website Deactivation (Zero Downtime)
If the AI Assistant needs to be removed from the live WordPress website:

### Option A (Elementor HTML Widget):
1. Navigate to **Elementor > Theme Builder > Footer** (or the page where the widget was inserted).
2. Right-click the **HTML Widget** containing the NIEL AI script and select **Delete**.
3. Click **Update** to publish the change immediately.

### Option B (Header/Footer Scripts Plugin or Child Theme):
1. Delete or comment out the `<script>` tag referencing `niel-widget.js`.
2. Clear the WordPress cache and Cloudflare edge cache.
3. The floating chatbot will disappear instantly for all visitors.

---

## 2. Emergency Backend Kill Switch (Without Redeployment)
If malicious activity, quota exhaustion, or an unexpected spike in queries is detected on the backend:

1. Update `.env` on the backend server:
   ```env
   KILL_SWITCH_ENABLED=true
   ```
2. Reload FastAPI (`systemctl reload niel-backend` or restart uvicorn).
3. The server remains online, but all new LLM queries are immediately blocked with a polite maintenance notice:
   *"The AI Assistant is temporarily paused by system administration. Please try again later."*
4. Zero additional tokens will be consumed on your OpenAI account.

