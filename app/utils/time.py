"""Time and datetime utilities."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(timezone.utc)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%dT%H:%M:%SZ") -> str:
    """Format datetime to ISO string.

    Args:
        dt: Datetime to format
        fmt: Format string (default ISO 8601)

    Returns:
        Formatted datetime string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(fmt)


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string.

    Args:
        dt_str: ISO format datetime string

    Returns:
        Parsed datetime object in UTC
    """
    # Handle various ISO formats
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(dt_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    raise ValueError(f"Could not parse datetime: {dt_str}")
