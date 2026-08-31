"""Single-product capability access and operational governance."""
from __future__ import annotations

from typing import Any

from app.models.tenant import Tenant

FEATURE_CATALOG: dict[str, dict[str, Any]] = {
    "managed_website": {
        "label": "受管網站交付與維護", "group": "核心交付（固定開啟）",
        "description": "由 ForgeBase 完成網站製作與交付，租戶維護既有內容。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "product_content": {
        "label": "商品與官網內容管理", "group": "核心交付（固定開啟）",
        "description": "維護商品、分類、頁面、應用、FAQ、認證與廠能。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "asset_library": {
        "label": "圖片與檔案管理", "group": "核心交付（固定開啟）",
        "description": "管理網站使用的圖片、文件與替代文字。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "rfq_workspace": {
        "label": "RFQ 詢價工作台", "group": "核心交付（固定開啟）",
        "description": "收件、品質、狀態、指派、備註、歷程與匯出。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "task_sla": {
        "label": "待辦、期限與 SLA", "group": "核心交付（固定開啟）",
        "description": "處理跟進任務、期限、逾期與責任歸屬。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "outcomes_dashboard": {
        "label": "成果與漏斗總覽", "group": "成效與營運",
        "description": "整合訪客、詢價、商機狀態、來源與成交結果。", "configurable": True,
    },
    "team_roles": {
        "label": "團隊成員與角色", "group": "核心交付（固定開啟）",
        "description": "管理租戶成員及 Owner、管理員、行銷與業務角色。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "support_requests": {
        "label": "網站修改與支援", "group": "核心交付（固定開啟）",
        "description": "向 ForgeBase 提交網站調整與支援需求。", "configurable": False,
        "status": "core_required", "locked_value": True,
    },
    "multilingual": {
        "label": "多語內容與語系網站", "group": "網站與內容",
        "description": "維護來源語系與買方語系內容；可產英文草稿，確認上架後才公開。", "configurable": True,
    },
    "full_tracking": {
        "label": "訪客與內容成效追蹤", "group": "買家旅程",
        "description": "保存訪客歷程、來源與內容成效。", "configurable": True,
    },
    "intent_scoring": {
        "label": "買家關注度", "group": "買家旅程",
        "description": "依站內行為計算關注分數與原因。", "configurable": True,
    },
    "ai_advisor": {
        "label": "AI 產品顧問", "group": "AI 客服與詢價",
        "description": "官網公開客服：依已發布資料回答，並協助整理詢價條件。", "configurable": True,
    },
    "chat_handoff": {
        "label": "官網對話與人工接手", "group": "AI 客服與詢價",
        "description": "查看官網對話、來源與轉交的詢價草稿。", "configurable": True,
    },
    "notifications": {
        "label": "RFQ 與營運通知", "group": "業務營運",
        "description": "RFQ、指派、逾期、官網對話轉交與日常營運通知。", "configurable": True,
    },
    "follow_up_reminders": {
        "label": "跟進提醒", "group": "業務營運",
        "description": "案件待辦、期限、逾期與提醒。", "configurable": True,
    },
    "advanced_content": {
        "label": "進階頁面與比較內容", "group": "網站與內容",
        "description": "新增自訂頁面與產品比較內容。", "configurable": True,
    },
    "audience_segments": {
        "label": "買家分群", "group": "買家旅程",
        "description": "依訪客與行為條件建立可重算分群。", "configurable": True,
    },
    "dynamic_cta": {
        "label": "動態 CTA", "group": "買家旅程",
        "description": "依關注階段與頁面情境選擇行動按鈕。", "configurable": True,
    },
    "advanced_intent_rules": {
        "label": "進階評分規則", "group": "買家旅程",
        "description": "自訂各種行為對買家關注分數的影響。", "configurable": True,
    },
    "nurture_email": {
        "label": "培育與跟進郵件", "group": "外聯與跟進",
        "description": "建立序列；寄送仍保留人工核准與安全限制。", "configurable": True,
    },
    "seo_redirects": {
        "label": "SEO 網址轉址", "group": "網站與內容",
        "description": "管理舊網址至新內容的 301／302 轉址。", "configurable": True,
    },
    "integrations": {
        "label": "寄件服務", "group": "潛在買家跟進",
        "description": "提供人工核准後的郵件寄送；技術憑證由 ForgeBase 維護。", "configurable": True,
    },
    "company_identification": {
        "label": "企業辨識與聯絡人候選", "group": "待第三方資源",
        "description": "需完成供應商 POC、OEM 授權與資料品質驗證後開放。", "configurable": False,
        "status": "awaiting_provider",
    },
    "ai_relation_recommendations": {
        "label": "AI 關聯內容建議", "group": "退場觀察",
        "description": "推薦 API 預設關閉；已發布的人工關聯資料不受影響。", "configurable": True,
        "status": "retirement_observation",
    },
    "contact_enrichment": {
        "label": "企業聯絡窗口候選", "group": "核心成長引擎（建置中）",
        "description": "由已確認公司尋找相關商務窗口；需完成資料授權及品質驗證。", "configurable": False,
        "status": "core_in_development",
    },
    "journey_personalization": {
        "label": "旅程個人化草稿", "group": "核心成長引擎（建置中）",
        "description": "依固定旅程證據與已發布知識產生可審核外聯草稿。", "configurable": False,
        "status": "core_in_development",
    },
    "outreach_review": {
        "label": "外聯審核工作台", "group": "核心成長引擎（建置中）",
        "description": "檢查候選、證據與信件內容後才允許後續寄送。", "configurable": False,
        "status": "core_in_development",
    },
    "outreach_send": {
        "label": "受控個人化外聯", "group": "核心成長引擎（試行）",
        "description": "具備核准、頻率、退訂、抑制、冪等與全域停止開關的寄送。", "configurable": True,
        "status": "pilot",
    },
    "inbound_reply": {
        "label": "外聯回覆接收", "group": "核心成長引擎（試行）",
        "description": "接收、關聯並安全分類對方回覆。", "configurable": True,
        "status": "pilot",
    },
    "sales_handoff": {
        "label": "真人業務接手", "group": "核心成長引擎（試行）",
        "description": "將有價值回覆轉為可指派、具 SLA 的業務任務。", "configurable": True,
        "status": "pilot",
    },
    "closed_loop_attribution": {
        "label": "RFQ／成交閉環歸因", "group": "核心成長引擎（試行）",
        "description": "串聯訪客、公司、窗口、外聯、回覆、RFQ 與成交成果。", "configurable": True,
        "status": "pilot",
    },
    "automation_runs": {
        "label": "自動任務執行中心", "group": "待外部執行環境",
        "description": "需完成 AgentOS 多租戶隔離與正式服務設定後開放。", "configurable": False,
        "status": "service_required",
    },
}

