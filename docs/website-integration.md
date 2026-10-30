# NIEL Industrial Intelligence AI - WordPress & Elementor Integration Guide

## 1. Executive Summary
This guide describes how to integrate the NIEL Industrial Intelligence Assistant into the official **New India Electricals Ltd. (NIEL)** website (`https://newindiaelectricals.com/`).

### Non-Negotiable Integration Rules:
- **Zero WordPress Database Schema Changes**: Does not alter MySQL tables or post metadata.
- **Zero Core or Theme File Modification**: Operates as a decoupled client communicating with the independent backend.
- **CSS Isolation via Shadow DOM**: Prevents conflicts with Elementor widgets, Bootstrap grids, or Tailwind utilities.
- **Zero Sensitive Secrets in WordPress**: All API keys remain isolated in the FastAPI backend environment.

---

## 2. Integration Architecture Options

### Option A: Embeddable Lightweight JavaScript Widget (Recommended)
The widget (`widget/niel-widget.js`) uses standard browser **Shadow DOM** (`host.attachShadow({ mode: 'open' })`). This guarantees that:
1. Styles from the WordPress theme cannot leak in and distort the chatbot UI.
2. Chatbot styles cannot leak out and break website layouts.

#### How to Add via Elementor Page Builder:
1. Open any page or the Global Site Footer in **Elementor**.
2. Drag and drop an **HTML Widget** into the bottom section of the footer template.
3. Paste the integration snippet from [`docs/website-integration-snippet.md`](website-integration-snippet.md).
4. Save / Update the template.

#### How to Add via WordPress Theme Customizer or Child Theme:
Add the snippet directly before the closing `</body>` tag in `footer.php` or using a trusted Header/Footer script manager plugin (e.g. *WPCode*).

---

### Option B: Secure Sandboxed iframe Integration
If NIEL hosting policy prohibits external JavaScript execution on the main domain, host the chatbot on a dedicated subdomain (e.g. `https://assistant.newindiaelectricals.com`):

```html
<iframe
  src="https://assistant.newindiaelectricals.com"
  title="NIEL Industrial Assistant"
  style="position: fixed; bottom: 20px; right: 20px; width: 400px; height: 600px; border: none; z-index: 999999;"
  sandbox="allow-scripts allow-same-origin allow-forms"
  loading="lazy">
</iframe>
```

---

## 3. Production Backend CORS Configuration
Before deploying to production, configure `ALLOWED_ORIGINS` in your backend `.env`:

```env
ALLOWED_ORIGINS=https://newindiaelectricals.com,https://www.newindiaelectricals.com
```

This ensures only requests originating from NIEL's verified domains can query `/api/v1/chat`.
