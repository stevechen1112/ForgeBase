"""Repair demo content encoding, titles, and Traditional Chinese FAQ coverage.

Revision ID: 0066_asset_locale_repairs
Revises: 0065_retire_intake_ai_content
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0066_asset_locale_repairs"
down_revision = "0065_retire_intake_ai_content"
branch_labels = None
depends_on = None


FAQ_TRANSLATIONS = [
    (10, "Can NorthForge support private-label branding on tool sets and cases?", "NorthForge 可以在工具組與工具箱上提供自有品牌標示嗎？", "<p>可以。依專案範圍與訂單形式，NorthForge 可為指定產品線、模塑工具箱、包裝內卡、外箱標示與條碼標籤提供自有品牌配置。</p>"),
    (20, "What is your typical MOQ for standard catalog tools?", "標準目錄工具的一般最低訂購量是多少？", "<p>最低訂購量取決於產品類型、包裝形式，以及採用標準包裝或自有品牌包裝。標準品通常比客製專案有更彈性的起訂數量。</p>"),
    (30, "Do you offer OEM or ODM development for custom hand tools?", "你們是否提供客製手工具的 OEM 或 ODM 開發？", "<p>NorthForge 支援 OEM 與部分 ODM 開發，包括 Logo 標示、包裝調整、品項組合規劃，以及部分產品修改或依圖面進行可行性評估。</p>"),
    (40, "Can you provide inspection reports before shipment?", "出貨前可以提供檢驗報告嗎？", "<p>NorthForge 可提供內部檢驗摘要；買方如有要求，也可協調第三方出貨前檢驗。實際文件範圍需依產品與訂單確認。</p>"),
    (50, "Do insulated tools come with supporting compliance documentation?", "絕緣工具是否附有相關合規文件？", "<p>針對專業電氣市場的絕緣工具專案，NorthForge 可協助整理合規相關文件與製程說明；實際適用標準與文件仍需依型號及目標市場確認。</p>"),
    (60, "Can you build mixed toolkits with custom item combinations?", "可以依指定品項組合製作混合工具組嗎？", "<p>可以。NorthForge 支援混合 SKU 工具組，包括 EVA 泡棉配置、模塑工具箱、品項組合規劃與自有品牌包裝。</p>"),
    (70, "How do you manage consistency between sample approval and mass production?", "如何維持核准樣品與量產之間的一致性？", "<p>NorthForge 透過圖面與版本控管、核准確認、檢驗流程及重複訂單管理，降低樣品與量產訂單之間可避免的差異。</p>"),
    (80, "Do you work with importers and distributors, or only large brands?", "你們服務進口商與經銷商，還是只服務大型品牌？", "<p>NorthForge 的服務對象包含進口商、經銷商、自有品牌與工業買家，定位以制度化的中型專案為主，不只承接大型企業帳戶。</p>"),
    (90, "Can you provide RoHS or REACH-related material declarations?", "可以提供 RoHS 或 REACH 相關材質聲明嗎？", "<p>對於需要掌握出口專案材質合規資訊的買方，NorthForge 可協助處理 RoHS 與 REACH 相關文件；實際文件內容需依產品與供應鏈資料確認。</p>"),
    (100, "What packaging options are available for OEM customers?", "OEM 客戶可以選擇哪些包裝方式？", "<p>依專案需求，可討論零售盒、模塑工具箱、EVA 內襯、標籤、條碼貼紙、說明書與出口外箱客製等包裝方式。</p>"),
    (110, "Can NorthForge support field-service and contractor kits?", "NorthForge 可以支援外勤維修與承包商工具組嗎？", "<p>可以。NorthForge 可為外勤技師與承包商供應專案規劃精簡維修工具組、電工工具組與行動維護組合。</p>"),
    (120, "Do you accept mixed-SKU repeat orders?", "你們接受混合 SKU 的重複訂單嗎？", "<p>可以。在品項組合、包裝規則與標示要求明確的情況下，NorthForge 可支援混合 SKU 的持續補貨專案。</p>"),
    (130, "Can you support barcode and carton label requirements for retailers or distributors?", "可以配合零售商或經銷商的條碼與外箱標籤要求嗎？", "<p>可以。條碼標籤、外箱標示與包裝結構細節可納入自有品牌及經銷通路專案一併管理。</p>"),
    (140, "What kinds of buyers usually work with NorthForge?", "NorthForge 通常與哪些類型的買家合作？", "<p>常見買家包括手工具進口商、工業經銷商、汽車售後市場供應商、承包商通路工具品牌，以及自有品牌採購團隊。</p>"),
    (150, "Can you help build retail-ready hand tool sets?", "可以協助製作可直接上架銷售的手工具組嗎？", "<p>可以。NorthForge 可協助規劃混合手工具組、包裝與自有品牌配置，供買方推出或擴充品牌產品線。</p>"),
    (160, "Do you support automotive-specific tool programs?", "你們支援汽車用途的專用工具專案嗎？", "<p>可以。可討論的品項包括扭力工具、套筒組、火星塞工具、拔卸工具、煞車維修工具組、飾板工具與車間工具組合。</p>"),
    (170, "Can I request samples before placing a production order?", "正式下量產訂單前可以先申請樣品嗎？", "<p>是否可提供樣品取決於品項與專案類型；NorthForge 可在制度化的 OEM 與重複訂單流程中安排樣品評估與核准。</p>"),
    (180, "Why do buyers choose NorthForge instead of price-only suppliers?", "買家為什麼選擇 NorthForge，而不只比較最低價格？", "<p>重視重複訂單一致性、包裝執行、文件清楚度與商務溝通效率的買家，通常不會只以最低單價作為選擇依據。</p>"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Repair the bad UTF-8 conversion in every global torque-tool variant.
    conn.execute(
        sa.text(
            """
            UPDATE products
            SET specifications = replace(specifications, '簣4%', '±4%'),
                updated_at = now()
            WHERE tenant_id IS NULL
              AND specifications LIKE '%簣4%'
            """
        )
    )

    # Remove stale manual-review markers and version labels from the demo row.
    conn.execute(
        sa.text(
            """
            UPDATE products
            SET product_name = CASE
                    WHEN locale = 'zh-tw' THEN '1/2 吋工業扭力扳手'
                    ELSE product_name
                END,
                seo_title = CASE
                    WHEN locale = 'zh-tw' THEN '1/2 吋工業扭力扳手'
                    WHEN locale = 'en' THEN '1/2 in Drive Industrial Torque Wrench'
                    ELSE seo_title
                END,
                updated_at = now()
            WHERE tenant_id IS NULL
              AND model_number = 'NFT-TW500'
              AND locale IN ('en', 'zh-tw')
            """
        )
    )

    # The root metadata template appends the brand. Strip duplicated trailing
    # suffixes from old seed records while preserving titles that begin with it.
    for table in (
        "products",
        "product_categories",
        "applications",
        "comparison_topics",
        "pages",
    ):
        conn.execute(
            sa.text(
                f"""
                UPDATE {table}
                SET seo_title = regexp_replace(seo_title, '\\s+\\|\\s+NorthForge Tools$', '')
                WHERE tenant_id IS NULL
                  AND seo_title ~ '\\s+\\|\\s+NorthForge Tools$'
                """
            )
        )

    # Seed human-reviewed Traditional Chinese FAQ variants from the global
    # English demo set. The shared variant_key preserves cross-locale pairing.
    insert_translation = sa.text(
        """
        INSERT INTO faq_items (
            id, tenant_id, variant_key, question, answer, category_tag,
            locale, sort_order, status, created_at, updated_at
        )
        SELECT
            :id, source.tenant_id, source.variant_key, :question, :answer,
            source.category_tag, 'zh-tw', :sort_order, source.status, now(), now()
        FROM faq_items AS source
        WHERE source.tenant_id IS NULL
          AND source.locale = 'en'
          AND source.question = :source_question
          AND NOT EXISTS (
              SELECT 1
              FROM faq_items AS existing
              WHERE existing.tenant_id IS NULL
                AND existing.locale = 'zh-tw'
                AND existing.variant_key = source.variant_key
          )
        """
    )
    for sort_order, source_question, question, answer in FAQ_TRANSLATIONS:
        conn.execute(
            insert_translation,
            {
                "id": uuid.uuid4(),
                "source_question": source_question,
                "question": question,
                "answer": answer,
                "sort_order": sort_order,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    delete_translation = sa.text(
        """
        DELETE FROM faq_items
        WHERE tenant_id IS NULL
          AND locale = 'zh-tw'
          AND question = :question
        """
    )
    for _, _, question, _ in FAQ_TRANSLATIONS:
        conn.execute(delete_translation, {"question": question})
