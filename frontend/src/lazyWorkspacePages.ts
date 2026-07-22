import { lazy } from "react";

export const HelpCenterPage = lazy(() =>
  import("./HelpCenterPage").then((module) => ({ default: module.HelpCenterPage })),
);

export const ReportCenterPage = lazy(() =>
  import("./ReportCenterPage").then((module) => ({ default: module.ReportCenterPage })),
);

export const ManageAssetsPage = lazy(() =>
  import("./ManageAssetsPage").then((module) => ({ default: module.ManageAssetsPage })),
);