_DEFAULT_ENABLED_STATUSES = {"core_required", "available"}


def _default_enabled(meta: dict[str, Any]) -> bool:
    if "locked_value" in meta:
        return bool(meta["locked_value"])
    return meta.get("status", "available") in _DEFAULT_ENABLED_STATUSES


def feature_catalog_payload() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            **meta,
            "default_enabled": _default_enabled(meta),
            "status": meta.get("status", "available"),
        }
        for key, meta in FEATURE_CATALOG.items()
    ]


def resolve_tenant_features(tenant: Tenant) -> dict[str, bool]:
    resolved = {
        key: _default_enabled(meta)
        for key, meta in FEATURE_CATALOG.items()
    }
    overrides = tenant.feature_overrides if isinstance(tenant.feature_overrides, dict) else {}
    for key, enabled in overrides.items():
        if key in FEATURE_CATALOG and FEATURE_CATALOG[key].get("configurable", True):
            resolved[key] = bool(enabled)
    # Fixed core modules and pending external modules cannot be changed through
    # a crafted payload or stale database row.
    for key, meta in FEATURE_CATALOG.items():
        if not meta.get("configurable", True):
            resolved[key] = bool(meta.get("locked_value", False))
    return resolved


def tenant_has_feature(tenant: Tenant, feature: str) -> bool:
    return resolve_tenant_features(tenant).get(feature, False)

# Capability key for the Email Nurture Engine (sequence / step / enrollment).
NURTURE_FEATURE = "nurture_email"
