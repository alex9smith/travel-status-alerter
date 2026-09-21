import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

BASE_URL = "https://api.tfl.gov.uk"
TIMEOUT_SECONDS = 20.0

HttpGet = Callable[[str], bytes]


class TflError(Exception):
    """Raised when the TfL API cannot be reached or returns something unexpected.

    Messages must never include the request URL, which contains the API key.
    """


@dataclass(frozen=True)
class LineStatus:
    """One status entry for a line. A line with several statuses yields several entries."""

    line_id: str
    name: str
    status: str
    reason: str | None


def urllib_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        body: bytes = response.read()
    return body


def build_url(lines: tuple[str, ...], api_key: str) -> str:
    query = urllib.parse.urlencode({"app_key": api_key})
    return f"{BASE_URL}/Line/{','.join(lines)}/Status?{query}"


def _require_str(mapping: dict[str, object], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise TflError(f"Unexpected TfL response: {context} has no string '{key}'")
    return value


def _optional_reason(mapping: dict[str, object]) -> str | None:
    value = mapping.get("reason")
    if value is None:
        return None
    if not isinstance(value, str):
        raise TflError("Unexpected TfL response: status 'reason' is not a string")
    return value.strip() or None


def _as_dict(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TflError(f"Unexpected TfL response: {context} is not an object")
    return value


def _parse_line(raw: object) -> tuple[LineStatus, ...]:
    line = _as_dict(raw, "line")
    line_id = _require_str(line, "id", "line")
    name = _require_str(line, "name", f"line '{line_id}'")
    entries = line.get("lineStatuses")
    if not isinstance(entries, list):
        raise TflError(f"Unexpected TfL response: line '{line_id}' has no 'lineStatuses' list")

    def parse_entry(entry: object) -> LineStatus:
        mapping = _as_dict(entry, f"status of line '{line_id}'")
        return LineStatus(
            line_id=line_id,
            name=name,
            status=_require_str(mapping, "statusSeverityDescription", f"status of '{line_id}'"),
            reason=_optional_reason(mapping),
        )

    return tuple(parse_entry(entry) for entry in entries)


def parse_statuses(payload: object) -> tuple[LineStatus, ...]:
    """Flatten a `/Line/{ids}/Status` response into one LineStatus per status entry."""
    if not isinstance(payload, list):
        raise TflError("Unexpected TfL response: expected a list of lines")
    return tuple(status for raw in payload for status in _parse_line(raw))


def fetch_statuses(
    lines: tuple[str, ...], api_key: str, http_get: HttpGet = urllib_get
) -> tuple[LineStatus, ...]:
    try:
        body = http_get(build_url(lines, api_key))
    except urllib.error.HTTPError as error:
        raise TflError(f"TfL API returned HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TflError(f"Could not reach TfL API: {error}") from None

    try:
        payload: object = json.loads(body)
    except ValueError:
        raise TflError("TfL API response was not valid JSON") from None
    return parse_statuses(payload)
