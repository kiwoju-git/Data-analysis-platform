import { useI18n } from "./LocaleProvider";
import { presentApiNotice, type ApiNotice, type ApiNoticeMessageKeys } from "./apiNoticePresentation";

export function ApiNoticeText({ notice, showCode, messageKeys }: {
  notice: ApiNotice; showCode?: boolean; messageKeys?: ApiNoticeMessageKeys;
}) {
  const { locale } = useI18n();
  const presentation = presentApiNotice(notice, locale, messageKeys);
  return <>
    {presentation.message}
    {(showCode ?? !presentation.knownCode) && notice.code !== "" ? (
      <span className="cell-subtle">{presentation.code}</span>
    ) : null}
  </>;
}
