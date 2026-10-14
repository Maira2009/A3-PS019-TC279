import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { API_BASE, api } from "./api/client";
import type { Evaluation, Finding, Footprint, Metadata, Page, Rule, Scan, Source, Summary, Workspace } from "./api/types";
import { AppShell, EmptyState, PageHeader, StatusBadge } from "./components/AppShell";

type DemoResponse = { workspace: Workspace; sources: Source[]; scan: Scan };
const titleByPage: Record<string, string> = {
  welcome: "Workspace", sources: "Source manager", scan: "Scan configuration", dashboard: "Overview",
  inventory: "Inventory", footprint: "Footprint explorer", metadata: "Metadata evidence", review: "Human review",
  evaluation: "Evaluation", reports: "Reports and export", rules: "Detection rules", privacy: "Privacy and settings"
};

function useHashPage() {
  const current = () => location.hash.replace("#", "") || "welcome";
  const [page, setPage] = useState(current);
  useEffect(() => { const listener = () => setPage(current()); addEventListener("hashchange", listener); return () => removeEventListener("hashchange", listener); }, []);
  return titleByPage[page] ? page : "welcome";
}

function App() {
  const page = useHashPage();
  const [health, setHealth] = useState<{ status: string; version: string; local_only: boolean } | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState(() => localStorage.getItem("dq_workspace") ?? "");
  const [scanId, setScanId] = useState(() => localStorage.getItem("dq_scan") ?? "");
  const [sources, setSources] = useState<Source[]>([]);
  const [scan, setScan] = useState<Scan | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [footprints, setFootprints] = useState<Footprint[]>([]);
  const [metadata, setMetadata] = useState<Metadata[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const guard = useCallback(async <T,>(operation: () => Promise<T>, onError?: (error: Error) => void): Promise<T | undefined> => {
    setError(""); setBusy(true);
    try { return await operation(); }
    catch (e) { const error = e instanceof Error ? e : new Error("Unexpected error"); setError(error.message); onError?.(error); return undefined; }
    finally { setBusy(false); }
  }, []);

  const refresh = useCallback(async (active: { workspaceId?: string; scanId?: string } = {}) => {
    const activeWorkspaceId = active.workspaceId ?? workspaceId;
    const activeScanId = active.scanId ?? scanId;
    const tasks: Promise<unknown>[] = [api.get("/health").then(v => setHealth(v as typeof health)), api.get<Page<Workspace>>("/api/v1/workspaces").then(v => setWorkspaces(v.items))];
    if (activeWorkspaceId) {
      tasks.push(api.get<Page<Source>>(`/api/v1/workspaces/${activeWorkspaceId}/sources`).then(v => setSources(v.items)));
      tasks.push(api.get<Page<Metadata>>(`/api/v1/workspaces/${activeWorkspaceId}/metadata`).then(v => setMetadata(v.items)));
    }
    tasks.push(api.get<{ items: Rule[] }>("/api/v1/rules").then(v => setRules(v.items)));
    if (activeScanId) {
      tasks.push(api.get<Scan>(`/api/v1/scans/${activeScanId}`).then(v => { setScan(v); setSummary(v.summary ?? null); }));
      tasks.push(api.get<Page<Finding>>(`/api/v1/scans/${activeScanId}/findings?limit=500`).then(v => setFindings(v.items)));
      tasks.push(api.get<Page<Footprint>>(`/api/v1/scans/${activeScanId}/footprints?limit=500`).then(v => setFootprints(v.items)));
    }
    await Promise.all(tasks);
  }, [workspaceId, scanId]);

  useEffect(() => { guard(refresh); }, [refresh, guard]);
  useEffect(() => { document.title = `${titleByPage[page]} · DATAQUEST`; }, [page]);

  const chooseWorkspace = (id: string) => {
    setWorkspaceId(id); localStorage.setItem("dq_workspace", id);
    setScanId(""); localStorage.removeItem("dq_scan"); setScan(null); setSummary(null); setFindings([]); setFootprints([]); setEvaluation(null);
  };
  const chooseScan = (id: string) => { setScanId(id); localStorage.setItem("dq_scan", id); setEvaluation(null); };
  const pageProps = { workspaceId, scanId, sources, scan, summary, findings, footprints, metadata, rules, evaluation, health, busy, guard, refresh, chooseWorkspace, chooseScan, setRules, setEvaluation };

  return <AppShell page={page}>
    <div className="topbar"><div>{workspaceId ? <><span>Workspace</span><strong>{workspaces.find(w => w.id === workspaceId)?.name ?? "Selected workspace"}</strong></> : <><span>No workspace selected</span><strong>Start with the synthetic demo</strong></>}</div><div className="top-status"><span className={health?.status === "ok" ? "dot ok" : "dot"} />{health ? `API ${health.status}` : "API unavailable"}</div></div>
    {error && <div className="error-banner" role="alert"><strong>Something needs attention</strong><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error">×</button></div>}
    {busy && <div className="loading-bar" aria-label="Loading" />}
    {page === "welcome" && <WelcomePage {...pageProps} workspaces={workspaces} />}
    {page === "sources" && <SourcesPage {...pageProps} />}
    {page === "scan" && <ScanPage {...pageProps} />}
    {page === "dashboard" && <DashboardPage {...pageProps} />}
    {page === "inventory" && <InventoryPage {...pageProps} />}
    {page === "footprint" && <FootprintPage {...pageProps} />}
    {page === "metadata" && <MetadataPage {...pageProps} />}
    {page === "review" && <ReviewPage {...pageProps} />}
    {page === "evaluation" && <EvaluationPage {...pageProps} />}
    {page === "reports" && <ReportsPage {...pageProps} />}
    {page === "rules" && <RulesPage {...pageProps} />}
    {page === "privacy" && <PrivacyPage {...pageProps} />}
  </AppShell>;
}

type Props = {
  workspaceId: string; scanId: string; sources: Source[]; scan: Scan | null; summary: Summary | null;
  findings: Finding[]; footprints: Footprint[]; metadata: Metadata[]; rules: Rule[]; evaluation: Evaluation | null;
  health: { status: string; version: string; local_only: boolean } | null; busy: boolean;
  guard: <T>(op: () => Promise<T>, onError?: (error: Error) => void) => Promise<T | undefined>; refresh: (active?: { workspaceId?: string; scanId?: string }) => Promise<void>;
  chooseWorkspace: (id: string) => void; chooseScan: (id: string) => void; setRules: (rules: Rule[]) => void;
  setEvaluation: (evaluation: Evaluation | null) => void;
};

function WelcomePage(props: Props & { workspaces: Workspace[] }) {
  const [name, setName] = useState("");
  const create = async (e: FormEvent) => { e.preventDefault(); const item = await props.guard(() => api.post<Workspace>("/api/v1/workspaces", { name })); if (item) { props.chooseWorkspace(item.id); setName(""); location.hash = "sources"; } };
  const demo = async () => { const result = await props.guard(() => api.post<DemoResponse>("/api/v1/demo")); if (result) { props.chooseWorkspace(result.workspace.id); props.chooseScan(result.scan.id); await props.refresh({ workspaceId: result.workspace.id, scanId: result.scan.id }); location.hash = "dashboard"; } };
  return <section className="page welcome-page">
    <div className="hero">
      <p className="eyebrow">AIORI 3 · PS 019</p><h1>Personal data discovery with an evidence trail</h1>
      <p className="hero-copy">Discover potential personal-data fields in CSV and SQLite sources, trace equal normalized values across locations, map declared purpose and retention evidence, and keep uncertainty open for human review.</p>
      <div className="hero-actions"><button className="primary" onClick={demo}>Load synthetic demo workspace</button><a className="secondary" href="#privacy">Read the privacy model</a></div>
      <div className="trust-row"><span>Localhost only</span><span>Masked samples</span><span>No external AI</span><span>Heuristic, reviewable findings</span></div>
    </div>
    <div className="split-grid">
      <article className="panel"><h2>Create a workspace</h2><p>A workspace keeps copied uploads, scans, metadata, and review history together.</p><form onSubmit={create} className="stack"><label>Name<input value={name} onChange={e => setName(e.target.value)} required maxLength={120} placeholder="Privacy inventory pilot" /></label><button className="primary" type="submit">Create workspace</button></form></article>
      <article className="panel"><h2>Open a workspace</h2>{props.workspaces.length ? <div className="workspace-list">{props.workspaces.map(w => <button key={w.id} className={props.workspaceId === w.id ? "workspace active" : "workspace"} onClick={() => { props.chooseWorkspace(w.id); location.hash = "sources"; }}><strong>{w.name}</strong><span>{new Date(w.created_at).toLocaleString()}</span></button>)}</div> : <EmptyState title="No saved workspaces" body="Create one or load the synthetic demo." />}</article>
    </div>
  </section>;
}

function SourcesPage(props: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [profile, setProfile] = useState<{ source_id: string; items: { object_name: string; field_name: string }[]; total: number } | null>(null);
  const upload = async () => { if (!props.workspaceId || !files.length || uploading) return; setUploading(true); setUploadError(""); const result = await props.guard(() => api.upload<Page<Source>>(`/api/v1/workspaces/${props.workspaceId}/sources`, files), error => setUploadError(error.message)); if (result) { setFiles([]); await props.guard(() => props.refresh(), error => setUploadError(error.message)); } setUploading(false); };
  const remove = async (id: string) => { if (!confirm("Remove this copied source and any scans that use it? The original file stays untouched.")) return; await props.guard(() => api.del(`/api/v1/sources/${id}?confirm=true`)); await props.refresh(); };
  const inspect = async (id: string) => { const result = await props.guard(() => api.post<{ source_id: string; items: { object_name: string; field_name: string }[]; total: number }>(`/api/v1/sources/${id}/profile`)); if (result) setProfile(result); };
  return <section className="page"><PageHeader eyebrow="02 · Ingestion" title="Source manager" description="Register CSV files and SQLite databases. DATAQUEST copies files into local application storage and never modifies originals." actions={<a className="secondary" href="#scan">Configure scan</a>} />
    {!props.workspaceId ? <NeedWorkspace /> : <><div className="upload-zone"><div><strong>Upload your files</strong><p>CSV, DB, SQLITE, or SQLITE3. Maximum 25 MB per file. Choose files, then click Upload copies.</p></div><label className="file-button">Choose CSV or SQLite files<input type="file" multiple accept=".csv,.db,.sqlite,.sqlite3" onChange={e => setFiles(Array.from(e.target.files ?? []))} /></label>{files.length > 0 && <><span>{files.map(file => file.name).join(", ")}</span><button className="primary" disabled={uploading} onClick={upload}>{uploading ? "Uploading..." : "Upload copies"}</button></>}</div>{uploadError && <p className="scan-feedback scan-feedback-error" role="alert">{uploadError}</p>}
    <div className="panel table-panel"><div className="panel-heading"><h2>Registered sources</h2><span>{props.sources.length} source{props.sources.length !== 1 ? "s" : ""}</span></div>{props.sources.length ? <table><thead><tr><th>Source</th><th>Type</th><th>Size</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{props.sources.map(source => <tr key={source.id}><td><strong>{source.display_name}</strong><small>{source.id.slice(0, 8)}</small></td><td>{source.source_type.toUpperCase()}</td><td>{(source.file_size_bytes / 1024).toFixed(1)} KB</td><td><StatusBadge value={source.status} /></td><td><div className="button-row"><button className="secondary" onClick={() => inspect(source.id)}>Profile</button><button className="text-danger" onClick={() => remove(source.id)}>Remove</button></div></td></tr>)}</tbody></table> : <EmptyState title="No sources yet" body="Choose at least two CSVs and one SQLite database, or load the synthetic demo." />}</div>{profile && <div className="panel profile-summary"><button className="drawer-close" onClick={() => setProfile(null)} aria-label="Close profile">×</button><h2>Profile summary</h2><p>{profile.total} fields across {new Set(profile.items.map(item => item.object_name)).size} objects</p><div className="tag-list">{profile.items.map((item, i) => <span key={`${item.object_name}-${item.field_name}-${i}`}>{item.object_name} / {item.field_name}</span>)}</div></div>}</>}
  </section>;
}

function ScanPage(props: Props) {
  const [selected, setSelected] = useState<string[]>(props.sources.map(s => s.id));
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [rowLimit, setRowLimit] = useState(100000); const [sampleLimit, setSampleLimit] = useState(500);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [failedSources, setFailedSources] = useState<Summary["failed_sources"]>([]);
  useEffect(() => setSelected(props.sources.map(s => s.id)), [props.sources]);
  const upload = async () => {
    if (!props.workspaceId || !files.length || uploading) return;
    setUploading(true);
    setUploadError("");
    const result = await props.guard(() => api.upload<Page<Source>>(`/api/v1/workspaces/${props.workspaceId}/sources`, files), error => setUploadError(error.message));
    if (result) { setFiles([]); await props.guard(() => props.refresh(), error => setUploadError(error.message)); }
    setUploading(false);
  };
  const run = async () => {
    if (!selected.length || scanning) return;
    setScanning(true);
    setScanError("");
    setFailedSources([]);
    const result = await props.guard(async () => {
      const scan = await api.post<Scan>(`/api/v1/workspaces/${props.workspaceId}/scans`, {
        source_ids: selected,
        options: { row_limit_per_table: rowLimit, sample_limit_per_field: sampleLimit, include_footprints: true }
      });
      props.chooseScan(scan.id);
      await props.refresh({ scanId: scan.id });
      return scan;
    }, error => setScanError(error.message));
    setScanning(false);
    if (!result) return;
    if (result.summary?.failed_sources?.length) setFailedSources(result.summary.failed_sources);
    if (result.status === "failed") {
      setScanError("No selected source could be read. Check the source errors below and retry.");
      return;
    }
    if (result.status === "partial") return;
    location.hash = "dashboard";
  };
  return <section className="page"><PageHeader eyebrow="03 · Configure" title="Scan configuration" description="Choose sources and bounded scan limits. The stage shown after completion comes from the backend scan record." actions={<a className="secondary" href="#rules">Edit detection rules</a>} />
    {!props.workspaceId ? <NeedWorkspace /> : <><div className="upload-zone"><div><strong>Upload your CSV or SQLite files here</strong><p>Choose files, click Upload copies, then select them below and start the scan.</p></div><label className="file-button">Choose CSV or SQLite files<input type="file" multiple accept=".csv,.db,.sqlite,.sqlite3" onChange={e => setFiles(Array.from(e.target.files ?? []))} /></label>{files.length > 0 && <><span>{files.map(file => file.name).join(", ")}</span><button className="primary" disabled={uploading} onClick={upload}>{uploading ? "Uploading..." : "Upload copies"}</button></>}</div>{uploadError && <p className="scan-feedback scan-feedback-error" role="alert">{uploadError}</p>}<div className="split-grid"><article className="panel"><h2>Sources</h2><div className="check-list">{props.sources.map(source => <label key={source.id}><input type="checkbox" checked={selected.includes(source.id)} onChange={e => setSelected(e.target.checked ? [...selected, source.id] : selected.filter(id => id !== source.id))} /><span><strong>{source.display_name}</strong><small>{source.source_type.toUpperCase()}</small></span></label>)}</div></article>
    <article className="panel"><h2>Limits</h2><div className="form-grid"><label>Rows per table<input type="number" min="1" max="1000000" value={rowLimit} onChange={e => setRowLimit(Number(e.target.value))} /></label><label>Samples per field<input type="number" min="1" max="10000" value={sampleLimit} onChange={e => setSampleLimit(Number(e.target.value))} /></label></div><p className="muted">Larger limits increase local processing time. Raw values remain inside the backend and are not returned to the browser.</p><button className="primary full" disabled={!selected.length || scanning || props.health?.status !== "ok"} onClick={run}>{scanning ? "Scanning selected sources..." : "Start local scan"}</button>{scanning && <p className="scan-feedback" role="status">The local scan is running. Keep both service windows open; larger files can take longer.</p>}{!selected.length && <p className="scan-feedback">Select at least one source above to enable scanning.</p>}{props.health?.status !== "ok" && <div className="scan-feedback" role="alert">The local API is unavailable. Keep the backend terminal running, confirm <code>http://127.0.0.1:8000/health</code> opens, then <button className="secondary" onClick={() => props.guard(() => props.refresh())}>Retry connection</button>.</div>}{scanError && <p className="scan-feedback scan-feedback-error" role="alert">{scanError}</p>}{failedSources.length > 0 && <div className="scan-feedback scan-feedback-error"><strong>Source errors</strong><ul>{failedSources.map(source => <li key={source.source_id}>{source.source}: {source.error}</li>)}</ul></div>}{props.scan && <div className="scan-result"><StatusBadge value={props.scan.status} /><span>Stage: {props.scan.stage}</span></div>}</article></div></>}
  </section>;
}

function DashboardPage(props: Props) {
  const counts = useMemo(() => ({
    purpose: props.findings.filter(f => f.purpose_status !== "present").length,
    retention: props.findings.filter(f => f.retention_status !== "present").length,
    review: props.findings.filter(f => ["needs_review", "review_later"].includes(f.review_status)).length
  }), [props.findings]);
  const byClass = useMemo(() => Object.entries(props.findings.reduce<Record<string, number>>((acc, f) => ({ ...acc, [f.class_key]: (acc[f.class_key] ?? 0) + 1 }), {})), [props.findings]);
  return <section className="page"><PageHeader eyebrow="04 · Evidence overview" title="Overview" description="Every figure below comes from the active scan API response." actions={<a className="primary" href="#inventory">Open inventory</a>} />
    {!props.scanId ? <NeedScan /> : <><div className="metric-grid">{[
      ["Sources", props.summary?.source_count ?? 0, "#sources"], ["Profiled fields", props.summary?.profiled_field_count ?? 0, "#inventory"], ["Potential findings", props.findings.length, "#inventory"],
      ["Cross-source groups", props.footprints.filter(f => f.overlap_type === "cross_source").length, "#footprint"], ["Missing purpose", counts.purpose, "#metadata"], ["Missing retention", counts.retention, "#metadata"], ["Needs review", counts.review, "#review"]
    ].map(([label, value, href]) => <a className="metric" href={String(href)} key={String(label)}><span>{label}</span><strong>{value}</strong></a>)}</div>
    <div className="split-grid"><article className="panel"><h2>Findings by class</h2>{byClass.length ? <div className="bar-list">{byClass.map(([label, value]) => <div key={label}><span>{label.replaceAll("_", " ")}</span><div><i style={{ width: `${Math.max(8, value / Math.max(...byClass.map(x => x[1])) * 100)}%` }} /></div><strong>{value}</strong></div>)}</div> : <EmptyState title="No findings" body="Run a scan to populate evidence." />}</article>
    <article className="panel"><h2>Latest scan</h2><dl className="detail-list"><div><dt>Status</dt><dd><StatusBadge value={props.scan?.status ?? "unknown"} /></dd></div><div><dt>Stage</dt><dd>{props.scan?.stage}</dd></div><div><dt>Objects</dt><dd>{props.summary?.object_count ?? 0}</dd></div><div><dt>Source failures</dt><dd>{props.summary?.failed_sources?.length ?? 0}</dd></div></dl><p className="muted">Results use deterministic rules. Evidence strength is not a probability or legal conclusion.</p></article></div></>}
  </section>;
}

function InventoryPage(props: Props) {
  const [classFilter, setClassFilter] = useState(""); const [statusFilter, setStatusFilter] = useState(""); const [sourceFilter, setSourceFilter] = useState(""); const [gapFilter, setGapFilter] = useState(""); const [selected, setSelected] = useState<Finding | null>(null);
  const filtered = props.findings.filter(f => (!classFilter || f.class_key === classFilter) && (!statusFilter || f.review_status === statusFilter) && (!sourceFilter || f.source_name === sourceFilter) && (!gapFilter || f[gapFilter as "purpose_status" | "retention_status"] !== "present"));
  return <section className="page"><PageHeader eyebrow="05 · Detection" title="Potential personal-data inventory" description="Findings combine field-name clues, bounded value patterns, inferred type support, and configured thresholds." />
    {!props.scanId ? <NeedScan /> : <><div className="filters"><label>Class<select value={classFilter} onChange={e => setClassFilter(e.target.value)}><option value="">All classes</option>{props.rules.map(r => <option key={r.class_key}>{r.class_key}</option>)}</select></label><label>Source<select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}><option value="">All sources</option>{Array.from(new Set(props.findings.map(f => f.source_name))).map(name => <option key={name}>{name}</option>)}</select></label><label>Review<select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="">All states</option><option>needs_review</option><option>accepted</option><option>rejected</option><option>review_later</option></select></label><label>Evidence<select value={gapFilter} onChange={e => setGapFilter(e.target.value)}><option value="">All evidence</option><option value="purpose_status">Purpose gap</option><option value="retention_status">Retention gap</option></select></label><span>{filtered.length} findings</span></div>
    <div className="content-drawer"><div className="panel table-panel"><table><thead><tr><th>Class</th><th>Location</th><th>Field</th><th>Strength</th><th>Purpose</th><th>Retention</th><th>Review</th></tr></thead><tbody>{filtered.map(f => <tr key={f.id} onClick={() => setSelected(f)} tabIndex={0} onKeyDown={e => e.key === "Enter" && setSelected(f)}><td><span className="class-chip">{f.class_key}</span></td><td>{f.source_name}<small>{f.object_name}</small></td><td><strong>{f.field_name}</strong></td><td>{Math.round(f.rule_strength * 100)}% <small>{f.confidence_label}</small></td><td><StatusBadge value={f.purpose_status} /></td><td><StatusBadge value={f.retention_status} /></td><td><StatusBadge value={f.review_status} /></td></tr>)}</tbody></table></div>{selected && <FindingDrawer finding={selected} close={() => setSelected(null)} />}</div></>}
  </section>;
}

function FindingDrawer({ finding, close }: { finding: Finding; close: () => void }) {
  return <aside className="drawer" aria-label="Finding details"><button className="drawer-close" onClick={close} aria-label="Close details">×</button><p className="eyebrow">Potential personal-data field</p><h2>{finding.field_name}</h2><span className="class-chip">{finding.class_key}</span><p>{finding.explanation}</p><dl className="detail-list"><div><dt>Location</dt><dd>{finding.source_name} / {finding.object_name}</dd></div><div><dt>Rule strength</dt><dd>{Math.round(finding.rule_strength * 100)}% ({finding.confidence_label})</dd></div><div><dt>Reason codes</dt><dd>{finding.reason_codes?.join(", ")}</dd></div><div><dt>Masked samples</dt><dd>{finding.masked_samples?.join(", ") || "None"}</dd></div><div><dt>Metadata scope</dt><dd>{finding.metadata_scope ?? "none"}</dd></div><div><dt>Rule version</dt><dd>{finding.rule_version}</dd></div></dl><p className="disclaimer">This finding is heuristic and may be challenged during review.</p></aside>;
}

function FootprintPage(props: Props) {
  return <section className="page"><PageHeader eyebrow="06 · Cross-source trace" title="Footprint explorer" description="Groups use equal conservative normalized values within this scan. No fuzzy identity resolution is performed." />
    <div className="disclaimer prominent"><strong>Potential overlap ≠ proof of identity.</strong> Shared, recycled, placeholder, or incorrectly entered values may create overlaps.</div>
    {!props.scanId ? <NeedScan /> : props.footprints.length ? <div className="footprint-grid">{props.footprints.map(group => <article className="panel footprint-card" key={group.id}><div className="footprint-top"><span className="class-chip">{group.class_key}</span><StatusBadge value={group.overlap_type} /></div><h2>{group.masked_representative}</h2><p><strong>{group.source_count}</strong> sources · <strong>{group.occurrence_count}</strong> occurrences</p><div className="locations">{group.locations?.map((location, i) => <div key={i}><span className="location-dot" /><div><strong>{String(location.source_name)}</strong><span>{String(location.object_name)} / {String(location.field_name)}</span><small>purpose {String(location.purpose_status)} · retention {String(location.retention_status)}</small></div></div>)}</div><p className="muted">{group.ambiguity_note}</p></article>)}</div> : <EmptyState title="No repeated candidate values" body="This scan produced no within-source or cross-source overlap groups." />}
  </section>;
}

function MetadataPage(props: Props) {
  const empty = { source_id: "", object_name: "", field_name: "", class_key: "", purpose_text: "", retention_duration: "", retention_basis: "", owner_label: "" };
  const [form, setForm] = useState(empty);
  const submit = async (e: FormEvent) => { e.preventDefault(); const payload = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v || null])); const result = await props.guard(() => api.post(`/api/v1/workspaces/${props.workspaceId}/metadata`, payload)); if (result) { setForm(empty); await props.refresh(); } };
  const importCsv = async (file: File) => { const result = await props.guard(() => api.upload(`/api/v1/workspaces/${props.workspaceId}/metadata/import`, [file], "file")); if (result) await props.refresh(); };
  const remove = async (id: string) => { if (!confirm("Delete this declaration?")) return; await props.guard(() => api.del(`/api/v1/metadata/${id}`)); await props.refresh(); };
  return <section className="page"><PageHeader eyebrow="07 · Declared evidence" title="Purpose and retention metadata" description="DATAQUEST records declarations and their scope. It does not determine whether evidence is legally sufficient." actions={props.workspaceId ? <div className="button-row"><label className="file-button">Import CSV<input type="file" accept=".csv" onChange={e => e.target.files?.[0] && importCsv(e.target.files[0])} /></label><a className="secondary" href={`${API_BASE}/api/v1/workspaces/${props.workspaceId}/metadata/export`}>Export metadata CSV</a></div> : null} />
    {!props.workspaceId ? <NeedWorkspace /> : <div className="split-grid wide-left"><article className="panel table-panel"><h2>Declarations</h2>{props.metadata.length ? <table><thead><tr><th>Scope</th><th>Class</th><th>Purpose</th><th>Retention</th><th></th></tr></thead><tbody>{props.metadata.map(item => <tr key={item.id}><td>{item.field_name || item.object_name || (item.source_id ? "source" : "workspace")}</td><td>{item.class_key || "Any"}</td><td>{item.purpose_text || <StatusBadge value="missing" />}</td><td>{item.retention_duration || item.retention_basis || <StatusBadge value="missing" />}</td><td><button className="text-danger" onClick={() => remove(item.id)}>Delete</button></td></tr>)}</tbody></table> : <EmptyState title="No declarations" body="Add purpose or retention evidence at workspace, class, source, object, or field scope." />}</article>
    <article className="panel"><h2>Add declaration</h2><form className="stack" onSubmit={submit}><label>Source<select value={form.source_id} onChange={e => setForm({ ...form, source_id: e.target.value })}><option value="">Any source</option>{props.sources.map(s => <option value={s.id} key={s.id}>{s.display_name}</option>)}</select></label><div className="form-grid"><label>Object<input value={form.object_name} onChange={e => setForm({ ...form, object_name: e.target.value })} placeholder="tickets" /></label><label>Field<input value={form.field_name} onChange={e => setForm({ ...form, field_name: e.target.value })} placeholder="mobile" /></label></div><label>Class<select value={form.class_key} onChange={e => setForm({ ...form, class_key: e.target.value })}><option value="">Any class</option>{props.rules.map(r => <option key={r.class_key}>{r.class_key}</option>)}</select></label><label>Declared purpose<textarea value={form.purpose_text} onChange={e => setForm({ ...form, purpose_text: e.target.value })} /></label><div className="form-grid"><label>Retention duration<input value={form.retention_duration} onChange={e => setForm({ ...form, retention_duration: e.target.value })} /></label><label>Retention basis<input value={form.retention_basis} onChange={e => setForm({ ...form, retention_basis: e.target.value })} /></label></div><label>Owner label<input value={form.owner_label} onChange={e => setForm({ ...form, owner_label: e.target.value })} /></label><button className="primary" type="submit">Save declaration</button></form></article></div>}
  </section>;
}

