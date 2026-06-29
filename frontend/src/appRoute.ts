import { parseAnalysisLocation, type AnalysisSelection } from "./analysisNavigation";

export type AppRoute =
  | {
      page: "dataset";
    }
  | {
      page: "analysis";
      selection: AnalysisSelection;
    };

export function parseAppRoute(pathname: string, hash: string): AppRoute {
  const analysisSelection = parseAnalysisLocation(pathname, hash);
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
