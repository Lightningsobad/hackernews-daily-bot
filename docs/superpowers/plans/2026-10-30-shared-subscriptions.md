# Shared Telegram subscriptions implementation plan

Approved specification: the user's implementation request in this chat.

Goal: generate one shared digest per run and deliver it to public private-chat subscribers.
Architecture: TypeScript Cloudflare Worker + D1 for commands and authenticated recipient API;
existing Python GitHub Actions job for generation and delivery, still at 07:17 Vietnam time.

- [x] Add configuration and authenticated paginated subscriber client. Preserve fixed-chat mode.
- [x] Fetch recipients before AI, deduplicate, generate once, broadcast with bounded retries.
- [x] Add atomic ordered /start and /stop, protected list and conditional-disable endpoints.
- [x] Add D1 migration, Wrangler configuration, workflow secrets/concurrency and operations guide.
- [x] Verify full Python suite, Worker SQL tests, TypeScript check and Wrangler dry build.
- [x] Read-only independent review; fix material findings and re-run verification.

Final verification: 60 Python tests, 12 Worker SQLite tests, TypeScript check and
Wrangler dry build passed. Review fix: retain last_update_id but order private-chat
commands using last_message_id to handle Telegram's update-ID reset after inactivity.
No live deployment performed; see docs/subscriptions.md for required account setup.

Acceptance: shared content and constant AI call count with multiple recipients; no-recipient
skip; API failure before AI; isolated delivery failures; retry_after and wait budget;
duplicate/out-of-order updates; conditional disable; no subscriber writes during dry-run.

Defaults: open registration; no immediate digest on /start; fixed address survives /stop;
no automatic whole-job rerun or persisted digest/delivery history; manual reruns may duplicate.
Deployment requires a Cloudflare account, D1 ID and real secrets, then a test Telegram account.
