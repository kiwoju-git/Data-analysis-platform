import { describe, expect, it } from "vitest";

import { createLocalizationPlugin } from "./vitePlugin";
import catalog from "./catalog.generated.json";

async function transform(code: string) {
  const plugin = createLocalizationPlugin({ "분석": "fixture.analysis", "이름": "fixture.name", "후": "fixture.after" });
  if (typeof plugin.transform !== "function") throw new Error("Expected transform hook");
  const output = await plugin.transform.call({} as never, code, "/fixture/frontend/src/Panel.tsx");
  if (typeof output === "string") return output;
  return output?.code?.toString() ?? code;
}

describe("localization compiler display boundary", () => {
  it("registers explicit BO display pairs without transforming their data or locale helper", async () => {
    const source = "측정 노이즈";
    const key = (catalog.sourceToKey as Record<string, string>)[source];
    expect((catalog.en as Record<string, string>)[key]).toBe("Measurement noise");
    expect((catalog.ko as Record<string, string>)[key]).toBe(source);
    const plugin = createLocalizationPlugin(catalog.sourceToKey);
    if (typeof plugin.transform !== "function") throw new Error("Expected transform hook");
    const input = 'const request = { name: "측정 노이즈", noise_mode: "estimate" }; const p = <p>{text("측정 노이즈", "Measurement noise")}</p>;';
    const result = await plugin.transform.call({} as never, input, "/fixture/frontend/src/Panel.tsx");
    const output = typeof result === "string" ? result : result?.code?.toString() ?? input;
    expect(output).toContain('name: "측정 노이즈"');
    expect(output).toContain('noise_mode: "estimate"');
    expect(output).toContain('text("측정 노이즈", "Measurement noise")');
    expect(output).not.toContain("__datalabUiText");
  });

  it("keeps the registered BO uncertainty and acquisition limitations explicit", () => {
    const mappings: Array<[string, string]> = [
      ["Jitter는 수치 안정화이며 측정오차 SD가 아닙니다.", "Jitter stabilizes numerical computation; it is not measurement SD."],
      ["거의 무잡음", "Near-noiseless"],
      ["16~256 사이의 정수를 입력하세요.", "Enter an integer from 16 through 256."],
      ["그룹 내 SS", "Within-group SS"],
    ];
    for (const [source, english] of mappings) {
      const key = (catalog.sourceToKey as Record<string, string>)[source];
      expect((catalog.ko as Record<string, string>)[key]).toBe(source);
      expect((catalog.en as Record<string, string>)[key]).toBe(english);
    }
  });

  it("translates display fallback literals without changing condition operands", async () => {
    const output = await transform('const p = <p>{userName ?? "이름"}{"분석" && "이름"}{"분석" || userName}</p>; const request = userName ?? "이름";');
    expect(output.match(/__datalabUiText_\d+\("fixture.name"\)/gu)).toHaveLength(2);
    expect(output).toContain('"분석" &&');
    expect(output).toContain('"분석" ||');
    expect(output).toContain('const request = userName ?? "이름"');
  });
  it("only translates static JSX text and declared presentation attributes", async () => {
    const output = await transform('const p = <section title="이름" data-name="이름" id="분석"><h2>분석</h2><input value="이름" placeholder="이름" /></section>;');
    expect(output).not.toContain("\uE000");
    expect(output).toContain('t as __datalabUiText');
    expect(output.match(/__datalabUiText_\d+\("fixture.name"\)/gu)).toHaveLength(2);
    expect(output).toContain('data-name="이름"');
    expect(output).toContain('value="이름"');
    expect(output).toContain('id="분석"');
  });

  it("does not change request objects, enums, keys, regex, comparisons or arbitrary strings", async () => {
    const source = 'const request = { name: "이름", method_id: "분석" }; const key = "분석"; const regex = /분석/; const p = <p>{key === "분석" ? "이름" : request.name}</p>;';
    const output = await transform(source);
    expect(output).toContain('name: "이름"');
    expect(output).toContain('method_id: "분석"');
    expect(output).toContain('const key = "분석"');
    expect(output).toContain('/분석/');
    expect(output).toContain('key === "분석"');
    expect(output).toMatch(/__datalabUiText_\d+\("fixture.name"\)/u);
    expect(output.match(/__datalabUiText_\d+\(/gu)).toHaveLength(1);
  });

  it("translates literal template segments without interpreting interpolated user values", async () => {
    const output = await transform('const p = <p>{`이름 ${userName} 후`}</p>; const name = `이름 ${userName} 후`;');
    expect(output).toMatch(/__datalabUiText_\d+\("fixture.name"\)/u);
    expect(output).toMatch(/__datalabUiText_\d+\("fixture.after"\)/u);
    expect(output).toContain('userName');
    expect(output).toContain('const name = `이름 ${userName} 후`');
    expect(output).not.toContain('resolveLocalizedText');
  });

  it("translates nested static fallbacks in display templates, not dynamic user text", async () => {
    const output = await transform('const p = <p>{`${userName || `이름 ${index}`} 후`}</p>;');
    expect(output.match(/__datalabUiText_\d+\("fixture.name"\)/gu)).toHaveLength(1);
    expect(output.match(/__datalabUiText_\d+\("fixture.after"\)/gu)).toHaveLength(1);
    expect(output).toContain("userName ||");
    expect(output).not.toContain("resolveLocalizedText");
  });

  it("supports declared UI collection labels but not arbitrary request objects or values", async () => {
    const output = await transform('const p = <DoeSettingsTable fields={[{label:"이름", value:"이름", request:{label:"이름"}}]} />; const q = <Sender request={{label:"이름"}} />; const r = <DefinitionRows rows={[["분석", userValue]]}/>;');
    expect(output.match(/__datalabUiText_\d+\("fixture.name"\)/gu)).toHaveLength(1);
    expect(output.match(/__datalabUiText_\d+\("fixture.analysis"\)/gu)).toHaveLength(1);
    expect(output).toContain('value: "이름"');
    expect(output).toContain('request: { label: "이름" }');
    expect(output).toContain('request={{ label: "이름" }}');
  });
});
