import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

const ok = (data: unknown) => Promise.resolve({ ok: true, json: () => Promise.resolve(data) } as Response);
const source = { id: "s1", workspace_id: "w1", display_name: "contacts.csv", source_type: "csv", file_size_bytes: 80, status: "ready" };
const workspace = { id: "w1", name: "My upload", created_at: "2026-10-14T00:00:00Z", status: "active" };
const summary = { source_count: 1, successful_source_count: 1, object_count: 1, profiled_field_count: 2, finding_count: 1, footprint_count: 0, failed_sources: [] };

describe("uploaded-source scan interaction", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("dq_workspace", "w1");
    location.hash = "#scan";
  });

  it("shows that the click started a scan and loads its result", async () => {
    let finishScan: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return ok({ status: "ok", version: "1.0.0", local_only: true });
      if (url.endsWith("/api/v1/workspaces")) return ok({ items: [workspace], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/sources")) return ok({ items: [source], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/metadata")) return ok({ items: [], total: 0 });
      if (url.endsWith("/api/v1/rules")) return ok({ items: [], version: "default-1" });
      if (url.endsWith("/api/v1/workspaces/w1/scans") && init?.method === "POST") {
        return new Promise<Response>(resolve => { finishScan = resolve; });
      }
      if (url.endsWith("/api/v1/scans/scan-1")) return ok({ id: "scan-1", status: "completed", stage: "persist", summary });
      if (url.includes("/api/v1/scans/scan-1/")) return ok({ items: [], total: 0 });
      return ok({ items: [], total: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    const button = await screen.findByRole("button", { name: "Start local scan" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(screen.getByRole("button", { name: "Scanning selected sources..." })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("The local scan is running");
    expect(finishScan).toBeTypeOf("function");
    finishScan!({ ok: true, json: () => Promise.resolve({ id: "scan-1", status: "completed", summary }) } as Response);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Overview" })).toBeInTheDocument());
    expect(localStorage.getItem("dq_scan")).toBe("scan-1");
    expect(screen.getByText("Profiled fields")).toBeInTheDocument();
  });

  it("puts a lost-backend message beside the scan button", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return ok({ status: "ok", version: "1.0.0", local_only: true });
      if (url.endsWith("/api/v1/workspaces")) return ok({ items: [workspace], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/sources")) return ok({ items: [source], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/metadata")) return ok({ items: [], total: 0 });
      if (url.endsWith("/api/v1/rules")) return ok({ items: [], version: "default-1" });
      if (url.endsWith("/api/v1/workspaces/w1/scans") && init?.method === "POST") return Promise.reject(new TypeError("Failed to fetch"));
      return ok({ items: [], total: 0 });
    }));
    render(<App />);
    const button = await screen.findByRole("button", { name: "Start local scan" });
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    await waitFor(() => expect(screen.getAllByText(/Cannot reach the local DATAQUEST backend/).length).toBeGreaterThan(0));
    await waitFor(() => expect(screen.getByRole("button", { name: "Start local scan" })).toBeEnabled());
  });

  it("offers file upload directly on the scan page and selects an uploaded source", async () => {
    let uploaded = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return ok({ status: "ok", version: "1.0.0", local_only: true });
      if (url.endsWith("/api/v1/workspaces")) return ok({ items: [workspace], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/sources") && init?.method === "POST") {
        uploaded = true;
        return ok({ items: [source], total: 1 });
      }
      if (url.endsWith("/api/v1/workspaces/w1/sources")) return ok({ items: uploaded ? [source] : [], total: uploaded ? 1 : 0 });
      if (url.endsWith("/api/v1/workspaces/w1/metadata")) return ok({ items: [], total: 0 });
      if (url.endsWith("/api/v1/rules")) return ok({ items: [], version: "default-1" });
      return ok({ items: [], total: 0 });
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    const chooser = await screen.findByLabelText("Choose CSV or SQLite files");
    fireEvent.change(chooser, { target: { files: [new File(["id,email\n1,a@example.com"], "contacts.csv", { type: "text/csv" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Upload copies" }));
    await waitFor(() => expect(screen.getByText("contacts.csv")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByRole("button", { name: "Start local scan" })).toBeEnabled());
  });

  it("requires custom scan labels before enabling evaluation", async () => {
    location.hash = "#evaluation";
    localStorage.setItem("dq_scan", "scan-1");
    let labelCount = 0;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return ok({ status: "ok", version: "1.0.0", local_only: true });
      if (url.endsWith("/api/v1/workspaces")) return ok({ items: [workspace], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/sources")) return ok({ items: [source], total: 1 });
      if (url.endsWith("/api/v1/workspaces/w1/metadata")) return ok({ items: [], total: 0 });
      if (url.endsWith("/api/v1/rules")) return ok({ items: [], version: "default-1" });
      if (url.endsWith("/api/v1/scans/scan-1/evaluation/labels") && init?.method === "POST") {
        labelCount = 1;
        return ok({ dataset_key: "mine", labelled_count: 1 });
      }
      if (url.endsWith("/api/v1/scans/scan-1/evaluation/labels")) return ok({ dataset_key: null, labelled_count: labelCount });
      if (url.endsWith("/api/v1/scans/scan-1")) return ok({ id: "scan-1", status: "completed", stage: "persist", summary });
      return ok({ items: [], total: 0 });
    }));
    render(<App />);
    expect(await screen.findByText(/No labels are attached to this scan/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run evaluation" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Choose label CSV"), { target: { files: [new File(["dataset_key,source_name"], "labels.csv", { type: "text/csv" })] } });
    fireEvent.click(screen.getByRole("button", { name: /Upload labels:/ }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run evaluation" })).toBeEnabled());
  });
});
