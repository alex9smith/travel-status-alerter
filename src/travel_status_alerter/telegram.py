import json
import urllib.error
import urllib.request
from collections.abc import Callable

BASE_URL = "https://api.telegram.org"
TIMEOUT_SECONDS = 20.0

HttpPost = Callable[[str, bytes], bytes]


class TelegramError(Exception):
    """Raised when a message could not be delivered.

    Messages must never include the request URL, which contains the bot token.
    """


def urllib_post(url: str, body: bytes) -> bytes:
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        response_body: bytes = response.read()
    return response_body


def build_url(bot_token: str) -> str:
    return f"{BASE_URL}/bot{bot_token}/sendMessage"


def build_payload(chat_id: str, text: str) -> bytes:
    return json.dumps(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
    ).encode()


def _check_response(body: bytes) -> None:
    try:
        response: object = json.loads(body)
    except ValueError:
        raise TelegramError("Telegram API response was not valid JSON") from None
    if not isinstance(response, dict) or "ok" not in response:
        raise TelegramError("Unexpected Telegram API response")
    if response["ok"] is not True:
        description = response.get("description")
        raise TelegramError(f"Telegram rejected the message: {description}")


def send_message(
    bot_token: str, chat_id: str, text: str, http_post: HttpPost = urllib_post
) -> None:
    try:
        body = http_post(build_url(bot_token), build_payload(chat_id, text))
    except urllib.error.HTTPError as error:
        raise TelegramError(f"Telegram API returned HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise TelegramError(f"Could not reach Telegram API: {error}") from None
    _check_response(body)
