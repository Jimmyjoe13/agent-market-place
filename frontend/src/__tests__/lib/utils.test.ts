/**
 * Utils Tests
 * =============
 *
 * Tests unitaires pour les fonctions utilitaires.
 */

import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (classnames utility)", () => {
  it("merges class names correctly", () => {
    expect(cn("foo", "bar")).toBe("foo bar");
  });

  it("handles conditional classes", () => {
    const isActive = true;
    const isDisabled = false;

    expect(cn("base", isActive && "active", isDisabled && "disabled")).toBe(
      "base active"
    );
  });

  it("handles array of classes", () => {
    expect(cn(["foo", "bar"], "baz")).toBe("foo bar baz");
  });

  it("handles object notation", () => {
    expect(cn({ foo: true, bar: false, baz: true })).toBe("foo baz");
  });

  it("handles undefined and null values", () => {
    expect(cn("foo", undefined, null, "bar")).toBe("foo bar");
  });

  it("merges Tailwind classes correctly", () => {
    // twMerge should handle conflicting Tailwind classes
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
    expect(cn("text-red-500", "text-blue-500")).toBe("text-blue-500");
  });

  it("handles empty input", () => {
    expect(cn()).toBe("");
    expect(cn("")).toBe("");
  });

  it("works with complex combinations", () => {
    const result = cn(
      "base-class",
      {
        "conditional-true": true,
        "conditional-false": false,
      },
      ["array-class-1", "array-class-2"],
      "final-class"
    );

    expect(result).toContain("base-class");
    expect(result).toContain("conditional-true");
    expect(result).not.toContain("conditional-false");
    expect(result).toContain("array-class-1");
    expect(result).toContain("array-class-2");
    expect(result).toContain("final-class");
  });
});
