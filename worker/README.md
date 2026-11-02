# Telegram command Worker

The TypeScript entry point was recovered from the existing Worker build's source
map. It preserves the `/start`, `/stop` and subscriber API handlers and adds
`/sleep`. The daily Python digest still runs separately through GitHub Actions.

## `/sleep`

Send `/sleep` in a **private chat** with the bot. The reply contains exactly five
wake-up times: current time + 15 minutes to fall asleep + 1–5 cycles of 90 minutes.
All times use `Asia/Ho_Chi_Minh` (UTC+7) and include a date. For example, at 23:00
on 01/11/2026, the results are 00:45, 02:15, 03:45, 05:15 and 06:45 on 02/11/2026.

This is an estimate, not an alarm or sleep-stage measurement. Short durations
are not presented as sufficient for a full night's sleep. Sleep cycles vary;
see [NIH on sleep cycles](https://www.nhlbi.nih.gov/health/sleep/stages-of-sleep)
and [NIH on adult sleep duration](https://health.nih.gov/health-topics-a-z/healthy-sleep).

The command works independently of newsletter registration, including after
`/stop`. It does not access D1. Only authenticated webhook updates are accepted.
Telegram send failures return HTTP 503 to allow delivery retries; delivery is
not guaranteed to be exactly once if Telegram retries an update.

## Development

Requires Node.js 24 or newer. From this directory:

```powershell
npm install
npm test
npm run typecheck
npm run build
```

Tests intercept outgoing Telegram requests; they do not contact a real bot.
The build writes `dist/index.js` and its source map. Generated output is ignored
by Git; commit the source, package files, configuration and tests.

## Updating the existing Worker

### Diagnose a silent command

After building, deploy `dist/index.js` to the existing Worker using its dashboard
editor (replace the entry module, save and deploy). Preserve bindings, secrets,
Worker name and webhook URL. This checkout has no deployment configuration, so
do not run an unconfigured Wrangler deployment.

Open Observability Live, send `/sleep` once in the bot's private chat, and inspect
the new event and associated console entry. Exception logs contain `message`,
`stage`, `command`, `update_id`, `error_name` and `error_message`. Secrets and HTTP
URLs are redacted; stacks, message text and chat identifiers are not logged.
Telegram HTTP/API failures log `http_status` and, when available,
`telegram_error_code` instead of an exception. HTTP failures do not parse the
Telegram response body.

Stages distinguish `authenticate`, `parse_update`, `format_sleep`,
`telegram_timeout`, `telegram_fetch`, `telegram_parse` and `subscriber_write`.
Share the diagnostic JSON plus the matching invocation's timestamp, request ID,
script version, response status, CPU and wall times. Include whether the command
was `/sleep` in private chat and whether a reply arrived. Do not share bot tokens,
webhook secrets or the full Telegram update. Repeated `update_id` values can help
identify retries of an older update.

This checkout does not contain the original Wrangler deployment configuration,
Cloudflare account/database identifiers, or production secrets. Restore the
existing Worker's configuration before deploying; do not invent a new D1 binding
or replace the subscriber database.

The configuration must point `main` to `src/index.ts` (or the bundled
`dist/index.js`), keep the existing Worker name, and keep D1 bound as `DB` with
the existing database ID. Keep these secrets on the same Worker:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET`
- `SUBSCRIBER_API_TOKEN`

Once the existing configuration is restored and checked, `npx wrangler deploy`
publishes the change. Alternatively, upload the built ESM `dist/index.js` through
the existing Worker's deployment workflow. No database migration or Telegram
webhook URL change is needed when updating the same Worker.

The `/sleep` menu entry has already been added through BotFather. That entry
becomes functional only after the updated webhook Worker is deployed. Test in
private chat by sending `/sleep`; verify five times and unchanged `/start` and
`/stop` behavior. Local implementation and tests do not deploy automatically.
