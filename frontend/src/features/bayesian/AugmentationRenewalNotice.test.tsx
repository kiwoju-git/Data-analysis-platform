import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, expect, it } from "vitest";
import { setCurrentLocale } from "../../i18n/store";
import { AugmentationRenewalNotice } from "./AugmentationRenewalNotice";

afterEach(() => setCurrentLocale("ko"));
it.each(["en", "ko"] as const)("shows explicit review action without auto-confirmation in %s", locale => {
  setCurrentLocale(locale);
  let calls = 0;
  const html = renderToStaticMarkup(<AugmentationRenewalNotice required lineage={null} confirmed={false} disabled={false}
    onRenew={() => calls++} onOpenOriginal={() => calls++} />);
  expect(html).toContain(locale === "en" ? "Renew saved recommendation" : "저장 추천 재검토");
  expect(html).toContain('role="status"');
  expect(html).toContain('type="button"');
  expect(calls).toBe(0);
  expect(renderToStaticMarkup(<AugmentationRenewalNotice required lineage={null} confirmed disabled={false}
    onRenew={() => calls++} onOpenOriginal={() => calls++} />)).toBe("");
});
