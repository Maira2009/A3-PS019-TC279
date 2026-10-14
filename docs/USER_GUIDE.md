# DATAQUEST
## User guide

AIORI-3 PS-019 | Prototype v1.0.0 | 14 October 2026

DATAQUEST helps you locate potential personal-data fields, see where matching values appear, record purpose and retention evidence, and review findings. This guide follows the controls in the supplied prototype.

### Your first walkthrough

Once the application is running, open `http://127.0.0.1:5173` and check that the top bar says **API ok**.

1. On **Workspace**, select **Load synthetic demo workspace** once. It creates a new workspace, copies the three demo sources, adds example metadata, runs a scan, and opens Overview.
2. Open **Sources**. You should see `admissions.csv`, `events.csv`, and `support.db`.
3. Open **Inventory**, choose **PHONE** in Class, and select a finding. Look for `guardian_phone`, `Phone Data Detected`, and `mobile`.
4. Open **Footprint**. Find the PHONE group spanning all three sources and read its source locations and masked value.
5. Open **Metadata** to compare the declared purpose and retention information.
6. Open **Review**, add a note, and select **Accept**, **Reject**, or **Review later**.
7. Open **Evaluation** and select **Run evaluation**.
8. Open **Reports** and choose **Inventory CSV** or **Report HTML**.

The demo uses fictional data. Clicking the demo button again creates another workspace. Complete one walkthrough in the same workspace and scan.

### Find what you need

| Page | Topic |
| --- | --- |
| 2 | Install, start, and stop the application |
| 3 | Add files, configure a scan, read Overview |
| 4 | Interpret findings, footprints, and review decisions |
| 5 | Add purpose and retention metadata |
| 6 | Change detection rules and run evaluation |
| 7 | Export results, understand storage, delete data |
| 8 | Troubleshooting and presentation checklist |

### Three terms to know

**Workspace** groups your uploaded copies, declarations, scans, and decisions. A **scan** is one run against selected sources. A **finding** is a field-and-class candidate requiring review; it is not a count of people.

<!-- pagebreak -->

# 1. Install and launch

Extract the project ZIP first. Open the `DATAQUEST_PS019` folder containing `backend`, `frontend`, and `README.md`. Do not run it from inside the ZIP viewer.

### Prerequisites

Use Python 3.11 or 3.12, a modern browser, and Node.js with npm. For compatibility with the bundled application and test dependencies, use **Node.js 24.15 or later in the 24.x series, or 26.x**. Package installation needs internet access; normal scanning uses local services.

### Windows: first launch

Double-click `START_DATAQUEST_WINDOWS.cmd` in the extracted folder. The launcher checks prerequisites, installs project packages on first run, starts both services, and shows the website address. Keep its window open while using the app. If startup fails, read the message in that window and `backend/runtime/backend.stderr.log`.

For manual setup, open PowerShell in the extracted project folder. In the first window, run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Leave that window running. Open a second PowerShell window in the project folder:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Both windows must remain open while you use the app. The Python commands above work without activating the virtual environment.

### Later launches

You only need to install dependencies once unless they change. In the first window, open `backend` and run the final Python command above. In the second window, open `frontend` and run `npm run dev`. To stop, press **Ctrl+C** in each window. Closing the browser alone does not stop the services.

### macOS or Linux

From the project folder, create the environment with `cd backend` then `python3 -m venv .venv`. Use `.venv/bin/python -m pip install -r requirements.txt` and then:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal using the same frontend commands as Windows. `docs/SETUP_GUIDE.md` and `README.md` provide additional setup details.

<!-- pagebreak -->

# 2. Add sources and scan

### Create or open a workspace

On **Workspace**, enter a name under **Create a workspace** and select **Create workspace**. To use an existing workspace, choose it under **Open a workspace**. Its registered sources are retained.

Opening a workspace clears the active scan selection. The current UI has no saved-scan picker: run a new scan to populate the results pages. Export useful results before switching workspaces or scans.

### Upload files

1. Open **Sources** or **Scan** and select **Choose CSV or SQLite files**. You can select multiple files.
2. Select **Upload copies** and wait for the sources to appear in the table.
3. Select **Profile** beside a source to see the object and field names discovered.
4. Check the source status, then open **Scan**.

