import { describe, it, expect } from "vitest";

const files = import.meta.glob("./**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/** Comments are documentation, not copy, so they are blanked rather than cut: the
 * line numbers in a violation still point at the line to fix. */
function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, (block) => block.replace(/[^\n]/g, " "))
    .replace(/\/\/.*$/gm, "");
}

/** Never, anywhere: the product flags a change for review, and the people it
 * watches are people, not patients (SPEC sections 7.5 and 17). */
const BANNED = [
  /diagnos/i,
  /suffers from/i,
  /has delirium/i,
  /has dementia/i,
  /patient/i,
];

/** The only "nurse" the code may keep: the one that names the care-home supervisor
 * specifically (SPEC section 17). A nurse on a unit is one kind of supervisor, so
 * everywhere else the wording has to work for someone watching their own routine,
 * their family or a carer — "person", or the person's name.
 *
 * Each entry is the care-home-specific string itself; they are cut out of the line
 * before it is checked, so a line that also says "nurse" about anything else still
 * fails. Most specific first: the shorter patterns are inside the longer ones. */
const CARE_HOME_NURSE = [
  /nurse: 'Nurse'/g, // people/MyRoutine.tsx: the label for that relationship
  /'Nurse Ana'/g, // mock/people.ts: the demo's care-home supervisor (SPEC section 17)
  /'nurse-ana'/g, // ...her id, and the unit she is linked to
  /'nurse'/g, // people/types.ts' Relationship, and the `by` the pipeline writes
];

function withoutCareHomeNurse(line: string): string {
  return CARE_HOME_NURSE.reduce((rest, allowed) => rest.replace(allowed, ""), line);
}

function sourceLines(): { path: string; line: string; number: number }[] {
  const lines: { path: string; line: string; number: number }[] = [];
  for (const [path, src] of Object.entries(files)) {
    if (path.includes(".test.")) continue;
    if (path.endsWith("contracts.ts")) continue;

    stripComments(src)
      .split("\n")
      .forEach((line, idx) => lines.push({ path, line, number: idx + 1 }));
  }
  return lines;
}

describe("product wording", () => {
  it("never uses banned diagnosis or patient wording in non-test source", () => {
    const violations = sourceLines()
      .filter(({ line }) => BANNED.some((re) => re.test(line)))
      .map(({ path, line, number }) => `${path}:${number}: ${line.trim()}`);

    expect(violations).toEqual([]);
  });

  it('only says "nurse" where it means the care-home supervisor', () => {
    const violations = sourceLines()
      .filter(({ line }) => /nurse/i.test(withoutCareHomeNurse(line)))
      .map(({ path, line, number }) => `${path}:${number}: ${line.trim()}`);

    expect(violations).toEqual([]);
  });

  it("keeps the care-home allow-list to the strings it is for", () => {
    /* The allow-list exists for the relationship and the demo persona, not as a way
       to smuggle a sentence about nurses past the rule above. */
    expect(withoutCareHomeNurse("  nurse: 'Nurse',")).not.toMatch(/nurse/i);
    expect(withoutCareHomeNurse("{ id: 'nurse-ana', name: 'Nurse Ana' }")).not.toMatch(/nurse/i);
    expect(withoutCareHomeNurse("export type Relationship = 'family' | 'carer' | 'nurse'")).not.toMatch(
      /nurse/i,
    );
    expect(withoutCareHomeNurse("const TITLE = 'What nurses said'")).toMatch(/nurse/i);
    expect(withoutCareHomeNurse("flagged for a nurse to review")).toMatch(/nurse/i);
    expect(withoutCareHomeNurse("{ relationship: 'nurse', hint: 'ask the nurse' }")).toMatch(
      /nurse/i,
    );
  });
});
