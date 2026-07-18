import { useEffect, useMemo, useState } from "react";

import type {
  AnalysisMethodDescriptor,
  AnalysisMethodListResponse,
  AnalysisModuleId,
} from "./api";
import { buildAnalysisPath, parseAnalysisLocation } from "./analysisNavigation";

export const defaultAnalysisModuleId: AnalysisModuleId = "exploration";

export interface NullableAnalysisSelection {
  moduleId: AnalysisModuleId;
  methodId: string | null;
}

interface ResolvedAnalysisSelection {
  moduleId: AnalysisModuleId;
  methodId: string | null;
  methods: AnalysisMethodDescriptor[];
  method: AnalysisMethodDescriptor | null;
}

export function useAnalysisSelection(catalog: AnalysisMethodListResponse | null): {
  selectedMethod: AnalysisMethodDescriptor | null;
  selectedMethodId: string | null;
  selectedMethods: AnalysisMethodDescriptor[];
  selectedModuleId: AnalysisModuleId;
  selectAnalysisMethod: (moduleId: AnalysisModuleId, methodId: string | null) => void;
} {
  const initialSelection = initialAnalysisSelectionFromLocation();
  const [selectedModuleId, setSelectedModuleId] = useState<AnalysisModuleId>(
    initialSelection.moduleId,
  );
  const [selectedMethodId, setSelectedMethodId] = useState<string | null>(
    initialSelection.methodId,
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    function handleRouteChange() {
      const selection = initialAnalysisSelectionFromLocation();
      setSelectedModuleId(selection.moduleId);
      setSelectedMethodId(selection.methodId);
    }

    window.addEventListener("popstate", handleRouteChange);
    window.addEventListener("hashchange", handleRouteChange);
    return () => {
      window.removeEventListener("popstate", handleRouteChange);
      window.removeEventListener("hashchange", handleRouteChange);
    };
  }, []);

  useEffect(() => {
    if (catalog === null) {
      return;
    }
    const resolved = resolveAnalysisSelection(catalog, {
      moduleId: selectedModuleId,
      methodId: selectedMethodId,
    });
    setSelectedModuleId(resolved.moduleId);
    setSelectedMethodId(resolved.methodId);
    if (resolved.methodId !== null && isCurrentAnalysisLocation()) {
      replaceAnalysisRoute(resolved.moduleId, resolved.methodId, true);
    }
  }, [catalog, selectedMethodId, selectedModuleId]);

  const resolvedSelection = useMemo(
    () =>
      catalog === null
        ? {
            moduleId: selectedModuleId,
            methodId: selectedMethodId,
            methods: [],
            method: null,
          }
        : resolveAnalysisSelection(catalog, {
            moduleId: selectedModuleId,
            methodId: selectedMethodId,
          }),
    [catalog, selectedMethodId, selectedModuleId],
  );

  function selectAnalysisMethod(moduleId: AnalysisModuleId, methodId: string | null) {
    setSelectedModuleId(moduleId);
    setSelectedMethodId(methodId);
    if (methodId !== null) {
      replaceAnalysisRoute(moduleId, methodId);
    }
  }

  return {
    selectedMethod: resolvedSelection.method,
    selectedMethodId: resolvedSelection.methodId,
    selectedMethods: resolvedSelection.methods,
    selectedModuleId: resolvedSelection.moduleId,
    selectAnalysisMethod,
  };
}

export function resolveAnalysisSelection(
  catalog: AnalysisMethodListResponse,
  selection: NullableAnalysisSelection,
): ResolvedAnalysisSelection {
  const moduleId = catalog.modules.some((module) => module.module_id === selection.moduleId)
    ? selection.moduleId
    : (catalog.modules[0]?.module_id ?? defaultAnalysisModuleId);
  const methods = catalog.methods.filter((method) => method.module_id === moduleId);
  const method =
    methods.find((candidate) => candidate.method_id === selection.methodId) ?? methods[0] ?? null;

  return {
    moduleId,
    methodId: method?.method_id ?? null,
    methods,
    method,
  };
}

function initialAnalysisSelectionFromLocation(): NullableAnalysisSelection {
  if (typeof window === "undefined") {
    return {
      moduleId: defaultAnalysisModuleId,
      methodId: null,
    };
  }

  const parsed = parseAnalysisLocation(window.location.pathname, window.location.hash);
  return {
    moduleId: parsed?.moduleId ?? defaultAnalysisModuleId,
    methodId: parsed?.methodId ?? null,
  };
}

function replaceAnalysisRoute(
  moduleId: AnalysisModuleId,
  methodId: string,
  preserveSearch = false,
) {
  if (typeof window === "undefined") {
    return;
  }
  const search = preserveSearch ? window.location.search : "";
  window.history.replaceState(null, "", `${buildAnalysisPath(moduleId, methodId)}${search}`);
}

function isCurrentAnalysisLocation(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return parseAnalysisLocation(window.location.pathname, window.location.hash) !== null;
}