Accepted files are `.csv`, `.db`, `.sqlite`, and `.sqlite3`, with a default maximum of 25 MB each. Use CSVs with a header row; UTF-8 is recommended. A database must be a valid SQLite file, not a spreadsheet renamed to `.db`. DATAQUEST scans its local upload copy; editing the original later does not update that copy.

### Run a scan

1. Tick the sources you want to include. Select at least one.
2. Leave **Rows per table** at `100000` and **Samples per field** at `500` for the initial run.
3. Select **Start local scan** once and wait for Overview to appear.

Rows per table limits how many rows are read from each CSV or table. Samples per field uses the first non-empty values for detection and overlap grouping, rather than a random sample. The maximum settings are 1,000,000 rows and 10,000 samples. SQLite views are not scanned. Processing is synchronous: the UI shows loading, then the recorded result, rather than continuous percentage progress.

### Read Overview

| Indicator | Meaning |
| --- | --- |
| Profiled fields | Fields read within the scan bounds |
| Potential findings | Field-and-class candidates; one field may have multiple classes |
| Cross-source groups | Repeated normalized values across more than one source |
| Missing purpose / retention | Findings whose evidence status is not present, including partial evidence |
| Needs review | Findings still awaiting review or marked review later |

Check **Latest scan** for status and source failures. A partial scan means some sources failed while others produced results. The UI loads up to 500 findings and 500 footprint groups; related dashboard counts can be limited to those entries. Sources, metadata, and review-history lists load up to 100 entries. Use full scan exports for larger result sets.

<!-- pagebreak -->

# 3. Investigate and review

### Inventory

Use the **Class**, **Source**, **Review**, and **Evidence** filters together to narrow the list. Select a row, or focus it and press Enter, to open finding details. The panel shows the explanation, location, rule strength, reason codes, masked samples, metadata scope, and rule version.

| Class | What it suggests |
| --- | --- |
| PHONE | A phone-like field or value pattern |
| EMAIL | An email-like field or value pattern |
| PERSON_NAME | A field that may contain a person's name |
| ADDRESS | Address or location-related data |
| PERSONAL_ID | An identifier that may relate to a person |

These are editable prototype defaults. **Rule strength** measures configured evidence; 80% strength does not mean an 80% chance of being personal data. A finding can be incorrect, and an unflagged field can still contain personal data.

### Footprint

Each card displays a masked representative, class, source count, occurrence count, and source/object/field locations. **Cross source** means a repeated normalized value appears in multiple source files. **Within source** means repetition inside a single source.

PHONE normalization removes punctuation and spaces but does not add or remove country codes. EMAIL comparison ignores letter case. Groups are limited to sampled, pattern-matching values within this scan. Two cards with the same masked text may still represent different underlying values.

For the demo, look for the PHONE group containing admissions `guardian_phone`, events `Phone Data Detected`, and support `tickets / mobile`. Matching values suggest overlap; they do not establish that records belong to the same person.

### Human review

1. Open **Review**. The default Status filter shows `needs_review`.
2. Read the finding and add a **Reviewer note**, such as "Field context and sample pattern support a contact number."
3. Select **Accept** if you agree with the classification, **Reject** if it is a false positive, or **Review later** if more context is needed.
4. Switch Status to **All states** or the chosen state to find the item again. Select **Show review history** to inspect earlier decisions.

Decisions append new events under the label **Local reviewer**. Re-review preserves earlier history. Rejecting a finding does not remove it from the inventory or change evaluation scores. A new scan creates new findings; review decisions do not automatically carry over.

<!-- pagebreak -->

# 4. Record purpose and retention

**Metadata** records what you declare about why data is held and how long it should be retained. DATAQUEST checks for that evidence; it does not decide whether a declaration is legally sufficient.

### Add a declaration

1. Choose a **Source**, or leave **Any source** for a broader declaration.
2. Enter the exact **Object** and **Field** when the declaration applies to one field. For CSVs, the object is the CSV filename; for SQLite, it is the table name.
3. Choose a **Class**, or leave **Any class** if appropriate.
4. Enter **Declared purpose**, **Retention duration**, **Retention basis**, and an optional **Owner label**.
5. Select **Save declaration**. Then run a new scan to update finding and footprint evidence statuses.

