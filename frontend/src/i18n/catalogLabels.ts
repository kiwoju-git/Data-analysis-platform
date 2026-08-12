import type {
  AnalysisMethodDescriptor,
  AnalysisModuleDescriptor,
} from "../api";
import type { AppLocale } from "./types";

export function moduleLabel(module: AnalysisModuleDescriptor, locale: AppLocale): string {
  return locale === "ko" ? module.label_ko : module.label_en;
}

export function methodLabel(method: AnalysisMethodDescriptor, locale: AppLocale): string {
  return locale === "ko" ? method.label_ko : method.label_en;
}
