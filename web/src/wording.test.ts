import { describe, it, expect } from "vitest";

const files = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/.*$/gm, "");
}

const BANNED = [/diagnos/i, /suffers from/i, /has delirium/i, /has dementia/i];

describe("product wording", () => {
  it("never uses banned diagnosis wording in non-test source", () => {
    const violations: string[] = [];

    for (const [path, src] of Object.entries(files)) {
      if (path.includes(".test.")) continue;
      if (path.endsWith("contracts.ts")) continue;

      const stripped = stripComments(src);
      const lines = stripped.split("\n");

      lines.forEach((line, idx) => {
        if (BANNED.some((re) => re.test(line))) {
          violations.push(`${path}:${idx + 1}: ${line.trim()}`);
        }
      });
    }

    expect(violations).toEqual([]);
  });
});
