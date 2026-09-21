from collections.abc import Mapping
from dataclasses import dataclass

REQUIRED_VARIABLES = (
    "TFL_API_KEY",
    "TFL_LINES",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
)


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    tfl_api_key: str
    tfl_lines: tuple[str, ...]
    telegram_bot_token: str
    telegram_chat_id: str


def _parse_lines(raw: str) -> tuple[str, ...]:
    return tuple(line for part in raw.split(",") if (line := part.strip().lower()))


def load_config(env: Mapping[str, str]) -> Config:
    """Build a Config from environment variables.

    Raises ConfigError naming every missing or blank variable; values are never included.
    """
    values = {name: env.get(name, "").strip() for name in REQUIRED_VARIABLES}
    lines = _parse_lines(values["TFL_LINES"])

    problems = tuple(
        name for name, value in values.items() if not value or (name == "TFL_LINES" and not lines)
    )
    if problems:
        raise ConfigError(f"Missing or empty environment variables: {', '.join(problems)}")

    return Config(
        tfl_api_key=values["TFL_API_KEY"],
        tfl_lines=lines,
        telegram_bot_token=values["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=values["TELEGRAM_CHAT_ID"],
    )
