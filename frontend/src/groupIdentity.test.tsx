import { afterEach, describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { GroupIdentityDetails } from "./GroupIdentityDetails";
import { fullGroupName, groupDisplayLabel, pairGroupLabel, validStoredGroupIdentities } from "./groupIdentity";
import { setCurrentLocale } from "./i18n/store";
import { InteractiveVarianceComparisonIntervalsChart, varianceGroupDetails } from "./charts/InteractiveVarianceComparisonIntervalsChart";
import type { EqualVarianceMultipleComparisons } from "./api/types/analysisResultsExploration";

const prefix = "X".repeat(121);
const label = `${"X".repeat(117)}...`;
const groups = [
  { group_index: 0, group_label: label, group_value: `${prefix}-A<&>\ue000user.key\ue001` },
  { group_index: 1, group_label: label, group_value: `${prefix}-B` },
  { group_index: 2, group_label: "literal...", group_value: "literal..." },
];
const comparison: EqualVarianceMultipleComparisons = {
  computed: true, method: "bonett", alpha: 0.05, p_value: 0.01, reject_equal_variances: true, warnings: [],
  groups: groups.map((group) => ({ ...group, n: 10, sample_standard_deviation: group.group_index + 1, comparison_interval: { lower: group.group_index + 0.5, upper: group.group_index + 1.5 }, allocation: 0.5 })),
  pairwise_p_values: [],
  non_overlapping_pairs: [{ left_group: label, right_group: "literal...", left_group_index: 1, right_group_index: 2, left_group_value: groups[1].group_value, right_group_value: "literal..." }],
};

afterEach(() => setCurrentLocale("ko"));

describe("stored group identities", () => {
  it.each(["ko", "en"] as const)("shows expandable full names and stable distinct identities in %s", (locale) => {
    setCurrentLocale(locale);
    const markup = renderToStaticMarkup(<GroupIdentityDetails groups={groups} />);
    expect(markup).toContain("data-group-identities");
    expect(markup).toContain(locale === "ko" ? "전체 그룹명" : "Full group names");
    expect(markup).toContain(`${prefix}-A&lt;&amp;&gt;\ue000user.key\ue001`);
    expect(markup).toContain(`${prefix}-B`);
    expect(markup).not.toContain("data-group-identity-legacy");
    expect(groupDisplayLabel(groups[0], groups, locale)).toContain(locale === "ko" ? "그룹 1" : "Group 1");
    expect(pairGroupLabel(1, label, groups, locale)).toContain(locale === "ko" ? "그룹 2" : "Group 2");
    expect(fullGroupName(groups[2])).toBe("literal...");
  });

  it("does not reconstruct names or infer legacy pair indexes", () => {
    setCurrentLocale("en");
    const legacy = groups.map(({ group_index, group_label }) => ({ group_index, group_label }));
    const markup = renderToStaticMarkup(<GroupIdentityDetails groups={legacy} />);
    expect(markup).toContain("does not contain full group values");
    expect(markup).not.toContain(`${prefix}-B`);
    expect(pairGroupLabel(undefined, label, groups, "en")).toBe(label);
    expect(validStoredGroupIdentities(legacy, false)).toBe(true);
    expect(validStoredGroupIdentities(legacy, true)).toBe(false);
    expect(validStoredGroupIdentities([groups[0], groups[0]], true)).toBe(false);
    expect(validStoredGroupIdentities(groups, true)).toBe(true);
  });

  it.each(["ko", "en"] as const)("uses exact interval pair indexes and full tooltip names in %s", (locale) => {
    setCurrentLocale(locale);
    expect(varianceGroupDetails(comparison.groups[0], comparison, locale).at(-1)?.value).toBe(locale === "ko" ? "없음" : "None");
    expect(varianceGroupDetails(comparison.groups[1], comparison, locale).at(-1)?.value).toBe("literal...");
    expect(varianceGroupDetails(comparison.groups[2], comparison, locale).at(-1)?.value).toBe(groups[1].group_value);
    const markup = renderToStaticMarkup(<InteractiveVarianceComparisonIntervalsChart chartId="identity" sourceKey="analysis-A" groupName="그룹\ue000raw\ue001" responseName="response" result={comparison} />);
    expect(markup).toContain(`${prefix}-A&lt;&amp;&gt;\ue000user.key\ue001`);
    expect(markup).toContain(`${prefix}-B`);
    expect(markup.match(/tabindex="0"/g)).toHaveLength(1);
    expect(markup).toContain('data-group-index="0"');
    expect(markup).toContain('data-group-index="1"');
  });
});
