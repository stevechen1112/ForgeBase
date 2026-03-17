import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.services.chat_service import (
    ChatService,
)
from app.services.chat_orchestrator import finalize_generated_chat_response


TRANSCRIPTS = [
    {
        "label": "category",
        "context_page": "/products/torque-and-socket-tools",
        "context_entity_type": "category",
        "entity_summary": """Category name: Torque and Socket Tools
SEO description: Industrial torque wrenches, socket systems, and ratchet tools for OEM supply and distributor programs.
Description: Torque and socket tools for workshop service kits, maintenance programs, and private-label industrial distribution.
Representative products: 1/2 in Drive Industrial Torque Wrench (model: TW-500; summary: Adjustable click-type torque wrench for repeat workshop tightening; specs: Drive: 1/2 in; Torque Range: 40-210 Nm; Accuracy: +/-4%; Material: chrome vanadium steel) | Digital Torque Adapter (model: DTA-120; summary: Digital adapter for retrofit torque verification in field service; specs: Drive: 1/2 in; Torque Range: 30-200 Nm; Display: LCD) | 94-Piece Metric Socket Tool Set (model: SK-94M; summary: Multi-size metric socket assortment for service carts and distributor bundles; specs: Pieces: 94; Finish: matte chrome; Case: blow-molded)
Common FAQs: Q: Do you support OEM or private label orders? A: Yes. We support logo marking, custom packaging, and specification alignment for OEM and private label programs. | Q: What is your MOQ policy? A: MOQ depends on the product configuration, packaging, and whether the order is standard or OEM.
Common certifications: ISO 9001 (SGS): Certified quality management system for consistent production and inspection workflows. | CE (TUV): Selected torque tools can be supplied with CE-related documentation where applicable.""",
        "turns": [
            "We distribute torque tools in Europe. Which sub-types here are best for workshop service kits, and do you support OEM packaging?",
            "We want a mid-range assortment first, not the most expensive option. Which 2 to 3 SKUs would you shortlist and what MOQ details should we prepare?",
            "Before RFQ, what exact details do you still need from us to confirm fit and private-label scope?",
        ],
    },
    {
        "label": "application",
        "context_page": "/applications/automotive-aftermarket-service",
        "context_entity_type": "application",
        "entity_summary": """Application name: Automotive Aftermarket Service
Industry: Automotive Aftermarket
SEO description: Torque tools, socket systems, and service kits for automotive workshops, aftermarket distributors, and OEM tool programs.
Description: NorthForge supports automotive aftermarket buyers with fastening, torque-control, extraction, and maintenance-tool programs that fit workshop use, distributor resale, and branded service assortments.
Buyer challenge: Automotive buyers often struggle with inconsistent socket fit, weak case quality, incomplete service assortments, and torque tools that do not hold up across recurring workshop use.
Recommended solution direction: NorthForge combines torque tools, ratchets, socket systems, service kits, and workshop-ready packaging to help buyers build more coherent automotive maintenance ranges.
Related products: [Torque and Socket Tools] 1/2 in Drive Industrial Torque Wrench (model: TW-500; summary: Adjustable click-type torque wrench for repeat workshop tightening; specs: Drive: 1/2 in; Torque Range: 40-210 Nm; Accuracy: +/-4%; Material: chrome vanadium steel) | [Torque and Socket Tools] 94-Piece Metric Socket Tool Set (model: SK-94M; summary: Multi-size metric socket assortment for service carts and distributor bundles; specs: Pieces: 94; Finish: matte chrome; Case: blow-molded) | [Torque and Socket Tools] 72-Tooth Reversible Ratchet Handle (model: RH-72; summary: Fine-tooth ratchet for confined automotive maintenance access; specs: Teeth: 72; Drive: 3/8 in; Material: chrome vanadium steel)
Relevant FAQs: Q: Do you support OEM or private label orders? A: Yes. We support logo marking, custom packaging, and specification alignment for OEM and private label programs. | Q: What is your MOQ policy? A: MOQ depends on the product configuration, packaging, and whether the order is standard or OEM.
Relevant certifications: ISO 9001 (SGS): Certified quality management system for consistent production and inspection workflows.""",
        "turns": [
            "We want to build a mid-range automotive aftermarket assortment for distributors. Which products should we start with?",
            "Good. We also need private-label packaging and stable workshop durability. Which product in this set best covers torque-critical service work, and what should we confirm before RFQ?",
            "Please summarize the recommended starter bundle and the RFQ inputs you need from us.",
        ],
    },
]


async def main() -> None:
    service = ChatService(None)
    report = []

    for transcript in TRANSCRIPTS:
        recent_messages = []
        turns = []

        for question in transcript["turns"]:
            try:
                payload = await service._generate_reply(
                    context_page=transcript["context_page"],
                    context_entity_type=transcript["context_entity_type"],
                    entity_summary=transcript["entity_summary"],
                    faq_summary="",
                    cert_summary="",
                    recent_messages=recent_messages,
                    user_question=question,
                )
                payload = finalize_generated_chat_response(
                    user_question=question,
                    context_entity_type=transcript["context_entity_type"],
                    recent_messages=recent_messages,
                    payload=payload,
                )
            except Exception as exc:
                payload = {
                    "reply": "",
                    "suggested_action": "none",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            turns.append({"user": question, "assistant": payload})
            recent_messages.append(SimpleNamespace(role="user", content=question))
            recent_messages.append(
                SimpleNamespace(role="assistant", content=payload.get("reply", ""))
            )

        report.append(
            {
                "label": transcript["label"],
                "context_page": transcript["context_page"],
                "turns": turns,
            }
        )

    output_path = Path(
        "/Users/yuchuchen/Desktop/ForgeBase/AI_Product_Advisor_真實對話測試_2026-03-16.json"
    )
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(output_path)


if __name__ == "__main__":
    asyncio.run(main())