import { parseAnalysisLocation, type AnalysisSelection } from "./analysisNavigation";

export type AppRoute =
  | {
      page: "home";
    }
  | {
      page: "dataset";
    }
  | {
      page: "analysis";
      selection: AnalysisSelection | null;
    }
  | { page: "graphs" }
  | { page: "reports" }
  | { page: "manage" }
  | { page: "help" };

export function parseAppRoute(pathname: string, hash: string): AppRoute {
  const normalizedPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (normalizedPath === "/" || normalizedPath === "/home" || normalizedPath === "/project") {
    return { page: "home" };
  }
  if (normalizedPath === "/datasets") {
    return { page: "dataset" };
  }
  if (normalizedPath === "/graphs") {
    return { page: "graphs" };
  }
  if (normalizedPath === "/reports") {
    return { page: "reports" };
  }
  if (normalizedPath === "/help") {
    return { page: "help" };
  }
  if (normalizedPath === "/manage") {
    return { page: "manage" };
  }
  if (normalizedPath === "/analysis") {
    return { page: "analysis", selection: null };
  }
  const analysisSelection = parseAnalysisLocation(normalizedPath, hash);
  if (analysisSelection !== null) {
    return {
      page: "analysis",
      selection: analysisSelection,
    };
  }
  return {
    page: "home",
  };
}

export function currentAppRoute(): AppRoute {
  if (typeof window === "undefined") {
    return {
      page: "home",
    };
  }
  return parseAppRoute(window.location.pathname, window.location.hash);
}
