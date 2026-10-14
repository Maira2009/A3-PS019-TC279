# DATAQUEST Setup Guide

## Quick start on Windows

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`, then select **Load synthetic demo workspace**.

## Quick start on macOS or Linux

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

## Configuration

Copy `backend/.env.example` values into your shell or environment manager if defaults need to change. Do not bind the prototype to `0.0.0.0` unless you have added appropriate authentication and transport security.

`VITE_API_BASE` controls the browser API URL at frontend build time. When changing it, update `DATAQUEST_ALLOWED_ORIGINS` to the exact local frontend origins.