function ReviewPage(props: Props) {
  const [filter, setFilter] = useState("needs_review"); const [notes, setNotes] = useState<Record<string, string>>({}); const [histories, setHistories] = useState<Record<string, { id: string; new_status: string; reviewer_label: string; note: string; created_at: string }[]>>({});
  const items = props.findings.filter(f => !filter || f.review_status === filter);
  const decide = async (finding: Finding, decision: string) => { const result = await props.guard(() => api.post(`/api/v1/findings/${finding.id}/review`, { decision, reviewer_label: "Local reviewer", note: notes[finding.id] ?? "" })); if (result) await props.refresh(); };
  const history = async (id: string) => { const result = await props.guard(() => api.get<Page<{ id: string; new_status: string; reviewer_label: string; note: string; created_at: string }>>(`/api/v1/findings/${id}/review-history`)); if (result) setHistories({ ...histories, [id]: result.items }); };
  return <section className="page"><PageHeader eyebrow="08 · Trust layer" title="Human review queue" description="Every decision creates a new append-only review event. Re-review never erases earlier history." />
    {!props.scanId ? <NeedScan /> : <><div className="filters"><label>Status<select value={filter} onChange={e => setFilter(e.target.value)}><option value="">All states</option><option>needs_review</option><option>review_later</option><option>accepted</option><option>rejected</option></select></label><span>{items.length} findings</span></div><div className="review-list">{items.map(f => <article className="panel review-card" key={f.id}><div><span className="class-chip">{f.class_key}</span><h2>{f.field_name}</h2><p>{f.source_name} / {f.object_name}</p><p className="muted">{f.explanation}</p><button className="secondary" onClick={() => history(f.id)}>Show review history</button>{histories[f.id] && <ol className="history-list">{histories[f.id].map(event => <li key={event.id}><strong>{event.new_status.replaceAll("_", " ")}</strong><span>{event.reviewer_label} · {new Date(event.created_at).toLocaleString()}</span><p>{event.note || "No note"}</p></li>)}</ol>}</div><div className="review-controls"><label>Reviewer note<textarea value={notes[f.id] ?? ""} onChange={e => setNotes({ ...notes, [f.id]: e.target.value })} placeholder="Reason for this decision" /></label><div><button onClick={() => decide(f, "accepted")} className="accept">Accept</button><button onClick={() => decide(f, "rejected")} className="reject">Reject</button><button onClick={() => decide(f, "review_later")} className="secondary">Review later</button></div></div></article>)}</div></>}
  </section>;
}

