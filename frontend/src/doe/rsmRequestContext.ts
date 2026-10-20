import { createLatestRequestGuard } from "../latestRequest";
import { createSourceContextGuard, type SourceContextToken } from "../sourceContextGuard";

export type RsmRequestLane = "create" | "save" | "analyze" | "history" | "plot" | "restore";
interface RsmRequest<Snapshot> {
  readonly lane: RsmRequestLane;
  readonly token: symbol;
  readonly source: SourceContextToken<null>;
  readonly snapshot: Snapshot;
}

/** Source edits invalidate every lane; view changes invalidate only the plot lane. */
export function createRsmRequestContext() {
  const source = createSourceContextGuard(null);
  const lanes = Object.fromEntries(
    (["create", "save", "analyze", "history", "plot", "restore"] as const)
      .map((lane) => [lane, createLatestRequestGuard()]),
  ) as Record<RsmRequestLane, ReturnType<typeof createLatestRequestGuard>>;
  return {
    begin<Snapshot>(lane: RsmRequestLane, snapshot: Snapshot): RsmRequest<Snapshot> {
      return { lane, token: lanes[lane].begin(), source: source.capture(), snapshot };
    },
    isCurrent(request: RsmRequest<unknown>) {
      return source.isCurrent(request.source) && lanes[request.lane].isCurrent(request.token);
    },
    invalidate() { source.advance(null); },
    invalidateLane(lane: RsmRequestLane) { lanes[lane].cancel(); },
  };
}
