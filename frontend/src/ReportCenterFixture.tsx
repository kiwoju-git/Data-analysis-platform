import { useState } from "react";
import { ReportCenterPage } from "./ReportCenterPage";
import { LocaleProvider, useI18n } from "./i18n/LocaleProvider";

// Synthetic browser fixture only; not part of the application route graph.
export function ReportCenterFixture() {
  return <LocaleProvider><FixtureControls /></LocaleProvider>;
}

function FixtureControls() {
  const { setLocale } = useI18n();
  const [datasetId, setDatasetId] = useState<string | null>("20000000-0000-4000-8000-000000000001");
  const [revision, setRevision] = useState(0);
  const [mounted, setMounted] = useState(true);
  return <main style={{ padding: 16, maxWidth: 1200, margin: "auto", minWidth: 0 }}>
    <div className="button-row">
      <button onClick={() => setLocale("ko")}>KOR</button>
      <button onClick={() => setLocale("en")}>ENG</button>
      <button onClick={() => setDatasetId(null)}>Clear fixture dataset</button>
      <button onClick={() => setRevision((value) => value + 1)}>Refresh fixture workspace</button>
      <button onClick={() => setMounted((value) => !value)}>Toggle fixture view</button>
    </div>
    {mounted ? <ReportCenterPage catalog={null} currentDatasetVersionId={datasetId}
      workspaceAssetRevision={revision} onWorkspaceMutation={() => setRevision((value) => value + 1)} /> : null}
  </main>;
}
