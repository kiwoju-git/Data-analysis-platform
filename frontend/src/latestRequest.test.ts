import { describe, expect, it } from "vitest";

import { createLatestRequestGuard } from "./latestRequest";

describe("createLatestRequestGuard", () => {
  it("accepts only the most recently started request", () => {
    const guard = createLatestRequestGuard();
    const first = guard.begin();
    const second = guard.begin();

    expect(guard.isCurrent(first)).toBe(false);
    expect(guard.isCurrent(second)).toBe(true);
  });

  it("invalidates in-flight work without cancelling a newer request", () => {
    const guard = createLatestRequestGuard();
    const first = guard.begin();
    const second = guard.begin();

    guard.cancel(first);
    expect(guard.isCurrent(second)).toBe(true);

    guard.cancel();
    expect(guard.isCurrent(second)).toBe(false);
  });

  it("ignores an older response and its loading cleanup when requests finish out of order", async () => {
    const guard = createLatestRequestGuard();
    const state = { isLoading: false, value: "" };
    let resolveFirst: (value: string) => void = () => undefined;
    let resolveSecond: (value: string) => void = () => undefined;
    const firstResponse = new Promise<string>((resolve) => {
      resolveFirst = resolve;
    });
    const secondResponse = new Promise<string>((resolve) => {
      resolveSecond = resolve;
    });

    async function run(response: Promise<string>) {
      const request = guard.begin();
      state.isLoading = true;
      try {
        const value = await response;
        if (guard.isCurrent(request)) {
          state.value = value;
        }
      } finally {
        if (guard.isCurrent(request)) {
          state.isLoading = false;
        }
      }
    }

    const firstRun = run(firstResponse);
    const secondRun = run(secondResponse);
    resolveFirst("obsolete");
    await firstRun;

    expect(state).toEqual({ isLoading: true, value: "" });

    resolveSecond("latest");
    await secondRun;
    expect(state).toEqual({ isLoading: false, value: "latest" });
  });

  it("keeps reset state after an invalidated request resolves", async () => {
    const guard = createLatestRequestGuard();
    const state = { isLoading: false, value: "reset" };
    let resolveResponse: (value: string) => void = () => undefined;
    const response = new Promise<string>((resolve) => {
      resolveResponse = resolve;
    });
    const request = guard.begin();
    state.isLoading = true;
    const run = response
      .then((value) => {
        if (guard.isCurrent(request)) {
          state.value = value;
        }
      })
      .finally(() => {
        if (guard.isCurrent(request)) {
          state.isLoading = false;
        }
      });

    guard.cancel();
    state.isLoading = false;
    state.value = "reset";
    resolveResponse("late");
    await run;

    expect(state).toEqual({ isLoading: false, value: "reset" });
  });
});
