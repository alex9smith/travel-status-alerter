# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.

## What this project does

A GitHub Actions workflow runs at 07:00 UK time Monday to Thursday. It calls the TfL
(Transport for London) Unified API, checks the status of a configurable set of lines
(Underground, Overground, Elizabeth line, etc.) and sends a Telegram message to a channel
if any line has disruption.

- **Disruption** means any line status other than "Good Service" (including planned
  closures and part closures).
- On a normal day (no disruption) **send nothing**.
- If the TfL API call fails, **log the error and also send an error message on Telegram**,
  so a broken job is never silent.

## Configuration and secrets

All configuration is passed to the script as environment variables, sourced from GitHub
repository secrets (including `TFL_LINES`; the workflow reads all four from `secrets.*`).
Nothing is read from config files and no secret is ever committed or logged.

| Variable             | Purpose                                                                     |
| -------------------- | --------------------------------------------------------------------------- |
| `TFL_API_KEY`        | TfL API key (sent as the `app_key` query parameter)                         |
| `TFL_LINES`          | Comma-separated TfL line IDs to monitor, e.g. `victoria,northern,elizabeth` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token                                                          |
| `TELEGRAM_CHAT_ID`   | Telegram channel / chat ID to post to                                       |

Missing or empty required variables should fail fast with a clear error message (naming the
variable, never printing its value).

## Scheduling

GitHub Actions cron is UTC-only, so the workflow uses **two crons (`17 6 * * 1-4` and
`17 7 * * 1-4`, i.e. 06:17 and 07:17 UTC on Mon-Thu)** and the script has a guard that exits early unless the current time in `Europe/London`
is in the 07:00 hour. This makes it fire once at ~07:17 UK time in both BST and GMT. The
minute is offset from the top of the hour on purpose: GitHub Actions documents that
on-the-hour schedules are the most congested and can be delayed by hours under load, which
previously caused runs to miss the guard window entirely.
The guard applies only when `GITHUB_EVENT_NAME == "schedule"`; manual `workflow_dispatch`
runs and local runs skip it so the job can be tested on demand. The
guard logic must be a pure function of an injected "now" so it is unit-testable.

## Tooling and language conventions

- **Python**: latest stable version, managed with `uv` (and other Astral tools). Pin the
  version in `.python-version` / `pyproject.toml`.
- **Standard library first.** Strongly prefer the stdlib (e.g. `urllib.request`, `json`,
  `zoneinfo`, `logging`, `dataclasses`). Only add a runtime dependency if there is a very
  strong reason; dev-only dependencies (pytest, coverage, ruff, mypy) are fine.
- **Functional style.** Prefer pure functions and immutable data (`@dataclass(frozen=True)`,
  `tuple` over `list`). Keep I/O (HTTP calls, reading env, clock, logging) at the edges
  in thin functions and pass dependencies in as arguments so the core logic is pure.
- **Strict type hints** everywhere, checked with `mypy --strict`. No untyped defs and no
  implicit `Any`. Use `# type: ignore` only with a specific error code and a reason.
- **Lint and format** with `ruff` (`ruff check` and `ruff format`).
- **Tests** use `pytest`, with good coverage (aim for near 100% of the logic; use
  `pytest-cov`). Tests must never hit the real TfL or Telegram APIs. Inject fake
  fetch/send functions or mock at the HTTP boundary.
- Run through `uv`, e.g. `uv run pytest`, `uv run ruff check`, `uv run mypy`.

## Workflow and commits

- After each **small logical change**, make sure the tests pass (and lint/type checks are
  clean), then create a **new commit**.
- Use **Conventional Commits** style: `feat:`, `fix:`, `test:`, `chore:`, `docs:`,
  `refactor:`, `ci:`, etc., with an optional scope, e.g. `feat(tfl): parse line statuses`.
- Keep commits small and focused; don't batch unrelated changes.
- The original requirements document (`docs/REQUIREMENTS.md`) is git-ignored and may not
  exist. This file is the source of truth for project conventions.
