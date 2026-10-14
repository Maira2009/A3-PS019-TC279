# DATAQUEST Setup Guide

Use Python 3.11 or 3.12 and Node.js 24.15 or later within 24.x, or 26.x, with npm. See [the user guide](USER_GUIDE.md) for installation, everyday use, and troubleshooting.

## Quick start on Windows

After cloning the repository or extracting its ZIP, double-click `START_DATAQUEST_WINDOWS.cmd` at the project root. Leave that window open while using the website at `http://127.0.0.1:5173/`. The first run installs packages; internet access is needed then. If the launcher reports a backend failure, inspect `backend/runtime/backend.stderr.log`.

For manual setup, open two PowerShell windows. In the first:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another PowerShell window:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`, then select **Load synthetic demo workspace**.

For your own files, create a workspace, use the uploader on **Sources** or **Scan**, then run a scan. Evaluation requires a separate manual-label CSV for that scan; download its template on **Evaluation**. The bundled demo labels are never used for your files.

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

GitHub is suitable for sharing this source repository. GitHub Pages cannot execute the Python backend; people should clone or download and run the app locally.

