# Share DATAQUEST through GitHub

DATAQUEST is a real local website with a React frontend and a Python/SQLite backend. A GitHub repository can hold the complete source. Visitors clone or download it and run the website on their own computer. GitHub Pages alone cannot execute the backend, so a Pages-only upload would leave upload, scan, and evaluation nonfunctional.

## Before uploading

1. Upload the contents of the `DATAQUEST_PS019` folder, not the outer deliverable ZIP.
2. Keep `.gitignore` in the repository. It excludes virtual environments, `node_modules`, local runtime uploads, the local results database, logs, and build outputs.
3. Do not commit real personal-data CSVs, SQLite databases, label notes containing personal data, or any `backend/runtime/` files. The included demo data is synthetic.
4. Include `README.md`, `docs/USER_GUIDE.pdf`, and the launch scripts so reviewers can start it easily.

## Reviewer instructions

On Windows: install Python 3.11 or 3.12 and Node.js 24.15+ (24.x) or 26.x with npm, clone or download the repository, then double-click `START_DATAQUEST_WINDOWS.cmd`. Keep the launcher window open and visit `http://127.0.0.1:5173/`.

On macOS/Linux: follow `docs/SETUP_GUIDE.md`. The first run needs internet access to install packages; scans run locally afterward.

To test custom data, create a workspace, upload CSV/SQLite files on Sources or Scan, run a scan, then download the scan-specific label template on Evaluation. Demo labels do not apply to uploaded files.
