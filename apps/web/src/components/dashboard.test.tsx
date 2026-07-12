import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./dashboard";

const CASE = {
  id: "case-ar-1",
  reference: "OPS-2026-ABC123",
  title: "طلب صلاحية مؤقتة",
  description: "نحتاج صلاحية دخول مؤقتة إلى حساب التقارير لمدة أسبوع.",
  requester: "فريق العمليات",
  language: "ar",
  category: null,
  priority: null,
  status: "new",
  created_at: "2026-07-10T12:00:00Z",
  updated_at: "2026-07-10T12:00:00Z",
  latest_analysis: null,
};

class FakeWebSocket {
  static OPEN = 1;
  readyState = FakeWebSocket.OPEN;
  onopen: (() => void) | null = null;
  onmessage: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor() {
    window.setTimeout(() => this.onopen?.(), 0);
  }

  send() {}
  close() {}
}

function jsonResponse(value: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(value), { status: 200, headers: { "Content-Type": "application/json" } }),
  );
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeWebSocket);
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url.endsWith("/api/cases")) return jsonResponse([CASE]);
      if (url.endsWith("/api/analytics")) {
        return jsonResponse({
          total: 1,
          by_status: { new: 1 },
          by_priority: { untriaged: 1 },
          by_category: { untriaged: 1 },
          high_risk_open: 0,
          average_confidence: 0,
        });
      }
      if (url.endsWith("/audit/verify")) {
        return jsonResponse({ valid: true, event_count: 1, first_invalid_event_id: null });
      }
      if (url.endsWith("/audit")) {
        return jsonResponse([
          {
            id: "audit-1",
            case_id: CASE.id,
            sequence: 1,
            event_type: "case.created",
            actor: CASE.requester,
            payload: {},
            previous_hash: "",
            event_hash: "abc123",
            created_at: CASE.created_at,
          },
        ]);
      }
      throw new Error(`Unhandled test request: ${url}`);
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("Dashboard", () => {
  it("renders Arabic case content RTL and verifies the audit chain", async () => {
    render(<Dashboard />);

    expect(screen.getByRole("heading", { name: "Context before conclusions." })).toBeInTheDocument();
    const heading = await screen.findByRole("heading", { name: CASE.title });
    expect(heading).toHaveAttribute("dir", "rtl");
    await waitFor(() => expect(screen.getByText("1 events verified")).toBeInTheDocument());
    expect(screen.getByText("#1 · Case Created")).toBeInTheDocument();
  });

  it("switches intake fields to RTL when Arabic is selected", async () => {
    render(<Dashboard />);
    await screen.findByRole("heading", { name: CASE.title });

    fireEvent.click(screen.getByRole("button", { name: "New request" }));
    expect(screen.getByLabelText("Title")).toHaveFocus();
    fireEvent.change(screen.getByLabelText("Language"), { target: { value: "ar" } });

    expect(screen.getByLabelText("Title")).toHaveAttribute("dir", "rtl");
    expect(screen.getByLabelText("Description")).toHaveAttribute("dir", "rtl");
    expect(screen.getByLabelText("Requester")).toHaveAttribute("dir", "rtl");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Create a request" })).not.toBeInTheDocument();
  });

  it("makes queue search and review filters explicit", async () => {
    render(<Dashboard />);
    await screen.findByRole("heading", { name: CASE.title });

    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.change(screen.getByRole("textbox", { name: "Search requests" }), { target: { value: "missing request" } });
    expect(screen.getByText("No matching requests")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Search requests" }), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByRole("button", { name: "Open" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: new RegExp(CASE.reference) })).toHaveAttribute("aria-current", "true");
  });
});
