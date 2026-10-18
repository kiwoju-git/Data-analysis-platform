export interface SourceContextToken<Source> {
  readonly epoch: number;
  readonly source: Source;
}

export interface SourceContextGuard<Source> {
  capture: () => SourceContextToken<Source>;
  advance: (source: Source) => SourceContextToken<Source>;
  isCurrent: (token: SourceContextToken<Source>) => boolean;
  dispose: () => void;
  isDisposed: () => boolean;
}

/** Compose with a latest-request lane to reject obsolete source completions, including A-B-A. */
export function createSourceContextGuard<Source>(initialSource: Source): SourceContextGuard<Source> {
  let current: SourceContextToken<Source> = Object.freeze({ epoch: 0, source: initialSource });
  let disposed = false;
  return {
    capture: () => current,
    advance: (source) => {
      if (disposed) throw new Error("source_context_disposed");
      current = Object.freeze({ epoch: current.epoch + 1, source });
      return current;
    },
    isCurrent: (token) => !disposed && token === current,
    dispose: () => { disposed = true; },
    isDisposed: () => disposed,
  };
}
