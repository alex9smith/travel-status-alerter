import dataclasses

import pytest

from travel_status_alerter.config import Config, ConfigError, load_config

VALID_ENV = {
    "TFL_API_KEY": "tfl-key",
    "TFL_LINES": "victoria,northern",
    "TELEGRAM_BOT_TOKEN": "bot-token",
    "TELEGRAM_CHAT_ID": "-100123",
}


def test_load_config_reads_all_values() -> None:
    assert load_config(VALID_ENV) == Config(
        tfl_api_key="tfl-key",
        tfl_lines=("victoria", "northern"),
        telegram_bot_token="bot-token",
        telegram_chat_id="-100123",
    )


def test_lines_are_trimmed_lowercased_and_empty_entries_dropped() -> None:
    env = {**VALID_ENV, "TFL_LINES": " Victoria , ,NORTHERN,"}

    assert load_config(env).tfl_lines == ("victoria", "northern")


def test_config_is_frozen() -> None:
    config = load_config(VALID_ENV)

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.tfl_api_key = "other"  # type: ignore[misc]


@pytest.mark.parametrize("name", sorted(VALID_ENV))
def test_missing_variable_is_reported_by_name(name: str) -> None:
    env = {k: v for k, v in VALID_ENV.items() if k != name}

    with pytest.raises(ConfigError, match=name):
        load_config(env)


@pytest.mark.parametrize("name", sorted(VALID_ENV))
def test_blank_variable_is_reported_by_name(name: str) -> None:
    env = {**VALID_ENV, name: "   "}

    with pytest.raises(ConfigError, match=name):
        load_config(env)


def test_all_problems_are_reported_together() -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config({})

    message = str(excinfo.value)
    assert all(name in message for name in VALID_ENV)


def test_error_message_never_contains_secret_values() -> None:
    env = {**VALID_ENV, "TFL_LINES": " , "}

    with pytest.raises(ConfigError) as excinfo:
        load_config(env)

    message = str(excinfo.value)
    assert "tfl-key" not in message
    assert "bot-token" not in message
