import { parseAnalysisLocation, type AnalysisSelection } from "./analysisNavigation";
import {
  isAnalysisModuleAvailableInProfile,
  isPresentationProfile,
  statisticalTwinProfile,
} from "./productProfile";

export type AppRoute =
  | {
      page: "home";
    }
  | {
      page: "dataset";
    }
  | {
      page: "analysis";
      selection: AnalysisSelection;
    }
  | { page: "graphs" }
  | { page: "reports" }
  | { page: "manage" }
  | { page: "help" };

export function parseAppRoute(pathname: string, hash: string): AppRoute {
  const normalizedPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  if (
    isPresentationProfile &&
    ["/graphs", "/reports", "/help", "/manage"].includes(normalizedPath)
  ) {
    return { page: "home" };
  }
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
  const analysisSelection = parseAnalysisLocation(normalizedPath, hash);
  if (analysisSelection !== null) {
    if (
      isPresentationProfile &&
      !isAnalysisModuleAvailableInProfile(analysisSelection.moduleId, statisticalTwinProfile)
    ) {
      return { page: "home" };
    }
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
