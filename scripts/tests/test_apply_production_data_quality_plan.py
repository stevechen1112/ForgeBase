import json
import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "apply_production_data_quality_plan.py"
SPEC = importlib.util.spec_from_file_location("apply_production_data_quality_plan", SCRIPT_PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
parse_rfq_plan = module.parse_rfq_plan


def test_parse_rfq_plan_requires_exact_replay_safe_identity() -> None:
    payload = json.dumps(
        [{"id": "000ac814-dd61-4e44-8f55-06259cbbbee3", "rfq_number": "RFQ-20260817-001"}]
    )
    assert parse_rfq_plan(payload) == [
        {"id": "000ac814-dd61-4e44-8f55-06259cbbbee3", "rfq_number": "RFQ-20260817-001"}
    ]


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        '[{"id":"not-a-uuid","rfq_number":"RFQ-1"}]',
        '[{"id":"000ac814-dd61-4e44-8f55-06259cbbbee3","rfq_number":"bad"}]',
        '[{"id":"000ac814-dd61-4e44-8f55-06259cbbbee3","rfq_number":"RFQ-1","extra":true}]',
    ],
)
def test_parse_rfq_plan_rejects_ambiguous_or_unscoped_input(payload: str) -> None:
    with pytest.raises(ValueError):
        parse_rfq_plan(payload)
