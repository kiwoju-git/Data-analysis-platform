interface RetryingRequestOptions<T> {
  request: (signal: AbortSignal) => Promise<T>;
  onSuccess: (value: T) => void;
  onError: () => void;
  retryDelayMs?: number;
}

export function startRetryingRequest<T>({
  request,
  onSuccess,
  onError,
  retryDelayMs = 1500,
}: RetryingRequestOptions<T>): () => void {
  let cancelled = false;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let controller: AbortController | null = null;

  const run = () => {
    controller = new AbortController();
    request(controller.signal)
      .then((value) => {
        if (!cancelled) {
          onSuccess(value);
        }
      })
      .catch(() => {
        if (cancelled || controller?.signal.aborted) {
          return;
        }
        onError();
        retryTimer = setTimeout(run, retryDelayMs);
      });
  };

  run();
  return () => {
    cancelled = true;
    controller?.abort();
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
    }
  };
}
