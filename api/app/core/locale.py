import re

from langdetect import DetectorFactory, LangDetectException, detect_langs

LOCALE_CATALOG = {
    "en": {"route": "en", "label": "English", "native_label": "English"},
    "zh-tw": {"route": "zh-TW", "label": "Traditional Chinese", "native_label": "繁體中文"},
    "ja": {"route": "ja", "label": "Japanese", "native_label": "日本語"},
    "fr": {"route": "fr", "label": "French", "native_label": "Français"},
    "ru": {"route": "ru", "label": "Russian", "native_label": "Русский"},
}

# Public website chrome currently ships complete message packs for these route locales.
# Other catalog locales are fully available for CMS drafts and review, but must not be
# represented as a complete public-site shell until their message pack is delivered.
PUBLIC_SITE_LOCALES = ("en", "zh-TW")
SUPPORTED_LOCALES = set(PUBLIC_SITE_LOCALES)
# Fallback when a request omits locale. Tenant source locale comes from site_profiles.default_locale.
SOURCE_LOCALE = "en"
SUPPORTED_CONTENT_LOCALES = tuple(LOCALE_CATALOG)
TARGET_LOCALES = tuple(locale for locale in SUPPORTED_CONTENT_LOCALES if locale != SOURCE_LOCALE)

# Public website content is intentionally limited to the locales above. Chat
# response languages are not: the advisor must answer in the visitor's language
# even when the approved source material is English.
_CHAT_LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,2}$")
_JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
_JAPANESE_TERM_RE = re.compile(r"(見積|納期|発注|製品|仕様|認証|希望|数量)")
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff]")
_HAN_RE = re.compile(r"[\u3400-\u9fff]")
_TRADITIONAL_HAN_RE = re.compile(r"[詢價與業這個門開關規格證認購買數量臺灣體]")
_SIMPLIFIED_HAN_RE = re.compile(r"[询价与业这个门开关规格证认购买数量台湾体]")
_SCRIPT_HINTS = (
    (re.compile(r"[\u0600-\u06ff]"), "ar"),
    (re.compile(r"[\u0590-\u05ff]"), "he"),
    (re.compile(r"[\u0900-\u097f]"), "hi"),
    (re.compile(r"[\u0e00-\u0e7f]"), "th"),
    (re.compile(r"[\u0370-\u03ff]"), "el"),
)
_GREETING_HINTS = {
    "hello": "en",
    "hola": "es",
    "bonjour": "fr",
    "hallo": "de",
    "guten tag": "de",
    "ciao": "it",
    "olá": "pt",
    "ola": "pt",
}

DetectorFactory.seed = 0

_ROUTE_TO_CONTENT = {
    alias: content_locale
    for content_locale, definition in LOCALE_CATALOG.items()
    for alias in {
        content_locale,
        definition["route"],
        definition["route"].lower(),
        definition["route"].replace("-", "_"),
    }
}


def to_content_locale(raw: str | None, default: str = SOURCE_LOCALE) -> str:
    """Normalize route/UI locale tags to the lowercase CMS representation."""
    if not raw:
        return default
    key = raw.strip()
    if key in _ROUTE_TO_CONTENT:
        return _ROUTE_TO_CONTENT[key]
    return _ROUTE_TO_CONTENT.get(key.lower().replace("_", "-"), default)


def to_route_locale(raw: str | None, default: str = "en") -> str:
    content_locale = to_content_locale(raw, default="")
    definition = LOCALE_CATALOG.get(content_locale)
    return str(definition["route"]) if definition else default


def content_locale_label(raw: str | None, *, native: bool = False) -> str:
    content_locale = to_content_locale(raw, default="")
    definition = LOCALE_CATALOG.get(content_locale)
    if not definition:
        return (raw or "").strip()
    return str(definition["native_label" if native else "label"])


def locale_catalog_payload() -> list[dict[str, str | bool]]:
    return [
        {
            "content_locale": content_locale,
            "route_locale": str(definition["route"]),
            "label": str(definition["label"]),
            "native_label": str(definition["native_label"]),
            "public_shell_ready": definition["route"] in PUBLIC_SITE_LOCALES,
        }
        for content_locale, definition in LOCALE_CATALOG.items()
    ]


def is_source_locale(raw: str | None) -> bool:
    return to_content_locale(raw) == SOURCE_LOCALE


def normalize_locale(value: str | None, default: str = "en") -> str:
    raw = (value or "").strip().replace("_", "-").lower()
    if raw.startswith("zh"):
        return "zh-TW"
    if raw.startswith("en"):
        return "en"
    return default


def normalize_chat_locale(value: str | None, default: str = "en") -> str:
    """Return a safe BCP-47-ish response locale without restricting chat to site locales."""
    raw = (value or "").strip().replace("_", "-")
    if not raw or not _CHAT_LOCALE_RE.fullmatch(raw):
        raw = default.strip().replace("_", "-") if default else "en"
    if not _CHAT_LOCALE_RE.fullmatch(raw):
        return "en"

    parts = raw.split("-")
    primary = parts[0].lower()
    if primary == "zh":
        lowered = raw.lower()
        return (
            "zh-CN"
            if any(tag in lowered for tag in ("hans", "-cn", "-sg"))
            else "zh-TW"
        )

    normalized = [primary]
    for part in parts[1:]:
        if len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        elif len(part) in {2, 3} and part.isalnum():
            normalized.append(part.upper())
        else:
            normalized.append(part.lower())
    result = "-".join(normalized)
    return result if len(result) <= 10 else primary


def chat_language(locale: str | None) -> str:
    return normalize_chat_locale(locale).split("-", 1)[0].lower()


def infer_message_locale(message: str, fallback: str = "en") -> str:
    """Infer the visitor language while keeping short model/spec inputs in-session."""
    text = (message or "").strip()
    fallback_locale = normalize_chat_locale(fallback)
    if not text:
        return fallback_locale
    if _JAPANESE_RE.search(text):
        return "ja"
    if _JAPANESE_TERM_RE.search(text):
        return "ja"
    if _HANGUL_RE.search(text):
        return "ko"
    if _HAN_RE.search(text):
        # Short Han-only messages are ambiguous; retain the established
        # Traditional-Chinese default. Longer Simplified-Chinese messages can
        # be distinguished by the detector.
        if _TRADITIONAL_HAN_RE.search(text):
            return "zh-TW"
        if _SIMPLIFIED_HAN_RE.search(text):
            return "zh-CN"
        if len(text) >= 6:
            try:
                candidates = detect_langs(text)
                if candidates and candidates[0].lang.startswith("zh"):
                    return normalize_chat_locale(candidates[0].lang, "zh-TW")
            except LangDetectException:
                pass
        return "zh-TW"
    for pattern, locale in _SCRIPT_HINTS:
        if pattern.search(text):
            return locale

    lowered = re.sub(r"\s+", " ", text.lower()).strip(" .,!?:;¡¿")
    if lowered in _GREETING_HINTS:
        return _GREETING_HINTS[lowered]

    letters = "".join(character for character in text if character.isalpha())
    if len(letters) < 4 or re.fullmatch(r"[A-Za-z]{1,5}-?\d+[A-Za-z0-9-]*", text):
        return fallback_locale
    try:
        candidates = detect_langs(text)
    except LangDetectException:
        return fallback_locale
    if not candidates or candidates[0].prob < 0.55:
        return fallback_locale
    return normalize_chat_locale(candidates[0].lang, fallback_locale)
