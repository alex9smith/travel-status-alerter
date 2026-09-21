import io
import json
import urllib.error
import urllib.request

import pytest

from travel_status_alerter import telegram
from travel_status_alerter.telegram import (
    TelegramError,
    build_payload,
    build_url,
    send_message,
    urllib_post,
)

TOKEN = "123:secret-token"


def test_build_url_embeds_bot_token() -> None:
    assert build_url(TOKEN) == "https://api.telegram.org/bot123:secret-token/sendMessage"


def test_build_payload_uses_html_parse_mode() -> None:
    assert json.loads(build_payload("-100123", "<b>hi</b>")) == {
        "chat_id": "-100123",
        "text": "<b>hi</b>",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


def test_send_message_posts_payload_to_bot_url() -> None:
    calls: list[tuple[str, bytes]] = []

    def post(url: str, body: bytes) -> bytes:
        calls.append((url, body))
        return b'{"ok": true}'

    send_message(TOKEN, "-100123", "hello", post)

    assert calls == [(build_url(TOKEN), build_payload("-100123", "hello"))]


def test_send_message_rejects_ok_false_response() -> None:
    def post(url: str, body: bytes) -> bytes:
        return b'{"ok": false, "description": "Bad Request: chat not found"}'

    with pytest.raises(TelegramError, match="chat not found"):
        send_message(TOKEN, "1", "x", post)


@pytest.mark.parametrize("body", [b"<html>", b"[]", b'{"result": 1}'])
def test_send_message_rejects_unexpected_responses(body: bytes) -> None:
    def post(url: str, request_body: bytes) -> bytes:
        return body

    with pytest.raises(TelegramError):
        send_message(TOKEN, "1", "x", post)


def test_http_errors_are_wrapped_without_leaking_the_token() -> None:
    def post(url: str, body: bytes) -> bytes:
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)  # type: ignore[arg-type]

    with pytest.raises(TelegramError) as excinfo:
        send_message(TOKEN, "1", "x", post)

    assert "401" in str(excinfo.value)
    assert "secret-token" not in str(excinfo.value)


def test_network_errors_are_wrapped() -> None:
    def post(url: str, body: bytes) -> bytes:
        raise urllib.error.URLError("connection refused")

    with pytest.raises(TelegramError, match="connection refused"):
        send_message(TOKEN, "1", "x", post)


class FakeResponse(io.BytesIO):
    def __enter__(self) -> "FakeResponse":
        return self


def test_urllib_post_sends_json_request(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        seen.update(
            url=request.full_url,
            data=request.data,
            method=request.get_method(),
            content_type=request.get_header("Content-type"),
            timeout=timeout,
        )
        return FakeResponse(b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert urllib_post("https://example.test/x", b"{}") == b'{"ok": true}'
    assert seen == {
        "url": "https://example.test/x",
        "data": b"{}",
        "method": "POST",
        "content_type": "application/json",
        "timeout": telegram.TIMEOUT_SECONDS,
    }
