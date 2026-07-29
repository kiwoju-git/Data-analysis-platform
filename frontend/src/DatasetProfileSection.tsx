import type { DatasetProfileResponse } from "./api";
import {
  formatPercent,
  formatProfileSummary,
  measurementLevelLabel,
  roleLabel,
} from "./datasetDisplay";

interface DatasetProfileSectionProps {
  isLoadingProfile: boolean;
  profile: DatasetProfileResponse | null;
  versionId: string;
  onLoadDatasetProfile: (versionId: string) => void;
}

export function DatasetProfileSection({
  isLoadingProfile,
  profile,
  versionId,
  onLoadDatasetProfile,
}: DatasetProfileSectionProps) {
  const missingCellCount =
    profile?.columns.reduce((total, column) => total + column.n_missing, 0) ?? 0;
  const missingColumnCount =
    profile?.columns.filter((column) => column.n_missing > 0).length ?? 0;
  const warningColumnCount =
    profile?.columns.filter((column) => column.warnings.length > 0).length ?? 0;
  const constantColumnCount =
    profile?.columns.filter((column) => column.constant).length ?? 0;
  const idCandidateCount =
    profile?.columns.filter(
      (column) =>
        column.role === "id" ||
        column.measurement_level === "id" ||
        column.warnings.some((warning) => warning.code.includes("id")),
    ).length ?? 0;

  return (
    <>
      <div className="schema-actions">
        <div>
          <strong>데이터 품질 점검</strong>
          <p>결측, 고유값, 상수열, ID 후보와 타입 문제를 분석 전에 확인합니다.</p>
        </div>
        <button
          className="secondary-button"
          disabled={isLoadingProfile}
          onClick={() => {
            onLoadDatasetProfile(versionId);
          }}
          type="button"
        >
          {isLoadingProfile ? "점검 중" : profile === null ? "품질 점검 실행" : "새로고침"}
        </button>
      </div>
      {profile?.warnings.length ? (
        <ul className="warning-list" aria-label="데이터셋 프로파일 경고">
          {profile.warnings.map((warning) => (
            <li key={warning.code}>{warning.message}</li>
          ))}
        </ul>
      ) : null}
      {profile !== null ? (
        <dl className="profile-quality-summary" aria-label="데이터 품질 요약">
          <QualityStat label="전체 행" value={profile.row_count.toLocaleString()} />
          <QualityStat label="전체 열" value={profile.column_count.toLocaleString()} />
          <QualityStat
            label="결측 셀"
            value={`${missingCellCount.toLocaleString()} · ${missingColumnCount.toLocaleString()}개 열`}
          />
          <QualityStat
            label="중복 행"
            value={`${profile.preflight.duplicate_row_count.toLocaleString()}${
              profile.preflight.duplicate_row_count_capped ? "+" : ""
            }`}
          />
          <QualityStat label="경고 열" value={warningColumnCount.toLocaleString()} />
          <QualityStat label="상수열" value={constantColumnCount.toLocaleString()} />
          <QualityStat label="ID 후보" value={idCandidateCount.toLocaleString()} />
        </dl>
      ) : null}
      {profile !== null ? (
        <div className="table-wrap">
          <table className="profile-table">
            <colgroup>
              <col className="profile-column-variable" />
              <col className="profile-column-role" />
              <col className="profile-column-missing" />
              <col className="profile-column-unique" />
              <col className="profile-column-summary" />
              <col className="profile-column-check" />
            </colgroup>
            <thead>
              <tr>
                <th>변수</th>
                <th>역할 · 수준</th>
                <th>결측</th>
                <th>고유값</th>
                <th>요약</th>
                <th>점검</th>
              </tr>
            </thead>
            <tbody>
              {profile.columns.map((column) => (
                <tr key={column.column_id}>
                  <td>
                    <strong>{column.display_name}</strong>
                    <span className="cell-subtle">{column.data_type}</span>
                  </td>
                  <td className="profile-nowrap">
                    <span
                      aria-label={`역할 ${roleLabel(column.role)}, 측정 수준 ${measurementLevelLabel(
                        column.measurement_level,
                      )}`}
                      className="profile-role-level"
                    >
                      <span>{roleLabel(column.role)}</span>
                      <span aria-hidden="true">·</span>
                      <span>{measurementLevelLabel(column.measurement_level)}</span>
                    </span>
                  </td>
                  <td className="profile-numeric-cell">
                    {column.n_missing.toLocaleString()} / {column.n_total.toLocaleString()}
                    <span aria-hidden="true"> · </span>
                    {formatPercent(column.missing_rate)}
                  </td>
                  <td className="profile-numeric-cell">
                    {column.unique_count_capped
                      ? `${profile.unique_count_limit}+`
                      : column.unique_count.toLocaleString()}
                  </td>
                  <td>{formatProfileSummary(column)}</td>
                  <td>
                    {column.warnings.length > 0 ? (
                      <ul className="inline-warning-list">
                        {column.warnings.map((warning) => (
                          <li key={warning.code}>{warning.message}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="cell-subtle">경고 없음</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="notice-box">
          {isLoadingProfile ? "프로파일 계산 중" : "프로파일을 아직 불러오지 않았습니다."}
        </div>
      )}
    </>
  );
}

function QualityStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
