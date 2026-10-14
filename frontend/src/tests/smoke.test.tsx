import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";

const json = (data: unknown) => Promise.resolve({ ok: true, json: () => Promise.resolve(data) } as Response);

describe("DATAQUEST app", () => {
  beforeEach(() => {
    location.hash = "#welcome";
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/health")) return json({ status: "ok", version: "1.0.0", local_only: true });
      if (url.endsWith("/api/v1/workspaces")) return json({ items: [], total: 0 });
      if (url.endsWith("/api/v1/rules")) return json({ items: [], version: "test" });
      return json({ items: [], total: 0 });
    }));
  });

  it("renders the local-only welcome journey", async () => {
    render(<App />);
    expect(await screen.findByText("Personal data discovery with an evidence trail")).toBeInTheDocument();
    expect(screen.getByText("Local processing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load synthetic demo workspace" })).toBeEnabled();
  });

  it("navigates to privacy guidance", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Read the privacy model"));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Privacy and settings" })).toBeInTheDocument());
    expect(screen.getByText(/no external AI, telemetry/i)).toBeInTheDocument();
  });
});
