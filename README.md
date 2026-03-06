# Birthday Notifier (Serverless)

A serverless birthday notifier that sends a daily Telegram message when someone has a birthday.
It runs using GitHub Actions (cron) and stores data/logs in the repository.

## Features
- Daily automation via GitHub Actions schedule (cron)
- Birthday list stored in `data/aniversariantes.json`
- Idempotency using `data/notification_log.json` (prevents duplicate notifications in the same day)
- Telegram message includes `name` and `description`
- Feb 29 birthdays are notified on Feb 28 in non-leap years

## Project structure
data/
aniversariantes.json
notification_log.json
scripts/
send_daily_birthdays.py
.github/workflows/
birthday.yml


## Requirements (local test)
- Python 3.9+ (uses `zoneinfo`)

## Environment variables
Set these as GitHub Actions Secrets (recommended):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

For local testing (Git Bash):
```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
```

run locally
python scripts/send_daily_birthdays.py

How it works (high level)

Load birthdays from data/aniversariantes.json

Determine today’s date in America/Fortaleza

Select today’s birthdays (+ Feb 29 rule)

Check data/notification_log.json to avoid duplicates

Send Telegram message

Append a new log entry (SENT/FAILED) and save the log
