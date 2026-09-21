# travel-status-alerter

A GitHub Actions job that checks TfL line statuses at 07:00 UK time, Monday to Thursday, and
sends a Telegram message if any monitored line has disruption. Nothing is sent when all
lines have a good service. If the TfL API call fails, the error is logged and reported on
Telegram, and the workflow run fails.

## Setup

In the repository settings (Settings → Secrets and variables → Actions):

| Name                 | Kind     | Example / notes                                              |
| -------------------- | -------- | ------------------------------------------------------------ |
| `TFL_API_KEY`        | Secret   | Key from the [TfL API portal](https://api-portal.tfl.gov.uk) |
| `TELEGRAM_BOT_TOKEN` | Secret   | From [@BotFather](https://t.me/BotFather)                    |
| `TELEGRAM_CHAT_ID`   | Secret   | Channel/chat ID (the bot must be able to post there)         |
| `TFL_LINES`          | Variable | Comma-separated TfL line IDs, e.g. `victoria,northern,elizabeth` |

Line IDs are those used by the TfL API (lower case, hyphenated), e.g. `bakerloo`,
`hammersmith-city`, `london-overground`, `dlr`, `elizabeth`. List them with
`https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr,elizabeth-line`.

## Scheduling

GitHub cron is UTC-only, so the workflow fires at 06:00 and 07:00 UTC on Mon-Thu and the
script only proceeds when it is the 07:00 hour in `Europe/London`. That gives 07:00 UK time
in both GMT and BST. GitHub may delay scheduled runs under load; a run delayed past 07:59 UK
time is skipped. GitHub also disables scheduled workflows in a repository after 60 days
without activity, so re-enable it in the Actions tab if the alerts stop.

To run on demand, use Actions → "Travel status alert" → Run workflow. Manual runs skip the
time guard.

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pytest            # tests with coverage
uv run ruff check        # lint
uv run ruff format       # format
uv run mypy              # strict type check
```

To run locally, export the four variables above and run `uv run travel-status-alerter`.

See [AGENTS.md](AGENTS.md) for project conventions.
