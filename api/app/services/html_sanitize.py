"""
HTML sanitize（CF→FB Publish Contract §8）

以 stdlib HTMLParser 實作白名單淨化，避免新增第三方相依：
- 剝除 script/style/iframe/object/embed/form 等危險標籤（含內容）
- 剝除所有 on* 事件屬性與 style 屬性
- href/src 僅允許 http/https/mailto/相對路徑，拒絕 javascript:、data:
- 非白名單標籤去殼保留文字
"""
from html import escape
from html.parser import HTMLParser

_ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "code",
    "strong", "em", "b", "i", "u", "s", "small", "sub", "sup",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "span", "div", "section", "article",
}

# 這些標籤連同內容整段丟棄
_DROP_CONTENT_TAGS = {"script", "style", "iframe", "object", "embed", "form", "noscript", "template"}

_ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height", "loading"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
}
_GLOBAL_ATTRS = {"class", "id", "lang", "dir"}

_ALLOWED_SCHEMES = {"http", "https", "mailto"}
_URL_ATTRS = {"href", "src"}

_VOID_TAGS = {"br", "hr", "img"}


def _is_safe_url(value: str) -> bool:
    v = value.strip().lower()
    if not v:
        return False
    if v.startswith(("/", "#")):
        return True
    scheme = v.split(":", 1)[0]
    if ":" not in v:
        return True  # 相對路徑
    return scheme in _ALLOWED_SCHEMES


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._drop_depth:
            if tag in _DROP_CONTENT_TAGS:
                self._drop_depth += 1
            return
        if tag in _DROP_CONTENT_TAGS:
            self._drop_depth = 1
            return
        if tag not in _ALLOWED_TAGS:
            return
        allowed = _ALLOWED_ATTRS.get(tag, set()) | _GLOBAL_ATTRS
        parts = [tag]
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on") or name == "style" or name not in allowed or value is None:
                continue
            if name in _URL_ATTRS and not _is_safe_url(value):
                continue
            parts.append(f'{name}="{escape(value, quote=True)}"')
        self._out.append("<" + " ".join(parts) + ">")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if self._drop_depth:
            if tag in _DROP_CONTENT_TAGS:
                self._drop_depth -= 1
            return
        if tag in _ALLOWED_TAGS and tag not in _VOID_TAGS:
            self._out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._drop_depth:
            self._out.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        if not self._drop_depth:
            self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self._drop_depth:
            self._out.append(f"&#{name};")

    def get(self) -> str:
        return "".join(self._out)


def sanitize_html(html: str) -> str:
    """回傳白名單淨化後的 HTML。輸入為 None 或空字串時原樣回傳。"""
    if not html:
        return html
    parser = _Sanitizer()
    parser.feed(html)
    parser.close()
    return parser.get()
