# DATAQUEST Privacy Model

## Local processing

The backend binds to `127.0.0.1` by default. Development CORS accepts only `http://127.0.0.1:5173` and `http://localhost:5173`. Production code includes no external AI service, analytics, telemetry, remote logging, remote font, CDN, or network database connector.

## Data minimization

- The browser receives masked samples only.
- Logs and audit events contain identifiers, counts, actions, and safe errors, not cell contents.
- Findings store masked samples and rule evidence, not raw candidate values.
- Footprints store masked representatives, locations, ambiguity text, and opaque scan-specific group IDs.
- A random secret exists only while a scan builds overlap groups.
- Exports omit raw values and internal fingerprints.
- CSV outputs prefix text beginning with `=`, `+`, `-`, or `@` to reduce spreadsheet formula injection risk.
- Manual evaluation labels are stored locally per scan; the bundled demo labels are never applied to uploaded sources. Label CSVs should contain field identifiers and class decisions only, not cell contents or personal data in annotation notes.

## Source handling

Uploads receive server-generated names and stay below a configurable 25 MB default. SQLite signatures are checked. SQLite copies open through a read-only URI; the application never executes user-provided SQL. Scans use bounded row and sample limits.

## Deletion

Workspace deletion requires explicit confirmation. It removes DATAQUEST-owned upload copies and workspace database records, including findings, footprints, review history, evaluations, metadata, and audit history. It never deletes the original source selected by the user.

## Limitations

Localhost reduces exposure but does not make the prototype secure against a compromised computer or browser extension. Masking reduces display risk but does not anonymize source data. Value equality can arise from shared, recycled, placeholder, or incorrect values. Purpose and retention declarations may be incomplete or inaccurate. An independent security and privacy review is required before real-world deployment.

