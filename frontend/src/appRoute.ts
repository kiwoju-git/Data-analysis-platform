import { parseAnalysisLocation, type AnalysisSelection } from "./analysisNavigation";

export type AppRoute =
  | {
      page: "dataset";
    }
  | {
      page: "analysis";
      selection: AnalysisSelection;
    }
  | { page: "reports" }
  | { page: "help" };

export function parseAppRoute(pathname: string, hash: string): AppRoute {
  const normalizedPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (normalizedPath === "/reports") {
    return { page: "reports" };
  }
  if (normalizedPath === "/help") {
    return { page: "help" };
  }
  const analysisSelection = parseAnalysisLocation(normalizedPath, hash);
  if (analysisSelection !== null) {
    return {
      page: "analysis",
      selection: analysisSelection,
    };
  }
  return {
    page: "dataset",
  };
}

export function currentAppRoute(): AppRoute {
  if (typeof window === "undefined") {
    return {
      page: "dataset",
    };
  }
  return parseAppRoute(window.location.pathname, window.location.hash);
}
