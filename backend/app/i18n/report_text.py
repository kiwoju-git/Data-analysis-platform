from typing import Literal

ReportLocale = Literal["en", "ko"]


def report_text(locale: ReportLocale, *, en: str, ko: str) -> str:
    return ko if locale == "ko" else en
