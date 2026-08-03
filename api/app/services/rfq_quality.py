"""Rule-based Lead Quality Score for RFQs (v1).

設計依據：FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md §5.1。
五個維度：規格完整度／商業可行／身分品質／貿易條件／風險。
每個加分都產生人可讀的 reason（可解釋性是驗收要求），
分數 clamp 在 0–100。之後若要換 ML 模型，保持同樣的
(score, reasons) 介面即可替換。
"""
from typing import Any, Optional

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "qq.com",
    "163.com", "aol.com", "mail.com", "protonmail.com", "yandex.com",
}

SPAM_KEYWORDS = {
    "seo service", "seo services", "crypto", "casino", "forex",
    "binary option", "guest post", "backlink", "loan offer",
}

VALID_INCOTERMS = {
    "EXW", "FCA", "FAS", "FOB", "CFR", "CIF",
    "CPT", "CIP", "DAP", "DPU", "DDP",
}


def score_rfq_quality(body: Any) -> tuple[int, list[str]]:
    """Compute (quality_score, reasons) from an RFQFormIn-like object.

    只讀取屬性、不寫入；trade-terms 屬性不存在時視為未填（向後相容）。
    """
    score = 0
    reasons: list[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        sign = "+" if points >= 0 else ""
        reasons.append(f"{sign}{points} {reason}")

    def get(name: str) -> Optional[Any]:
        return getattr(body, name, None)

    specs = (get("specifications") or "").strip()
    msg = (get("message") or "").strip()
    qty = (get("quantity") or "").strip()

    # ── 規格完整度 ─────────────────────────────────────────────
    if len(specs) >= 50:
        add(15, "附詳細規格說明")
    elif specs:
        add(5, "有規格說明（簡短）")
    if qty:
        add(10, "提供數量")
    if get("product_ids"):
        add(5, "指定產品")
    if len(msg) >= 100:
        add(5, "需求描述完整")

    # ── 商業可行 ───────────────────────────────────────────────
    if get("timeline"):
        add(10, "提供採購時程")
    if qty and any(ch.isdigit() for ch in qty):
        add(5, "數量含具體數字")

    # ── 身分品質 ───────────────────────────────────────────────
    if get("company_name"):
        add(10, "提供公司名稱")
    if get("country"):
        add(5, "提供國家")
    if get("job_title"):
        add(5, "提供職稱")
    email = (get("email") or "").lower()
    domain = email.split("@")[-1] if "@" in email else ""
    if domain in FREE_EMAIL_DOMAINS:
        add(-10, f"使用免費信箱（{domain}）")

    # ── 貿易條件（強採購訊號）─────────────────────────────────
    incoterm = get("incoterm")
    if incoterm:
        add(15, f"指定貿易條件 {incoterm}")
    if get("annual_volume"):
        add(10, "提供年需求量")
    if get("is_trial_order") is not None:
        add(5, "表明試單／量產需求")
    certs = get("required_certs") or []
    if certs:
        add(10, f"指定認證（{', '.join(certs[:3])}）")
    if get("target_price"):
        add(5, "提供目標價")

    # ── 風險 ───────────────────────────────────────────────────
    text_all = f"{msg} {specs}".lower()
    for kw in SPAM_KEYWORDS:
        if kw in text_all:
            add(-30, f"疑似垃圾內容（{kw}）")
            break
    if len(msg) < 20 and not specs:
        add(-10, "需求描述過短且無規格")

    return max(0, min(100, score)), reasons
