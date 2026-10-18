import { describe, expect, it } from "vitest";

import { createLatestRequestGuard } from "./latestRequest";
import { createSourceContextGuard } from "./sourceContextGuard";

describe("source context guard", () => {
  it("invalidates an older epoch even when the source returns to the same identity", () => {
    const guard = createSourceContextGuard("a");
    const firstA = guard.capture();
    guard.advance("b");
    const lastA = guard.advance("a");
    expect(lastA.source).toBe(firstA.source);
    expect(lastA.epoch).toBe(2);
    expect(guard.isCurrent(firstA)).toBe(false);
    expect(guard.isCurrent(lastA)).toBe(true);
  });

  it("invalidates an outstanding write when a new draft keeps the same committed source", () => {
    const source = { versionId: "a", schemaHash: "schema-a" } as const;
    const guard = createSourceContextGuard(source);
    const prior = guard.capture();
    const next = guard.advance(source);
    expect(next.source).toBe(source);
    expect(guard.isCurrent(prior)).toBe(false);
  });

  it("does not let one read lane supersede another", () => {
    const source = createSourceContextGuard("a");
    const token = source.capture();
    const preview = createLatestRequestGuard();
    const profile = createLatestRequestGuard();
    const firstPreview = preview.begin();
    const firstProfile = profile.begin();
    preview.begin();
    expect(preview.isCurrent(firstPreview)).toBe(false);
    expect(profile.isCurrent(firstProfile) && source.isCurrent(token)).toBe(true);
    source.advance("b");
    expect(profile.isCurrent(firstProfile) && source.isCurrent(token)).toBe(false);
  });

  it("rejects another guard's token and fabricated copies", () => {
    const first = createSourceContextGuard("a");
    const second = createSourceContextGuard("a");
    expect(first.isCurrent(second.capture())).toBe(false);
    expect(first.isCurrent({ ...first.capture() })).toBe(false);
  });

  it("disposes outstanding work and cannot reactivate an old guard", () => {
    const guard = createSourceContextGuard("a");
    const token = guard.capture();
    guard.dispose();
    expect(guard.isCurrent(token)).toBe(false);
    expect(guard.isDisposed()).toBe(true);
    expect(() => guard.advance("b")).toThrow("source_context_disposed");
  });

  it("does not mutate previous token metadata", () => {
    const guard = createSourceContextGuard<string | null>(null);
    const token = guard.capture();
    guard.advance("a");
    expect(token).toEqual({ epoch: 0, source: null });
    expect(Object.isFrozen(token)).toBe(true);
  });
});
