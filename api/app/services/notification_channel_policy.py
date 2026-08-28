"""Fail-closed policy for notification channels in retirement observation."""

RETIRED_NOTIFICATION_CHANNELS = frozenset({"telegram", "line"})
ACTIVE_NOTIFICATION_CHANNELS = frozenset({"email", "in_app"})


def retirement_candidate_for_channel(channel: str) -> str | None:
    normalized = channel.strip().lower()
    if normalized in RETIRED_NOTIFICATION_CHANNELS:
        return f"notification_{normalized}"
    return None