### Demo example

The existing `support.db / tickets / mobile / PHONE` declaration has purpose "Support callback" and no retention information. For a fictional practice update, replace it with purpose "Support callback", duration "30 days", and basis "Synthetic support policy". These example values are not a retention recommendation.

The UI supports adding and deleting declarations, but has no Edit button. To replace one, first copy its details, delete that declaration after confirmation, then add the corrected version. The API also supports updates. Avoid duplicate declarations for the same scope.

### Scope and evidence status

Blank Source, Object, Field, or Class values broaden a declaration. Matching uses exact supplied names and favors declarations with more populated matching scope fields. Do not rely on the newest declaration winning a tie. Complete both purpose and retention on the declaration you want to apply; separate matching declarations are not merged.

| Status | How to read it |
| --- | --- |
| present | Non-placeholder evidence is supplied |
| missing | No matching evidence is supplied |
| partial | A supplied value is a placeholder such as TBD or unknown |

Purpose uses the purpose text. Retention can be present when either duration or basis is supplied. "Present" therefore means evidence exists, not that a full retention policy has been established.

### Import and export metadata

Use **Export metadata CSV** as your template, edit a copy, then select **Import CSV**. The sample template is `backend/data/demo/metadata.csv`. Keep its headers intact and use source filenames that exactly match sources in the selected workspace. An unmatched filename can become an any-source declaration, so check names before import. Import adds rows; it does not replace existing rows. Re-scan after any change.

<!-- pagebreak -->

# 5. Tune rules and evaluate

### Detection rules

Open **Rules** to enable or disable a class, edit its aliases, patterns, weights, threshold, and notes. These rules are shared across the local application, not isolated to one workspace.

| Control | Effect |
| --- | --- |
| Aliases | Comma-separated field-name clues |
| Patterns | One named regular expression per line, in name::regex format |
| Name / Pattern / Type weight | Contributions to the evidence score |
| Threshold | Minimum score needed to create a finding |

Weights and thresholds must be between 0 and 1. Keep the three weights' sum at or below 1. Invalid regular expressions are rejected. Leave the default patterns unchanged unless you are comfortable with regular expressions.

Select **Save new version**, then run a new scan. Existing scans keep their original findings and rule version. **Restore defaults** requires confirmation and restores the five prototype rules for subsequent scans. For a predictable demo, restore defaults before loading the synthetic workspace if you previously changed them.

### Evaluation

The synthetic demo scan already has its 19 bundled manual labels. Open **Evaluation** and select **Run evaluation** for that scan. Those labels are never applied to a scan of your own files.

For your scan, select **Download label template** on Evaluation. It lists the exact source, object, and field names from that scan. Fill `expected_class_key` with PHONE, EMAIL, PERSON_NAME, ADDRESS, or PERSONAL_ID and `label` with `positive`; for a negative field use `NONE` and `negative`. Keep one `dataset_key` across rows. Save as UTF-8 CSV, select **Choose label CSV**, then **Upload labels** and **Run evaluation**. You may label only a subset; unlabelled fields are excluded from metrics. Replacing labels invalidates the prior evaluation for that scan.

| Metric | Meaning |
| --- | --- |
| TP | A labelled positive correctly detected for that class |
| FP | A field incorrectly predicted as that class |
| FN | A labelled positive missed for that class |
| TN | A field correctly not predicted as that class |
| Precision | TP / (TP + FP): how many predictions were correct |
| Recall | TP / (TP + FN): how many labelled positives were found |
| Support | TP + FN: positive labels for the class |

**N/A** means the denominator is zero, not a zero score. The bundled benchmark contains 19 manually labelled fields covering five classes. Scores come from the scan's predictions; accepting or rejecting findings does not alter them. Small synthetic results do not establish accuracy on real data.

<!-- pagebreak -->

# 6. Export, keep, and delete

### Download results

Open **Reports** while your intended scan is active. Choose the format that fits your next task. Inventory filters do not restrict exports: they contain the full active scan's relevant records, including rejected findings.

