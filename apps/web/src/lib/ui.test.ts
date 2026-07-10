import { describe, expect, it } from "vitest";
import { formatDate, priorityMeta, titleCase } from "./ui";


describe("UI formatting", () => {
  it("maps priorities to accessible labels", () => {
    expect(priorityMeta.critical.label).toBe("Critical");
    expect(priorityMeta.low.className).toContain("badge-low");
  });

  it("formats event names for audit history", () => {
    expect(titleCase("case.approved")).toBe("Case Approved");
  });

  it("returns a human-readable date", () => {
    expect(formatDate("2026-07-10T10:30:00Z")).toMatch(/Jul/);
  });
});
