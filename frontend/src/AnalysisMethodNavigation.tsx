import type { ReactNode } from "react";

import { useI18n } from "./i18n/LocaleProvider";

interface AnalysisMethodNavigationProps {
  selectedMethodId: string | null;
  children: ReactNode;
}

export function AnalysisMethodNavigation({ selectedMethodId, children }: AnalysisMethodNavigationProps) {
  const { t } = useI18n();
  if (selectedMethodId === null) return <>{children}</>;

  // Only navigation resets on a method change. The executable panel is a sibling.
  return (
    <details className="analysis-method-navigation" key={selectedMethodId}>
      <summary>{t("uiRefinement.changeAnalysis")}</summary>
      <div className="analysis-method-navigation-content">{children}</div>
    </details>
  );
}
