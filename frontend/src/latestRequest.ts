export interface LatestRequestGuard {
  begin: () => symbol;
  cancel: (request?: symbol) => void;
  isCurrent: (request: symbol) => boolean;
}

export function createLatestRequestGuard(): LatestRequestGuard {
  let currentRequest: symbol | null = null;

  return {
    begin() {
      currentRequest = Symbol("latest-request");
      return currentRequest;
    },
    cancel(request) {
      if (request === undefined || currentRequest === request) {
        currentRequest = null;
      }
    },
    isCurrent(request) {
      return currentRequest === request;
    },
  };
}
