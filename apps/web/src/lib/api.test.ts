import { afterEach, describe, expect, it, vi } from "vitest";

import { api, websocketUrl } from "./api";


afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});


describe("API client", () => {
  it("loads cases from the configured backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.listCases()).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/cases",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  it("turns FastAPI validation details into a readable message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ detail: [{ msg: "Title is too short" }, { msg: "Description is required" }] }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(api.createCase({ title: "x", description: "", requester: "QA", language: "en" }))
      .rejects.toThrow("Title is too short; Description is required");
  });

  it("derives the WebSocket URL from the API origin", () => {
    expect(websocketUrl()).toBe("ws://localhost:8000/ws/events");
  });
});