| Export | Use |
| --- | --- |
| Inventory CSV | Review all findings in a spreadsheet |
| Footprints CSV / JSON | Inspect overlap groups and locations |
| Evidence gaps CSV | Follow up missing or partial evidence |
| Review history CSV | Keep decisions, notes, and timestamps |
| Metrics CSV / JSON | Reproduce or present evaluation results |
| Report Markdown / HTML | Share a readable scan summary |

Run **Evaluation** before downloading metrics. Reports include the latest saved evaluation for the active scan, or say it was not evaluated. CSV/JSON downloads may contain structured lists in a cell; that is expected. The HTML report is a simple text report that opens in a browser.

Detected source samples are masked. User-authored reviewer notes, metadata text, filenames, and field names can still appear in exports. Keep unnecessary personal details out of notes and declarations, and inspect a report before sharing it. Masking does not anonymize the uploaded files themselves.

### Where work is stored

Under default settings, the local application database is `backend/runtime/dataquest.sqlite3`, and source copies are in `backend/runtime/uploads/`. Browser local storage remembers the active workspace and scan IDs. Results persist on disk when you stop the servers.

For a backup, stop both services and copy the complete `backend/runtime` folder to a protected location. This backup includes raw uploaded file copies. Downloaded reports are separate files, usually in your browser's Downloads folder, and are not removed when you delete a workspace.

### Remove a source or workspace

**Sources > Remove** deletes the uploaded copy and scans that used it, including their results and review history. **Privacy > Delete selected workspace** deletes that workspace's upload copies, metadata, scans, reviews, evaluations, and audit records after confirmation. Original source files remain in their original locations.

Export anything you need before deleting. The app has no undo or trash. Workspace deletion does not reset the global detection rules. If removing a source leaves an old scan error on screen, reopen the workspace and run a new scan with the remaining sources.

<!-- pagebreak -->

# 7. Troubleshooting and demo checklist

| What you see | What to do |
| --- | --- |
| API unavailable or Failed to fetch | Confirm the backend window is still running. Open http://127.0.0.1:8000/health and look for status ok. Use the documented frontend address and port. |
| Browser cannot open the app | Confirm npm run dev is running and open the Local URL printed in that window. The supplied configuration uses port 5173. |
| Python or npm not recognized | Install the prerequisites, reopen your terminal, and confirm python --version and node --version work. |
| Node engine/version error | Use Node 24.15+ within 24.x, or 26.x, then rerun npm install from frontend. |
| Port already in use | Stop another DATAQUEST instance with Ctrl+C. Start one backend and one frontend. |
| No active scan | Open the intended workspace, select sources, and run a scan. Opening a saved workspace does not restore a prior scan selection. |
| Invalid, empty, or unreadable file | Check the actual file type, CSV headers/encoding, and size. For SQLite, close a writer and upload a consistent database copy. |
| Metadata change is not reflected | Run a new scan after saving, importing, deleting, or replacing declarations. |
| Reviewed item disappeared | Review defaults to needs_review. Change Status to All states or the decision you selected. |
| No footprint group | Check scan selection, sample limits, and value formatting. Country-code differences are not normalized away. |
| Metrics export says not evaluated | For a demo scan, select Run evaluation. For your own scan, upload matching manual labels first, then run evaluation. |
| Evaluation says labels are required | Download the template for that exact scan and upload completed labels. Demo labels do not apply to your files. |
| Numbers differ between runs | Check rules, sources, scan limits, and the active scan. The displayed metrics are computed, not fixed demo targets. |

### Before showing the prototype

1. Start both services and confirm **API ok**.
2. Restore default rules if needed, then load one fresh synthetic demo workspace.
3. Follow the sequence **Sources > Inventory > Footprint > Metadata > Review > Evaluation > Reports**.
4. Show the three phone field names and the PHONE group spanning all three sources.
5. Explain the events purpose gap and support retention gap, then record one review decision with a short note.
6. Run evaluation for this scan and download a report. Use the timed script in `docs/DEMO_SCRIPT.md` for a four-to-five-minute presentation.

### If a problem continues

Record the page, action, visible error, file type and size, and whether the synthetic demo works. Keep raw source values out of issue reports. The package includes `docs/TEST_RESULTS.md` for observed checks and `README.md` for further setup and prototype limitations. This guide documents the supplied v1.0.0 implementation; it does not claim visual browser testing was completed in the build environment.
