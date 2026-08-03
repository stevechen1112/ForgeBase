"""
信任內容標準（實效計畫 §4.4）

「信任驗證」facet 要有合格的內容才能被觸發。本模組定義最低品質標準，
對 page 做規則式檢查，結果可作為 CF 內容 brief 的輸入：

- 認證頁：可下載證書、標示效期、發證機構——不只是放 logo
- 產能頁：實際數字、設備與檢驗設備清單——讓買家判斷是否真工廠
- 案例頁：國家＋產業＋問題→解決敘事——而非「我們品質很好」
"""
import re
from typing import Any

_CERT_ISSUERS = ["iso", "ce", "ul", "fda", "tüv", "tuv", "sgs", "rohs", "reach", "bv", "intertek", "dnv"]
_COUNTRIES = [
    "germany", "usa", "united states", "japan", "uk", "france", "italy", "spain",
    "netherlands", "poland", "mexico", "brazil", "india", "vietnam", "thailand",
    "australia", "canada", "korea", "uae", "saudi", "turkey", "europe",
]
_INDUSTRIES = [
    "automotive", "construction", "aerospace", "medical", "electronics",
    "furniture", "bicycle", "motorcycle", "industrial", "marine", "energy", "diy",
]
_EQUIPMENT_TERMS = [
    "cnc", "machine", "machinery", "equipment", "lathe", "milling", "stamping",
    "injection", "inspection", "instrument", "hardness tester", "projector", "cmm",
    "salt spray", "torque tester",
]
_PROBLEM_TERMS = ["problem", "challenge", "issue", "pain point", "difficulty"]
_SOLUTION_TERMS = ["solution", "solved", "resolved", "helped", "delivered", "achieved", "reduced", "improved"]


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _has_download_link(body_html: str) -> bool:
    if re.search(r'href="[^"]+\.pdf"', body_html, re.IGNORECASE):
        return True
    return "download" in body_html.lower()


def _has_expiry(text: str) -> bool:
    if _has_any(text, ["valid until", "valid through", "expiry", "expires", "expiration", "issue date", "issued"]):
        return True
    return bool(re.search(r"\b(19|20)\d{2}\s*[-/]\s*(0?[1-9]|1[0-2])", text))


def _has_real_numbers(text: str) -> bool:
    matches = re.findall(
        r"\b\d[\d,]*\s?(?:pcs|pieces|units|sets|tons|sqm|m²|square meters|%|machines|lines|workers|staff|years)\b",
        text,
    )
    return len(matches) >= 2


def _check(page_type: str, text: str, body_html: str) -> list[dict[str, Any]]:
    if page_type == "certification":
        return [
            {
                "key": "cert_download",
                "label": "證書可下載（PDF 連結）",
                "passed": _has_download_link(body_html),
                "hint": "放可下載的證書檔，不只是放 logo",
            },
            {
                "key": "expiry_marked",
                "label": "標示效期／發證日期",
                "passed": _has_expiry(text),
                "hint": "標示效期讓買家確認證書仍然有效",
            },
            {
                "key": "issuer_named",
                "label": "具名發證／標準機構",
                "passed": _has_any(text, _CERT_ISSUERS),
                "hint": "寫明 ISO／CE／UL／SGS 等機構與標準編號",
            },
        ]
    if page_type == "capability":
        return [
            {
                "key": "real_numbers",
                "label": "實際產能數字",
                "passed": _has_real_numbers(text),
                "hint": "寫月產能、廠房面積、人力等可驗證數字",
            },
            {
                "key": "equipment_list",
                "label": "設備／檢驗設備清單",
                "passed": _has_any(text, _EQUIPMENT_TERMS),
                "hint": "列出生產設備與檢驗儀器，讓買家判斷是否真工廠",
            },
        ]
    if page_type in ("case", "case_study", "application"):
        return [
            {
                "key": "region_named",
                "label": "具名國家／地區",
                "passed": _has_any(text, _COUNTRIES),
                "hint": "寫「幫某國客戶」，提升外銷買家共鳴",
            },
            {
                "key": "industry_named",
                "label": "具名產業",
                "passed": _has_any(text, _INDUSTRIES),
                "hint": "寫明客戶所屬產業",
            },
            {
                "key": "problem_solution",
                "label": "問題→解決敘事",
                "passed": _has_any(text, _PROBLEM_TERMS) and _has_any(text, _SOLUTION_TERMS),
                "hint": "寫「解決什麼問題」，而非「我們品質很好」",
            },
        ]
    return []


def evaluate_trust_content(page_type: str, title: str, body_html: str) -> dict[str, Any]:
    """對信任類頁面做規則式品質檢查。非信任類頁面回傳 applicable=False。"""
    text = re.sub(r"<[^>]+>", " ", f"{title} {body_html or ''}").lower()
    body_lower = (body_html or "").lower()

    checklist = _check(page_type, text, body_lower)
    if not checklist:
        return {
            "applicable": False,
            "page_type": page_type,
            "score": None,
            "checklist": [],
            "message": "非信任內容類型（適用：certification / capability / case_study / application）",
        }

    passed = sum(1 for item in checklist if item["passed"])
    total = len(checklist)
    return {
        "applicable": True,
        "page_type": page_type,
        "score": round(passed / total * 100),
        "passed": passed,
        "total": total,
        "checklist": checklist,
    }
