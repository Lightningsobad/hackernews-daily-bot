# Telegram /sleep command

Approved in chat on 2026-11-01.

## Intent and behavior

Extend the existing Telegram bot with `/sleep`. Add 15 minutes to the current
time for falling asleep, then show wake-up times for exactly 1, 2, 3, 4 and 5
cycles of 90 minutes. Format times in `Asia/Ho_Chi_Minh` and include the calendar
date so midnight, month and year rollovers are unambiguous.

The reply is Vietnamese and describes these times as estimates. Explain that
short options are not sufficient for a full night's sleep and that most adults
need 7–9 hours. Do not promise a particular sleep stage or alertness.

## Approaches

- Extend the Cloudflare Worker webhook: reuses the existing authenticated
  `/start` and `/stop` receiver and responds immediately. Selected by the user.
- Add a Python polling service: would require an additional continuously running
  process and conflict with an existing Telegram webhook. Rejected.

## Implementation constraints

Only the Worker's built output and embedded TypeScript source map are available.
Restore that source before editing; retain existing subscription behavior.
Support private chats, matching the current receiver. `/sleep` must not subscribe,
unsubscribe, or require a database operation. Keep webhook authentication and
message validation. A failed sleep reply must return an error for Telegram retry.

No alarms, reminders, custom sleep durations, sixth cycle, subscription schema
changes, or deployment are included. BotFather registration is already done.

## Builder decisions

Use a separate pure formatter with an injectable date for deterministic tests.
Restore build tooling with existing local dependencies, use Node's built-in test
runner, and document how to deploy using the existing Worker and D1 binding.
