import logging
from datetime import UTC, datetime

import pytest

from travel_status_alerter import main as app
from travel_status_alerter.main import run
from travel_status_alerter.telegram import TelegramError
from travel_status_alerter.tfl import LineStatus, TflError

ENV = {
    "TFL_API_KEY": "tfl-key",
    "TFL_LINES": "victoria,northern",
    "TELEGRAM_BOT_TOKEN": "bot-token",
    "TELEGRAM_CHAT_ID": "-100123",
}
SCHEDULED_ENV = {**ENV, "GITHUB_EVENT_NAME": "schedule"}

# 07:05 in London (GMT) and 06:05 in London's summer time respectively.
IN_WINDOW = datetime(2026, 1, 12, 7, 5, tzinfo=UTC)
OUT_OF_WINDOW = datetime(2026, 1, 12, 6, 5, tzinfo=UTC)

GOOD = (LineStatus("victoria", "Victoria", "Good Service", None),)
DISRUPTED = (
    *GOOD,
    LineStatus("northern", "Northern", "Minor Delays", "Faulty train"),
)


class Recorder:
    """Fake fetch/send functions that record calls and optionally raise."""

    def __init__(
        self,
        statuses: tuple[LineStatus, ...] = GOOD,
        fetch_error: Exception | None = None,
        send_errors: tuple[Exception | None, ...] = (),
    ) -> None:
        self.statuses = statuses
        self.fetch_error = fetch_error
        self.send_errors = list(send_errors)
        self.fetch_calls: list[tuple[tuple[str, ...], str]] = []
        self.sent: list[tuple[str, str, str]] = []

    def fetch(self, lines: tuple[str, ...], api_key: str) -> tuple[LineStatus, ...]:
        self.fetch_calls.append((lines, api_key))
        if self.fetch_error:
            raise self.fetch_error
        return self.statuses

    def send(self, token: str, chat_id: str, text: str) -> None:
        self.sent.append((token, chat_id, text))
        if self.send_errors and (error := self.send_errors.pop(0)):
            raise error


def do_run(recorder: Recorder, env: dict[str, str] = ENV, now: datetime = IN_WINDOW) -> int:
    return run(env, now, fetch=recorder.fetch, send=recorder.send)


def test_sends_alert_when_there_is_disruption() -> None:
    recorder = Recorder(DISRUPTED)

    assert do_run(recorder) == 0
    assert recorder.fetch_calls == [(("victoria", "northern"), "tfl-key")]
    assert len(recorder.sent) == 1
    token, chat_id, text = recorder.sent[0]
    assert (token, chat_id) == ("bot-token", "-100123")
    assert "<b>Northern</b>: Minor Delays" in text


def test_sends_nothing_when_all_lines_are_good(caplog: pytest.LogCaptureFixture) -> None:
    recorder = Recorder(GOOD)

    with caplog.at_level(logging.INFO):
        assert do_run(recorder) == 0

    assert recorder.sent == []
    assert "no disruption" in caplog.text.lower()


def test_tfl_failure_is_logged_and_reported_on_telegram(
    caplog: pytest.LogCaptureFixture,
) -> None:
    recorder = Recorder(fetch_error=TflError("TfL API returned HTTP 500"))

    with caplog.at_level(logging.ERROR):
        assert do_run(recorder) == 1

    assert "TfL API returned HTTP 500" in caplog.text
    assert len(recorder.sent) == 1
    assert "TfL status check failed" in recorder.sent[0][2]
    assert "HTTP 500" in recorder.sent[0][2]


def test_failure_to_report_tfl_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    recorder = Recorder(
        fetch_error=TflError("boom"), send_errors=(TelegramError("Telegram API returned HTTP 401"),)
    )

    with caplog.at_level(logging.ERROR):
        assert do_run(recorder) == 1

    assert "boom" in caplog.text
    assert "HTTP 401" in caplog.text


def test_telegram_failure_sending_alert_fails_the_run(caplog: pytest.LogCaptureFixture) -> None:
    recorder = Recorder(DISRUPTED, send_errors=(TelegramError("Telegram API returned HTTP 400"),))

    with caplog.at_level(logging.ERROR):
        assert do_run(recorder) == 1

    assert "HTTP 400" in caplog.text
    assert len(recorder.sent) == 1


def test_scheduled_run_outside_uk_7am_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    recorder = Recorder(DISRUPTED)

    with caplog.at_level(logging.INFO):
        assert do_run(recorder, SCHEDULED_ENV, OUT_OF_WINDOW) == 0

    assert recorder.fetch_calls == []
    assert recorder.sent == []
    assert "skipping" in caplog.text.lower()


def test_scheduled_run_inside_uk_7am_proceeds() -> None:
    recorder = Recorder(DISRUPTED)

    assert do_run(recorder, SCHEDULED_ENV, IN_WINDOW) == 0
    assert len(recorder.sent) == 1


@pytest.mark.parametrize("event", ["workflow_dispatch", "push"])
def test_non_scheduled_runs_ignore_the_time_guard(event: str) -> None:
    recorder = Recorder(DISRUPTED)

    assert do_run(recorder, {**ENV, "GITHUB_EVENT_NAME": event}, OUT_OF_WINDOW) == 0
    assert len(recorder.sent) == 1


def test_missing_config_fails_without_calling_any_api(caplog: pytest.LogCaptureFixture) -> None:
    recorder = Recorder(DISRUPTED)

    with caplog.at_level(logging.ERROR):
        assert do_run(recorder, {"TFL_LINES": "victoria"}) == 1

    assert "TFL_API_KEY" in caplog.text
    assert "bot-token" not in caplog.text
    assert recorder.fetch_calls == []
    assert recorder.sent == []


def test_main_runs_with_real_environment_and_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(env: object, now: datetime) -> int:
        captured.update(env=env, now=now)
        return 7

    monkeypatch.setattr(app, "run", fake_run)
    monkeypatch.setenv("TFL_LINES", "victoria")

    assert app.main() == 7
    assert isinstance(captured["env"], dict)
    assert captured["env"]["TFL_LINES"] == "victoria"
    now = captured["now"]
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
