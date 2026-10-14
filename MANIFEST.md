# Deliverable manifest

## Application

- `backend/app/` — FastAPI application, SQLite schema, detection, profiling, footprints, evaluation, exports, and privacy-safe error handling.
- `backend/tests/` — automated API, rule, detection, evaluation, export, validation, and deletion tests.
- `frontend/src/` — React application with all twelve required workflow sections and live API integration.
- `frontend/src/tests/` — frontend component tests.

## Data

- `backend/data/demo/admissions.csv` — synthetic admissions data.
- `backend/data/demo/events.csv` — synthetic events data including `Phone Data Detected`.
- `backend/data/demo/support.db` — synthetic SQLite support database.
- `backend/data/demo/metadata.csv` — synthetic purpose and retention declarations.
- `backend/data/demo/gold_labels.csv` — manually authored field-level evaluation labels.
- `backend/scripts/generate_demo.py` — reproducible demo-data generator.

## Documentation

- `README.md` — project overview, complete setup, workflow, troubleshooting, and limitations.
- `docs/SETUP_GUIDE.md` — focused installation and startup guide.
- `docs/ARCHITECTURE.md` — system structure and data flow.
- `docs/DATA_DICTIONARY.md` — application and import/export field definitions.
- `docs/PRIVACY.md` — storage, masking, deletion, trust boundaries, and limitations.
- `docs/DEMO_SCRIPT.md` — hackathon presentation walkthrough.
- `docs/TEST_PLAN.md` — test strategy and acceptance coverage.
- `docs/TEST_RESULTS.md` — exact checks executed and observed results.
- `docs/REQUIREMENTS_TRACEABILITY.md` — implementation mapping to the build specification.
- `LICENSE` — MIT license.

Generated dependencies, virtual environments, local runtime databases, copied uploads, caches, logs, and temporary build state are intentionally excluded from the ZIP.

