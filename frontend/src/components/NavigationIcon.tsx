import {
  Activity, ArrowRight, BookOpen, Box, BrainCircuit, ChartColumnIncreasing,
  ChartLine, ChartNoAxesCombined, ChartScatter, Check, ChevronDown, Database,
  Equal, FileChartColumn, FolderOpen, Gauge, Grid2X2, House, RefreshCw,
  SlidersHorizontal, type LucideIcon,
} from "lucide-react";

import type { AnalysisDomainId } from "../analysisDomains";
import { analysisDomainForMethod } from "../analysisDomainMapping";

const icons = {
  home: House, dataset: Database, analysis: ChartNoAxesCombined, graphs: ChartLine,
  reports: FileChartColumn, manage: FolderOpen, help: BookOpen,
  "basic-exploration": ChartColumnIncreasing,
  "mean-equivalence": Equal,
  "proportions-categorical": Grid2X2,
  "correlation-regression-prediction": ChartScatter,
  "doe-optimization": Box,
  "ai-ml-experimental-design": BrainCircuit,
  "quality-process-monitoring": Activity,
  "measurement-variability": Gauge,
  histogram: ChartColumnIncreasing, box_plot: SlidersHorizontal,
  individual_value_plot: ChartScatter, scatter_plot: ChartScatter,
  run_chart: ChartLine, imr_chart: Activity, qq_plot: ChartScatter, ecdf: ChartLine,
  arrow: ArrowRight, chevron: ChevronDown, refresh: RefreshCw, check: Check,
} satisfies Record<string, LucideIcon> & Record<AnalysisDomainId, LucideIcon>;

export function NavigationIcon({ name, className = "", size = 20 }: {
  name: string;
  className?: string;
  size?: number;
}) {
  const key = name in icons ? name : analysisDomainForMethod(name)?.id ?? "analysis";
  const Icon = icons[key as keyof typeof icons];
  return <Icon aria-hidden="true" focusable="false" className={`navigation-icon ${className}`}
    size={size} strokeWidth={1.8} />;
}
