import type {
  DatasetColumnRole,
  DatasetMeasurementLevel,
  DatasetVersionResponse,
} from "./api";
import { columnRoleOptions, measurementLevelOptions } from "./datasetDisplay";
import type { SchemaDraftPatch } from "./datasetPreparationTypes";
import type { SchemaDraft } from "./schemaPresets";

interface DatasetSchemaSectionProps {
  canApplyBayesianPreset: boolean;
  isSavingSchema: boolean;
  schemaDrafts: SchemaDraft[];
  version: DatasetVersionResponse;
  onApplyBayesianPreset: () => void;
  onSaveSchema: () => void;
  onSchemaDraftChange: (columnId: string, patch: SchemaDraftPatch) => void;
}

export function DatasetSchemaSection({
  canApplyBayesianPreset,
  isSavingSchema,
  schemaDrafts,
  version,
  onApplyBayesianPreset,
  onSaveSchema,
  onSchemaDraftChange,
}: DatasetSchemaSectionProps) {
  return (
    <>
      <div className="schema-actions">
        <span>스키마 확인</span>
        <div className="button-row">
          {canApplyBayesianPreset ? (
            <button className="secondary-button" onClick={onApplyBayesianPreset} type="button">
              Bayesian 역할 자동 지정
            </button>
          ) : null}
          <button
            className="secondary-button"
            disabled={isSavingSchema}
            onClick={onSaveSchema}
            type="button"
          >
            {isSavingSchema ? "저장 중" : "스키마 저장"}
          </button>
        </div>
      </div>
      <div className="table-wrap">
        <table className="schema-table">
          <thead>
            <tr>
              <th>컬럼</th>
              <th>표시명</th>
              <th>타입</th>
              <th>측정 수준</th>
              <th>역할</th>
              <th>단위</th>
            </tr>
          </thead>
          <tbody>
            {version.columns.map((column) => {
              const draft = schemaDrafts.find((item) => item.column_id === column.column_id);
              return (
                <tr key={column.column_id}>
                  <td>{column.original_name || "(empty)"}</td>
                  <td>
                    <input
                      aria-label={`${column.original_name || "empty"} 표시명`}
                      value={draft?.display_name ?? column.display_name}
                      onChange={(event) => {
                        onSchemaDraftChange(column.column_id, {
                          display_name: event.currentTarget.value,
                        });
                      }}
                    />
                  </td>
                  <td>{column.data_type}</td>
                  <td>
                    <select
                      aria-label={`${column.original_name || "empty"} 측정 수준`}
                      value={draft?.measurement_level ?? column.measurement_level}
                      onChange={(event) => {
                        const measurementLevel = event.currentTarget
                          .value as DatasetMeasurementLevel;
                        onSchemaDraftChange(column.column_id, {
                          measurement_level: measurementLevel,
                        });
                      }}
                    >
                      {measurementLevelOptions.map((level) => (
                        <option key={level.value} value={level.value}>
                          {level.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      aria-label={`${column.original_name || "empty"} 역할`}
                      value={draft?.role ?? column.role}
                      onChange={(event) => {
                        const role = event.currentTarget.value as DatasetColumnRole;
                        onSchemaDraftChange(column.column_id, {
                          role,
                        });
                      }}
                    >
                      {columnRoleOptions.map((role) => (
                        <option key={role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      aria-label={`${column.original_name || "empty"} 단위`}
                      value={draft?.unit ?? column.unit ?? ""}
                      onChange={(event) => {
                        onSchemaDraftChange(column.column_id, {
                          unit: event.currentTarget.value,
                        });
                      }}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
