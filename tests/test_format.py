from travel_status_alerter.format import (
    MAX_MESSAGE_LENGTH,
    MAX_REASON_LENGTH,
    format_alert,
    format_error,
)
from travel_status_alerter.tfl import LineStatus


def status(
    name: str = "Northern",
    state: str = "Minor Delays",
    reason: str | None = None,
    line_id: str | None = None,
) -> LineStatus:
    return LineStatus(
        line_id=line_id or name.lower().replace(" ", "-"),
        name=name,
        status=state,
        reason=reason,
    )


def test_returns_none_when_everything_is_good_service() -> None:
    statuses = (status("Victoria", "Good Service"), status("Northern", "Good Service"))

    assert format_alert(statuses) is None


def test_returns_none_for_no_statuses() -> None:
    assert format_alert(()) is None


def test_good_service_check_is_case_insensitive() -> None:
    assert format_alert((status(state="good service"),)) is None


def test_lists_only_disrupted_lines() -> None:
    statuses = (
        status("Victoria", "Good Service"),
        status("Northern", "Minor Delays", "NORTHERN LINE: Delays due to a faulty train."),
    )

    assert format_alert(statuses) == (
        "🚨 <b>TfL disruption</b>\n"
        "\n"
        "<b>Northern</b>: Minor Delays\n"
        "NORTHERN LINE: Delays due to a faulty train."
    )


def test_status_without_reason_has_no_trailing_line() -> None:
    message = format_alert((status("DLR", "Part Closure"),))

    assert message is not None
    assert message.endswith("<b>DLR</b>: Part Closure")


def test_multiple_statuses_and_lines_are_separated_by_blank_lines() -> None:
    statuses = (
        status("Northern", "Minor Delays", "a"),
        status("Northern", "Severe Delays"),
        status("Jubilee", "Part Suspended", "b"),
    )

    assert format_alert(statuses) == (
        "🚨 <b>TfL disruption</b>\n"
        "\n"
        "<b>Northern</b>: Minor Delays\na\n"
        "\n"
        "<b>Northern</b>: Severe Delays\n"
        "\n"
        "<b>Jubilee</b>: Part Suspended\nb"
    )


def test_html_in_tfl_text_is_escaped() -> None:
    message = format_alert((status("A & B <line>", "Delays", "Use <b>bus</b> & walk"),))

    assert message is not None
    assert "<b>A &amp; B &lt;line&gt;</b>: Delays" in message
    assert "Use &lt;b&gt;bus&lt;/b&gt; &amp; walk" in message


def test_long_reasons_are_truncated_before_escaping() -> None:
    reason = "&" * (MAX_REASON_LENGTH + 50)

    message = format_alert((status(reason=reason),))

    assert message is not None
    assert message.endswith("&amp;" * (MAX_REASON_LENGTH - 1) + "…")
    assert "&amp&" not in message


def test_message_is_capped_and_says_how_many_entries_were_dropped() -> None:
    reason = "x" * MAX_REASON_LENGTH
    statuses = tuple(status(f"Line {n}", "Severe Delays", reason) for n in range(30))

    message = format_alert(statuses)

    assert message is not None
    assert len(message) <= MAX_MESSAGE_LENGTH
    dropped = int(message.rsplit("…and ", 1)[1].split(" ", 1)[0])
    assert 0 < dropped < 30
    assert message.count("<b>Line ") == 30 - dropped


def test_format_error_escapes_and_names_the_failure() -> None:
    assert format_error("TfL API returned HTTP 500 <oops>") == (
        "⚠️ <b>TfL status check failed</b>\nTfL API returned HTTP 500 &lt;oops&gt;"
    )
