import logging
import os
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from travel_status_alerter.config import Config, ConfigError, load_config
from travel_status_alerter.format import format_alert, format_error
from travel_status_alerter.schedule import should_run
from travel_status_alerter.telegram import TelegramError, send_message
from travel_status_alerter.tfl import LineStatus, TflError, fetch_statuses

logger = logging.getLogger(__name__)

Fetch = Callable[[tuple[str, ...], str], tuple[LineStatus, ...]]
Send = Callable[[str, str, str], None]

SCHEDULE_EVENT = "schedule"


def _is_skipped_by_guard(env: Mapping[str, str], now: datetime) -> bool:
    """Only cron-triggered runs are subject to the UK 07:00 guard; manual runs always go."""
    return env.get("GITHUB_EVENT_NAME") == SCHEDULE_EVENT and not should_run(now)


def _try_send(config: Config, text: str, send: Send) -> bool:
    try:
        send(config.telegram_bot_token, config.telegram_chat_id, text)
    except TelegramError as error:
        logger.error("Failed to send Telegram message: %s", error)
        return False
    return True


def run(
    env: Mapping[str, str],
    now: datetime,
    fetch: Fetch = fetch_statuses,
    send: Send = send_message,
) -> int:
    """Check TfL line statuses and alert on Telegram. Returns the process exit code."""
    if _is_skipped_by_guard(env, now):
        logger.info("Not 07:00 in the UK right now; skipping this scheduled run")
        return 0

    try:
        config = load_config(env)
    except ConfigError as error:
        logger.error("%s", error)
        return 1

    try:
        statuses = fetch(config.tfl_lines, config.tfl_api_key)
    except TflError as error:
        logger.error("TfL status check failed: %s", error)
        _try_send(config, format_error(str(error)), send)
        return 1

    message = format_alert(statuses)
    if message is None:
        logger.info("No disruption on %s", ", ".join(config.tfl_lines))
        return 0

    logger.info("Disruption found; sending Telegram alert")
    return 0 if _try_send(config, message, send) else 1


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return run(dict(os.environ), datetime.now(UTC))
