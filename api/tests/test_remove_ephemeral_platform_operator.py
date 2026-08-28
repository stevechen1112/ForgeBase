from __future__ import annotations

import pytest
from pydantic import EmailStr, TypeAdapter
from scripts.remove_ephemeral_platform_operator import expected_ephemeral_email


def test_expected_ephemeral_email_is_exactly_scoped_to_the_workflow_run() -> None:
    email = expected_ephemeral_email("33134643328", "2")
    assert email == "production-browser-33134643328-2@forgebase.com"
    assert TypeAdapter(EmailStr).validate_python(email) == email


@pytest.mark.parametrize(
    ("run_id", "run_attempt"),
    [("", "1"), ("0", "1"), ("-1", "1"), ("12x", "1"), ("12", "0")],
)
def test_expected_ephemeral_email_rejects_unscoped_values(
    run_id: str, run_attempt: str
) -> None:
    with pytest.raises(ValueError):
        expected_ephemeral_email(run_id, run_attempt)
