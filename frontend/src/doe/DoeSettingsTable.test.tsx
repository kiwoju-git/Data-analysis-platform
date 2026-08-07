import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DoeSettingsTable } from "./DoeSettingsTable";

describe("DoeSettingsTable", () => {
  it("renders semantic headers, controls, helpers, toggles, and errors", () => {
    const html = renderToStaticMarkup(
      <DoeSettingsTable
        ariaLabel="설계 설정"
        fields={[
          {
            key: "name",
            label: "설계 이름",
            controlId: "test-design-name",
            control: <input id="test-design-name" defaultValue="DOE" />,
            helper: "사용자에게 표시할 이름입니다.",
            helperId: "test-design-name-help",
          },
          {
            key: "policy",
            label: "설계 방식",
            controlId: "test-design-policy",
            control: (
              <select id="test-design-policy" defaultValue="lhs">
                <option value="lhs">LHS</option>
              </select>
            ),
          },
          {
            key: "randomize",
            label: "실행 순서 무작위화",
            controlId: "test-randomize",
            control: (
              <label className="doe-table-toggle" htmlFor="test-randomize">
                <input id="test-randomize" type="checkbox" defaultChecked />
                <span>사용</span>
              </label>
            ),
          },
          {
            key: "seed",
            label: "Seed",
            controlId: "test-seed",
            control: <input id="test-seed" disabled defaultValue="1" />,
            helper: "유효한 seed를 입력하세요.",
            helperId: "test-seed-error",
            helperTone: "error",
          },
        ]}
      />,
    );

    expect(html).toContain('class="result-table doe-settings-table');
    expect(html).toContain("<thead><tr>");
    expect(html).toContain('<th id="compact-setting-');
    expect(html).toContain('<label for="test-design-name">설계 이름</label>');
    expect(html).toContain("<tbody>");
    expect(html).toContain('id="test-randomize" type="checkbox" checked=""');
    expect(html).toContain('id="test-design-policy"');
    expect(html).toContain('id="test-seed" disabled=""');
    expect(html).toContain('id="test-seed-error"');
    expect(html).toContain('class="compact-settings-helper is-error"');
    expect(html).not.toContain("doe-settings-matrix");
  });
});
