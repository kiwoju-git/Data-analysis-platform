import { setCurrentLocale } from "./i18n/store";

// Existing component tests assert the established Korean UX. Product startup is
// always wrapped by LocaleProvider and still defaults to English.
setCurrentLocale("ko");
