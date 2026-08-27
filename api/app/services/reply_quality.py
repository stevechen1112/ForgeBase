"""
回覆品質輔助（實效計畫 §5.4）

第一封回覆的品質決定是否進入買家 shortlist。提供：
- 回覆前 checklist：規格缺口、圖面、包裝、認證需求、建議反問的問題
- Quote Readiness：報價前檢查規格／圖面／包裝／認證缺口（先人工 checklist）
- 範本匹配：依買家國家／語系從範本庫挑選
"""
import json
from typing import Any, Optional

from app.models.reply_template import ReplyTemplate
from app.models.rfq_request import RFQRequest

_PACKAGING_TERMS = ["packaging", "package", "carton", "pallet", "box", "label", "packing"]
_DRAWING_TERMS = ["drawing", "blueprint", "cad", "dxf", "step file", "attachment", "diagram", "圖"]


def _form(rfq: RFQRequest) -> dict:
    if not rfq.form_data:
        return {}
    try:
        return json.loads(rfq.form_data)
    except (json.JSONDecodeError, TypeError):
        return {}


def _certs(rfq: RFQRequest) -> list[str]:
    if not rfq.required_certs_json:
        return []
    try:
        value = json.loads(rfq.required_certs_json)
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def build_reply_checklist(rfq: RFQRequest) -> list[dict[str, Any]]:
    """回覆前 checklist（業務視角，中文標籤＋英文建議反問句）。"""
    form = _form(rfq)
    text = " ".join(
        str(form.get(k) or "") for k in ("specifications", "message", "quantity")
    ).lower()

    items: list[dict[str, Any]] = []

    specs_missing = not (form.get("specifications") or "").strip()
    items.append({
        "key": "specs",
        "label": "規格完整度（材料／尺寸／標準）",
        "ok": not specs_missing,
        "ask": "Could you share the key specifications — material, dimensions, and applicable standard?" if specs_missing else None,
    })

    has_drawing = _has_any(text, _DRAWING_TERMS)
    items.append({
        "key": "drawing",
        "label": "圖面／附件",
        "ok": has_drawing,
        "ask": "Do you have drawings or CAD files you can share for accurate quoting?" if not has_drawing else None,
    })

    has_packaging = _has_any(text, _PACKAGING_TERMS)
    items.append({
        "key": "packaging",
        "label": "包裝／標籤需求",
        "ok": has_packaging,
        "ask": "Any packaging or labeling requirements (retail box, private label, pallet spec)?" if not has_packaging else None,
    })

    certs = _certs(rfq)
    items.append({
        "key": "certs",
        "label": "認證需求",
        "ok": bool(certs),
        "ask": "Which certifications does your market require (e.g. CE, FDA, UL, RoHS)?" if not certs else None,
    })

    items.append({
        "key": "incoterm",
        "label": "貿易條件（Incoterms／目的港）",
        "ok": bool(rfq.incoterm),
        "ask": "Which Incoterm and destination port should we quote on?" if not rfq.incoterm else None,
    })

    items.append({
        "key": "volume",
        "label": "數量／年需求量",
        "ok": bool((form.get("quantity") or "").strip() or rfq.annual_volume),
        "ask": "What is the trial quantity and expected annual volume?" if not ((form.get("quantity") or "").strip() or rfq.annual_volume) else None,
    })

    return items


def quote_readiness(rfq: RFQRequest) -> dict[str, Any]:
    """報價前檢查：可報價比例＋缺口（§5.4 Quote Readiness，先人工 checklist）。"""
    checklist = build_reply_checklist(rfq)
    ok_count = sum(1 for item in checklist if item["ok"])
    total = len(checklist)
    score = round(ok_count / total * 100)
    gaps = [item["label"] for item in checklist if not item["ok"]]
    return {
        "score": score,
        "ready": score >= 80,
        "checked": ok_count,
        "total": total,
        "gaps": gaps,
        "message": "可進入報價" if score >= 80 else "報價前建議先補齊缺口",
    }


def suggested_questions(rfq: RFQRequest) -> list[str]:
    """建議反問買家的問題（依缺口，最多 4 題）。"""
    return [item["ask"] for item in build_reply_checklist(rfq) if item["ask"]][:4]


def match_templates(
    templates: list[ReplyTemplate],
    *,
    country: Optional[str] = None,
    locale: str = "en",
    product_line: Optional[str] = None,
) -> list[ReplyTemplate]:
    """依買家條件排序範本：完全匹配（國家＋產品線）優先，通用範本墊底。"""
    def _rank(t: ReplyTemplate) -> tuple[int, int, int]:
        country_hit = 0 if country and t.country == country else (1 if t.country is None else 2)
        line_hit = 0 if product_line and t.product_line == product_line else (1 if not t.product_line else 2)
        locale_hit = 0 if t.locale == locale else 1
        return (country_hit, line_hit, locale_hit)

    return sorted(templates, key=_rank)


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)
