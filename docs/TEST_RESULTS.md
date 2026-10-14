# Verified test results

## Scan, upload, and evaluation fix verification - 14 October 2026

- Backend: `backend/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` - **18 passed**. This includes uploaded CSV partial/failure handling, custom scan refusing demo labels, exact-scan label CSV upload, computed custom metrics, mismatched-label rejection, demo-only labels, and exclusion of unlabelled fields from false positives.
- Frontend: Vitest `run` - **2 test files, 6 tests passed**. This includes the scan click, lost-backend feedback, visible file upload on Scan, and custom-label gating on Evaluation.
- TypeScript: `tsc -b` - **passed**.
- Frontend production bundle: `vite build` - **passed** (18 modules; HTML 0.50 kB, CSS 15.30 kB, JavaScript 262.98 kB).
- Windows launcher: started both services in this environment; `/health` returned `ok`, and the website returned HTTP 200. A pre-existing virtual environment was correctly reused.
- Live HTTP workflow through the website's Vite proxy: demo scan completed (3 sources, 16 findings, 6 footprint groups, 19 labels); a freshly uploaded CSV scan completed (2 findings); evaluation correctly refused to run before labels, then a downloaded template, uploaded custom label CSV (3 fields), and custom evaluation succeeded.

The only observed automated-test warning was a Starlette/AnyIO deprecation warning from a dependency. It did not affect test results. The user's particular uploaded file was not provided, so its exact format cannot be verified here.

The earlier 11 October results below are retained as the original build record.

Verification date: 2026-10-11

## Automated backend suite

Command from `backend/`:

```powershell
pytest -q
```

Observed result: **14 passed** in 7.33 seconds.

Covered behavior includes health and local-only configuration, CORS, rule validation, deterministic detection, the full demo flow, read-only SQLite handling, metadata gaps, scan-local overlap grouping, append-only review history, metric arithmetic, privacy-safe exports, formula-injection defense, invalid/empty uploads, and confirmed deletion.

One dependency warning was observed in Starlette's test client about an AnyIO compatibility alias. It does not originate in DATAQUEST code and did not affect the results.

## Automated frontend suite

Command from `frontend/`:

```powershell
npm test
```

Observed result: **1 test file passed; 2 tests passed** in 2.99 seconds.

The tests verify the application shell/navigation and privacy messaging while using a controlled fetch boundary.

## Production frontend build

Command from `frontend/`:

```powershell
npm run build
```

Observed result: **successful**. Vite transformed 18 modules and emitted the production bundle.

- HTML: 0.50 kB (0.31 kB gzip)
- CSS: 14.95 kB (4.20 kB gzip)
- JavaScript: 258.07 kB (77.89 kB gzip)

## Python compilation check

Command from `backend/`:

```powershell
python -m compileall -q app tests
```

Observed result: **passed**.

## Live HTTP workflow check

Both services were started on loopback and exercised over HTTP in one controlled verification run. Observed result:

- API health: `ok`
- API version: `1.0.0`
- API local-only flag: `true`
- Frontend response: HTTP `200`
- Demo scan status: `completed`
- Sources scanned: `3`
- Findings produced: `16`
- Footprint groups produced: `6`
- Supported classes evaluated: `5`
- Manual labels evaluated: `19`

## Visual verification limitation

The in-app browser in the build environment was isolated from the local server process, so a genuine browser screenshot could not be captured. No screenshot was fabricated. The production build, frontend component tests, backend integration tests, and live HTTP workflow all completed successfully.

