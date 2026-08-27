#!/usr/bin/env python3
"""Run the hermetic public-advisor eval and emit release-gate evidence."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

API_DIR = Path(__file__).resolve().parents[1]
ROOT = API_DIR.parent
ARTIFACT_DIR = ROOT / "artifacts" / "ai-knowledge-eval"
sys.path.insert(0, str(API_DIR))

from app.services.knowledge_eval import run_frozen_eval


def main() -> int:
    result = run_frozen_eval()
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["network_calls"] = 0
    result["live_model_used"] = False
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    suite = ElementTree.Element(
        "testsuite",
        name="ai-knowledge-eval",
        tests=str(result["case_count"]),
        failures=str(result["failed_count"]),
    )
    for row in result["results"]:
        case = ElementTree.SubElement(suite, "testcase", name=row["id"])
        if not row["passed"]:
            detail = "; ".join(row["failures"])
            ElementTree.SubElement(case, "failure", message=detail).text = detail
    ElementTree.ElementTree(suite).write(
        ARTIFACT_DIR / "junit.xml", encoding="utf-8", xml_declaration=True
    )

    print(
        f"AI knowledge eval: {result['passed_count']}/{result['case_count']} "
        f"cases passed; thresholds="
        f"{'passed' if all(result['threshold_checks'].values()) else 'failed'}"
    )
    if not result["passed"]:
        for row in result["results"]:
            if not row["passed"]:
                print(f"FAIL {row['id']}: {', '.join(row['failures'])}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
