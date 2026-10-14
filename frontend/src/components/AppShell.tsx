import type { ReactNode } from "react";
import { API_BASE } from "../api/client";

export const NAV = [
  ["welcome", "Workspace"], ["sources", "Sources"], ["scan", "Scan"], ["dashboard", "Overview"],
  ["inventory", "Inventory"], ["footprint", "Footprint"], ["metadata", "Metadata"], ["review", "Review"],
  ["evaluation", "Evaluation"], ["reports", "Reports"], ["rules", "Rules"], ["privacy", "Privacy"]
] as const;

export function AppShell({ page, children }: { page: string; children: ReactNode }) {
  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#welcome" aria-label="DATAQUEST home"><span className="brand-mark">DQ</span><span><strong>DATAQUEST</strong><small>Privacy evidence inventory</small></span></a>
      <nav aria-label="Primary navigation">
        {NAV.map(([key, label], index) => <a key={key} href={`#${key}`} className={page === key ? "active" : ""}><span>{String(index + 1).padStart(2, "0")}</span>{label}</a>)}
      </nav>
      <div className="local-panel"><span className="pulse" /> Local processing<strong>{API_BASE}</strong></div>
    </aside>
    <main>{children}</main>
  </div>;
}

export function StatusBadge({ value }: { value: string }) {
  const safe = value?.toLowerCase().replace(/[^a-z]+/g, "-") || "unknown";
  return <span className={`status status-${safe}`}>{value?.replaceAll("_", " ")}</span>;
}

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow: string; title: string; description: string; actions?: ReactNode }) {
  return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{actions && <div className="header-actions">{actions}</div>}</header>;
}

export function EmptyState({ title, body }: { title: string; body: string }) {
  return <div className="empty"><div className="empty-icon">◇</div><h3>{title}</h3><p>{body}</p></div>;
}
