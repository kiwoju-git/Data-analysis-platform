import type { SchemaDraft } from "./schemaPresets";

export type SchemaDraftPatch = Partial<
  Pick<SchemaDraft, "display_name" | "measurement_level" | "role" | "unit">
>;
