from datetime import datetime, timezone


def utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def isoformat_utc(value: datetime | None) -> str | None:
    """Serialize database timestamps as unambiguous UTC ISO-8601 values.

    ForgeBase stores operational timestamps as UTC without timezone metadata.
    Appending ``Z`` prevents browsers from treating those values as local time
    and shifting follow-up reminders by the user's UTC offset.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return f"{value.isoformat()}Z"
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
