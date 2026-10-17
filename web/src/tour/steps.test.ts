import { describe, it, expect } from "vitest";
import { TOUR_STEPS } from "./steps";

const BANNED = /diagnos|\bhas (delirium|dementia|a stroke)\b|treatment/i;

describe("guided tour copy", () => {
  it("never uses diagnosis wording and has non-empty title/body", () => {
    for (const step of TOUR_STEPS) {
      expect(step.title.length).toBeGreaterThan(0);
      expect(step.body.length).toBeGreaterThan(0);
      expect(step.title).not.toMatch(BANNED);
      expect(step.body).not.toMatch(BANNED);
    }
  });

  it("at least one step flags a change for review", () => {
    expect(TOUR_STEPS.some((s) => s.body.includes("flags a change for review"))).toBe(true);
  });
});
