from html import escape

from travel_status_alerter.tfl import LineStatus

# Telegram rejects messages longer than 4096 characters.
MAX_MESSAGE_LENGTH = 4096
MAX_REASON_LENGTH = 500

GOOD_SERVICE = "good service"
HEADER = "🚨 <b>TfL disruption</b>"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _format_entry(entry: LineStatus) -> str:
    heading = f"<b>{escape(entry.name)}</b>: {escape(entry.status)}"
    if entry.reason is None:
        return heading
    return f"{heading}\n{escape(_truncate(entry.reason, MAX_REASON_LENGTH))}"


def _footer(dropped: int) -> str:
    return f"…and {dropped} more"


def _fit(entries: tuple[str, ...]) -> str:
    """Join entries under the header, dropping trailing ones (with a note) if too long."""
    for kept in range(len(entries), -1, -1):
        dropped = len(entries) - kept
        parts = (HEADER, *entries[:kept], *((_footer(dropped),) if dropped else ()))
        message = "\n\n".join(parts)
        if len(message) <= MAX_MESSAGE_LENGTH:
            return message
    return HEADER  # pragma: no cover - the header alone always fits


def format_alert(statuses: tuple[LineStatus, ...]) -> str | None:
    """Build an HTML Telegram message for disrupted lines, or None if all is well."""
    entries = tuple(
        _format_entry(entry) for entry in statuses if entry.status.strip().lower() != GOOD_SERVICE
    )
    return _fit(entries) if entries else None


def format_error(description: str) -> str:
    return f"⚠️ <b>TfL status check failed</b>\n{escape(description)}"
