import io
import json
import urllib.error
import urllib.request
from collections.abc import Callable

import pytest

from travel_status_alerter import tfl
from travel_status_alerter.tfl import (
    LineStatus,
    TflError,
    build_url,
    fetch_statuses,
    parse_statuses,
    urllib_get,
)

SAMPLE = [
    {
        "$type": "Tfl.Api.Presentation.Entities.Line, Tfl.Api.Presentation.Entities",
        "id": "victoria",
        "name": "Victoria",
        "modeName": "tube",
        "lineStatuses": [
            {"statusSeverity": 10, "statusSeverityDescription": "Good Service"},
        ],
    },
    {
        "id": "northern",
        "name": "Northern",
        "modeName": "tube",
        "lineStatuses": [
            {
                "statusSeverity": 9,
                "statusSeverityDescription": "Minor Delays",
                "reason": "NORTHERN LINE: Minor delays due to a faulty train.",
            },
            {
                "statusSeverity": 6,
                "statusSeverityDescription": "Severe Delays",
            },
        ],
    },
]


def test_parse_flattens_one_entry_per_status() -> None:
    assert parse_statuses(SAMPLE) == (
        LineStatus(line_id="victoria", name="Victoria", status="Good Service", reason=None),
        LineStatus(
            line_id="northern",
            name="Northern",
            status="Minor Delays",
            reason="NORTHERN LINE: Minor delays due to a faulty train.",
        ),
        LineStatus(line_id="northern", name="Northern", status="Severe Delays", reason=None),
    )


def test_parse_treats_blank_reason_as_missing() -> None:
    payload = [
        {
            "id": "dlr",
            "name": "DLR",
            "lineStatuses": [{"statusSeverityDescription": "Part Closure", "reason": "  "}],
        }
    ]

    assert parse_statuses(payload)[0].reason is None


def test_parse_empty_list_is_empty_tuple() -> None:
    assert parse_statuses([]) == ()


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "victoria"},
        "nope",
        None,
        [42],
        [{"name": "Victoria", "lineStatuses": []}],
        [{"id": "victoria", "lineStatuses": []}],
        [{"id": "victoria", "name": "Victoria"}],
        [{"id": "victoria", "name": "Victoria", "lineStatuses": "x"}],
        [{"id": "victoria", "name": "Victoria", "lineStatuses": ["x"]}],
        [{"id": "victoria", "name": "Victoria", "lineStatuses": [{}]}],
        [{"id": 1, "name": "Victoria", "lineStatuses": []}],
        [
            {
                "id": "victoria",
                "name": "Victoria",
                "lineStatuses": [{"statusSeverityDescription": "X", "reason": 5}],
            }
        ],
    ],
)
def test_parse_rejects_malformed_payloads(payload: object) -> None:
    with pytest.raises(TflError):
        parse_statuses(payload)


def test_build_url_joins_lines_and_encodes_key() -> None:
    url = build_url(("victoria", "northern"), "a b&c")

    assert url == "https://api.tfl.gov.uk/Line/victoria,northern/Status?app_key=a+b%26c"


def fake_get(body: bytes) -> tuple[Callable[[str], bytes], list[str]]:
    calls: list[str] = []

    def get(url: str) -> bytes:
        calls.append(url)
        return body

    return get, calls


def test_fetch_statuses_requests_url_and_parses_response() -> None:
    get, calls = fake_get(json.dumps(SAMPLE).encode())

    statuses = fetch_statuses(("victoria", "northern"), "key", get)

    assert calls == [build_url(("victoria", "northern"), "key")]
    assert [s.line_id for s in statuses] == ["victoria", "northern", "northern"]


def test_fetch_statuses_wraps_invalid_json() -> None:
    get, _ = fake_get(b"<html>Bad gateway</html>")

    with pytest.raises(TflError, match="valid JSON"):
        fetch_statuses(("victoria",), "key", get)


def test_fetch_statuses_wraps_transport_errors_without_leaking_the_key() -> None:
    def get(url: str) -> bytes:
        raise urllib.error.HTTPError(url, 500, "Server Error", {}, None)  # type: ignore[arg-type]

    with pytest.raises(TflError) as excinfo:
        fetch_statuses(("victoria",), "super-secret", get)

    assert "500" in str(excinfo.value)
    assert "super-secret" not in str(excinfo.value)


def test_fetch_statuses_wraps_network_and_timeout_errors() -> None:
    def get(url: str) -> bytes:
        raise TimeoutError("timed out")

    with pytest.raises(TflError, match="timed out"):
        fetch_statuses(("victoria",), "key", get)


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self


def test_urllib_get_returns_body_and_uses_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(url: str, timeout: float) -> FakeResponse:
        seen.update(url=url, timeout=timeout)
        return FakeResponse(b"body")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert urllib_get("https://example.test/x") == b"body"
    assert seen == {"url": "https://example.test/x", "timeout": tfl.TIMEOUT_SECONDS}