function EvaluationPage(props: Props) {
  const [labels, setLabels] = useState<{ dataset_key: string | null; labelled_count: number } | null>(null);
  const [labelFile, setLabelFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [labelStatusError, setLabelStatusError] = useState("");
  useEffect(() => {
    let active = true;
    setLabels(null);
    setLabelStatusError("");
    if (props.scanId) api.get<{ dataset_key: string | null; labelled_count: number }>(`/api/v1/scans/${props.scanId}/evaluation/labels`).then(value => { if (active) setLabels(value); }).catch(() => { if (active) setLabelStatusError("Could not load the labels for this scan. Check the backend connection and reopen Evaluation."); });
    return () => { active = false; };
  }, [props.scanId]);
  const uploadLabels = async () => {
    if (!props.scanId || !labelFile || uploading) return;
    setUploading(true);
    const result = await props.guard(() => api.upload<{ dataset_key: string; labelled_count: number }>(`/api/v1/scans/${props.scanId}/evaluation/labels`, [labelFile], "file"));
    if (result) { setLabels(result); setLabelStatusError(""); setLabelFile(null); props.setEvaluation(null); }
    setUploading(false);
  };
  const run = async () => { const result = await props.guard(() => api.post<Evaluation>(`/api/v1/scans/${props.scanId}/evaluation`)); if (result) props.setEvaluation(result); };
  return <section className="page"><PageHeader eyebrow="09 · Reproducible test" title="Evaluation" description="Metrics compare this scan's predictions with manual labels attached to this same scan—not with another dataset." actions={<button className="primary" disabled={!props.scanId || !labels?.labelled_count} onClick={run}>Run evaluation</button>} />
    {!props.scanId ? <NeedScan /> : <><div className="panel"><h2>Manual labels for this scan</h2><p>{labelStatusError || (labels ? labels.labelled_count ? `${labels.labelled_count} labelled fields loaded (${labels.dataset_key}).` : "No labels are attached to this scan. Metrics are unavailable until you upload matching labels." : "Checking labels for this scan...")}</p><p className="muted">The synthetic demo brings its own 19 labels. For your files, download this scan's template, fill each row with a positive class or negative / NONE, save as UTF-8 CSV, then upload it.</p><div className="button-row"><a className="secondary" href={`${API_BASE}/api/v1/scans/${props.scanId}/evaluation/labels-template`}>Download label template</a><label className="file-button">Choose label CSV<input type="file" accept=".csv" onChange={e => setLabelFile(e.target.files?.[0] ?? null)} /></label>{labelFile && <button className="primary" disabled={uploading} onClick={uploadLabels}>{uploading ? "Uploading labels..." : `Upload labels: ${labelFile.name}`}</button>}</div></div>{!props.evaluation ? <EmptyState title="Not evaluated" body={labels?.labelled_count ? "Select Run evaluation to calculate metrics from these labels." : "Upload matching manual labels to enable evaluation. No placeholder metrics are shown."} /> : <><div className="metric-grid"><div className="metric"><span>Labelled fields</span><strong>{props.evaluation.labelled_count}</strong></div></div><div className="panel table-panel"><table><thead><tr><th>Class</th><th>Precision</th><th>Recall</th><th>TP</th><th>FP</th><th>FN</th><th>TN</th><th>Support</th></tr></thead><tbody>{Object.entries(props.evaluation.per_class).map(([key, value]) => <tr key={key}><td><span className="class-chip">{key}</span></td><td>{formatMetric(value.precision)}</td><td>{formatMetric(value.recall)}</td><td>{value.tp}</td><td>{value.fp}</td><td>{value.fn}</td><td>{value.tn}</td><td>{value.support}</td></tr>)}</tbody></table></div><p className="disclaimer">{props.evaluation.caveat}</p></>}</>}
  </section>;
}

function ReportsPage(props: Props) {
  const exports = [["inventory_csv", "Inventory CSV"], ["footprints_json", "Footprints JSON"], ["footprints_csv", "Footprints CSV"], ["evidence_gaps_csv", "Evidence gaps CSV"], ["review_history_csv", "Review history CSV"], ["metrics_json", "Metrics JSON"], ["metrics_csv", "Metrics CSV"], ["report_md", "Report Markdown"], ["report_html", "Report HTML"]];
  return <section className="page"><PageHeader eyebrow="10 · Safe outputs" title="Reports and export" description="Exports contain masked samples and redacted evidence only. Raw values and internal fingerprints are excluded." />
    {!props.scanId ? <NeedScan /> : <div className="export-grid">{exports.map(([type, label]) => <a key={type} className="export-card" href={`${API_BASE}/api/v1/scans/${props.scanId}/exports/${type}`}><span>{label}</span><small>Download local artifact</small><b>↓</b></a>)}</div>}
  </section>;
}

function RulesPage(props: Props) {
  const update = (index: number, changes: Partial<Rule>) => props.setRules(props.rules.map((r, i) => i === index ? { ...r, ...changes } : r));
  const save = async () => { const result = await props.guard(() => api.put<{ items: Rule[] }>("/api/v1/rules", props.rules)); if (result) props.setRules(result.items); };
  const restore = async () => { if (!confirm("Restore the five prototype defaults?")) return; const result = await props.guard(() => api.post<{ items: Rule[] }>("/api/v1/rules/restore-defaults?confirm=true")); if (result) props.setRules(result.items); };
  return <section className="page"><PageHeader eyebrow="11 · Prototype defaults" title="Configurable detection rules" description="The presentation specifies five classes but does not name them. These editable classes are prototype implementation decisions." actions={<div className="button-row"><button className="secondary" onClick={restore}>Restore defaults</button><button className="primary" onClick={save}>Save new version</button></div>} />
    <div className="rule-list">{props.rules.map((rule, index) => <article className="panel rule-card" key={rule.class_key}><div className="rule-title"><div><span className="class-chip">{rule.class_key}</span><h2>{rule.display_name}</h2></div><label className="toggle"><input type="checkbox" checked={rule.enabled} onChange={e => update(index, { enabled: e.target.checked })} /><span>Enabled</span></label></div><div className="form-grid"><label>Aliases<textarea value={rule.field_aliases.join(", ")} onChange={e => update(index, { field_aliases: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })} /></label><label>Patterns (name::regex)<textarea value={rule.patterns.map(p => `${p.name}::${p.regex}`).join("\n")} onChange={e => update(index, { patterns: e.target.value.split("\n").filter(Boolean).map(line => { const split = line.indexOf("::"); return { name: split >= 0 ? line.slice(0, split) : "pattern", regex: split >= 0 ? line.slice(split + 2) : line }; }) })} /></label></div><div className="form-grid four"><label>Name weight<input type="number" min="0" max="1" step="0.05" value={rule.field_name_weight} onChange={e => update(index, { field_name_weight: Number(e.target.value) })} /></label><label>Pattern weight<input type="number" min="0" max="1" step="0.05" value={rule.pattern_weight} onChange={e => update(index, { pattern_weight: Number(e.target.value) })} /></label><label>Type weight<input type="number" min="0" max="1" step="0.05" value={rule.type_weight} onChange={e => update(index, { type_weight: Number(e.target.value) })} /></label><label>Threshold<input type="number" min="0" max="1" step="0.05" value={rule.threshold} onChange={e => update(index, { threshold: Number(e.target.value) })} /></label></div><label>Notes<input value={rule.notes} onChange={e => update(index, { notes: e.target.value })} /></label></article>)}</div>
  </section>;
}

function PrivacyPage(props: Props) {
  const remove = async () => { if (!props.workspaceId || !confirm("Delete this workspace, its copied uploads, scan results, review events, and audit history? Original files remain untouched.")) return; const result = await props.guard(() => api.del<{ deleted: boolean }>(`/api/v1/workspaces/${props.workspaceId}?confirm=true`)); if (result?.deleted) { props.chooseWorkspace(""); localStorage.clear(); location.hash = "welcome"; await props.refresh(); } };
  return <section className="page"><PageHeader eyebrow="12 · Local safeguards" title="Privacy and settings" description="The prototype minimizes exposure while keeping its limitations explicit." />
    <div className="privacy-grid"><article className="panel"><h2>Processing boundary</h2><p>The API binds to <code>127.0.0.1</code> and accepts the local Vite origins only. The production code includes no external AI, telemetry, analytics, remote logging, remote fonts, or CDN calls.</p><dl className="detail-list"><div><dt>API</dt><dd>{API_BASE}</dd></div><div><dt>Version</dt><dd>{props.health?.version ?? "Unavailable"}</dd></div><div><dt>Local-only flag</dt><dd>{String(props.health?.local_only ?? false)}</dd></div></dl></article><article className="panel"><h2>Storage and masking</h2><p>Uploaded files are copied into backend local storage. Profiles and findings keep masked samples. The results database does not store raw candidate values. Overlap grouping uses a random scan-lifetime HMAC secret.</p></article><article className="panel"><h2>Boundaries</h2><p>The tool uses heuristics and cannot guarantee discovery. Equal normalized values indicate a potential overlap, not identity. Metadata records declarations, not legal sufficiency. This prototype has not undergone a security audit.</p></article><article className="panel danger-zone"><h2>Delete workspace</h2><p>Removes copied uploads and workspace-owned records. Original source files stay untouched.</p><button className="danger" disabled={!props.workspaceId} onClick={remove}>Delete selected workspace</button></article></div>
  </section>;
}

function NeedWorkspace() { return <EmptyState title="Choose a workspace first" body="Open Workspace from the navigation, then create a workspace or load the synthetic demo." />; }
function NeedScan() { return <EmptyState title="No active scan" body="Register sources and run a scan, or load the synthetic demo workspace." />; }
function formatMetric(value: number | null) { return value === null ? "N/A" : `${(value * 100).toFixed(1)}%`; }

export default App;
