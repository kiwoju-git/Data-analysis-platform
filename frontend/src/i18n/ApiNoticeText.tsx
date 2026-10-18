import { useI18n } from "./LocaleProvider";
import { presentApiNotice, type ApiNotice } from "./apiNoticePresentation";

export function ApiNoticeText({ notice, showCode }: { notice: ApiNotice; showCode?: boolean }) {
  const { locale } = useI18n();
  const presentation = presentApiNotice(notice, locale);
  return <>
    {presentation.message}
    {(showCode ?? !presentation.knownCode) && notice.code !== "" ? (
      <span className="cell-subtle">{presentation.code}</span>
    ) : null}
  </>;
}
