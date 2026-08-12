import { useI18n } from "./LocaleProvider";

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();
  return (
    <div className="language-switcher" role="group" aria-label={t("language.selector")}>
      <button
        aria-label={t("language.korean")}
        aria-pressed={locale === "ko"}
        className={locale === "ko" ? "is-active" : undefined}
        onClick={() => setLocale("ko")}
        type="button"
      >
        KOR
      </button>
      <span aria-hidden="true">/</span>
      <button
        aria-label={t("language.english")}
        aria-pressed={locale === "en"}
        className={locale === "en" ? "is-active" : undefined}
        onClick={() => setLocale("en")}
        type="button"
      >
        ENG
      </button>
    </div>
  );
}
