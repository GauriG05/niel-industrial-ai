# NIEL Industrial Intelligence AI - Setup & Execution Guide

## Overview
This document describes how to configure and execute the NIEL Industrial Intelligence Assistant locally in a secure, self-contained environment.

## 1. Prerequisites
- Python 3.11+ (Python 3.13 verified)
- Node.js 18+ and npm
- Git
- OpenAI API key (for embedding and question answering; not needed for health checks)

## 2. Backend Local Setup

1. **Create and activate a virtual environment**:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install backend dependencies**:
   ```powershell
   pip install -r backend/requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
   Edit `.env` to include your:
   - `OPENAI_API_KEY`: Your OpenAI key (kept strictly backend-only)
   - `ADMIN_API_KEY`: Secret string required for authorized document upload/deletion

4. **Run Backend Unit Tests**:
   ```powershell
   python -m pytest backend/tests -v
   ```

5. **Start FastAPI Backend Server**:
   ```powershell
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs` in development mode.

## 3. Storage & Security Layout
- `data/docs/`: Stores uploaded authorized NIEL technical PDFs (git-ignored).
- `data/index/`: Stores local FAISS vector index files and chunk metadata JSON (git-ignored).
- Secrets and index files are strictly excluded from git via `.gitignore`.

