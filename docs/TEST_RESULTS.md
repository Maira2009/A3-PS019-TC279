# Verified test results

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

