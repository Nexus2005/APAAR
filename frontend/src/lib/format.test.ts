import { describe, expect, it } from "vitest";
import { dateLabel, initials, num, pct, titleCase } from "./format";

describe("format helpers", () => {
  it("formats percentages and falls back safely", () => {
    expect(pct(91.24, 1)).toBe("91.2%");
    expect(pct(null)).toBe("—");
  });

  it("formats Indian numbering", () => {
    expect(num(1652)).toBe("1,652");
    expect(num(undefined)).toBe("—");
  });

  it("derives initials from display names", () => {
    expect(initials("Ananya Kulkarni")).toBe("AK");
    expect(initials(null)).toBe("?");
  });

  it("labels dates and titles rule codes", () => {
    expect(titleCase("intake_exceeded")).toBe("Intake Exceeded");
    expect(dateLabel("2026-06-01")).toContain("2026");
  });
});
