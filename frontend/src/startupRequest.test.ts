import { afterEach, describe, expect, it, vi } from "vitest";

import { startRetryingRequest } from "./startupRequest";

describe("startRetryingRequest", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("recovers when the backend becomes ready after the first request", async () => {
    vi.useFakeTimers();
    const request = vi
      .fn<(signal: AbortSignal) => Promise<string>>()
      .mockRejectedValueOnce(new Error("not ready"))
      .mockResolvedValueOnce("ready");
    const onSuccess = vi.fn();
    const onError = vi.fn();

    const cancel = startRetryingRequest({ request, onSuccess, onError, retryDelayMs: 100 });
    await vi.advanceTimersByTimeAsync(0);
    expect(onError).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(100);
    expect(request).toHaveBeenCalledTimes(2);
    expect(onSuccess).toHaveBeenCalledWith("ready");
    cancel();
  });

  it("aborts the active request and prevents retries after cancellation", async () => {
    vi.useFakeTimers();
    const request = vi.fn<(signal: AbortSignal) => Promise<never>>(() => {
      return Promise.reject(new Error("not ready"));
    });
    const onSuccess = vi.fn();
    const onError = vi.fn();

    const cancel = startRetryingRequest({ request, onSuccess, onError, retryDelayMs: 100 });
    cancel();
    await Promise.resolve();
    await vi.advanceTimersByTimeAsync(100);

    expect(request.mock.calls[0]?.[0].aborted).toBe(true);
    expect(request).toHaveBeenCalledTimes(1);
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onError).not.toHaveBeenCalled();
  });
});
