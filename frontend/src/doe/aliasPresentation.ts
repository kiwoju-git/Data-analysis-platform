import type { FactorialDesignResponse } from "../api/types/doe";

export type FractionalMetadata = NonNullable<FactorialDesignResponse["fractional"]>;
export type AliasTerm = NonNullable<FractionalMetadata["alias_classes"]>[number][number];

export function aliasEquation(terms: readonly AliasTerm[], full = false): string {
  return terms.map((term) => `${term.sign < 0 ? "-" : ""}${full ? term.full_label : term.compact_label}`)
    .join(" = ");
}

export function visibleAliasClasses(metadata: FractionalMetadata, maxOrder: number | null) {
  if (metadata.alias_view_schema_version !== 1 || !metadata.alias_classes) return null;
  return metadata.alias_classes
    .map((terms, index) => ({ id: `alias:${index}`, terms }))
    .filter(({ terms }) => maxOrder === null || terms.some((term) => term.order <= maxOrder));
}
