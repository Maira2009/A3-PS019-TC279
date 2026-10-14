# DATAQUEST Test Plan

## Automated backend coverage

- Health response and `local_only=true`.
- Rejection of non-local CORS origin.
- PHONE aliases and negative-control fields.
- Invalid regex rejection.
- Demo load with two CSVs and one SQLite database.
- Field detection, masked API results, and three-source phone overlap.
- Purpose-missing and retention-missing evidence gaps.
- Read-only SQLite checksum before and after profiling.
- Append-only review event history.
- Hand-verifiable confusion counts and metric denominators.
- Formula-injection neutralization.
- All nine masked export types.
- Unsupported file, corrupt SQLite, and empty CSV handling.
- Confirmation and local-copy removal during workspace deletion.

## Automated frontend coverage

- Welcome workflow renders with local-processing context.
- Privacy navigation and local-only explanation.
- TypeScript compile and Vite production build.

## Manual acceptance pass

1. Start API and UI on the documented localhost ports.
2. Load the demo and navigate all twelve sections.
3. Confirm the Overview numbers match Inventory, Footprint, and metadata gaps.
4. Inspect masked values at desktop and tablet widths.
5. Edit a rule alias and threshold, save, and run a new scan.
6. Create a metadata declaration and confirm it appears in the list.
7. Review the same finding twice and inspect history through the API.
8. Run evaluation and download every export.
9. Search exports for unmasked demo phone/email values and `hmac`.
10. Delete a workspace and verify copied uploads disappear while the original demo files remain.

## Commands

```powershell
cd backend
pytest -q
cd ..\frontend
npm test
npm run build
```

The final delivery report distinguishes commands executed in the build environment from manual checks that remain for the recipient’s browser.

