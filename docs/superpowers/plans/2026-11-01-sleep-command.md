# Sleep Command Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Respond to `/sleep` with five wake-up times using a 15-minute latency and 90-minute cycles.

**Architecture:** Restore the existing TypeScript Worker from its source map. Add a pure sleep-message formatter and route `/sleep` through the authenticated webhook without touching subscribers.

**Tech Stack:** Cloudflare Workers, TypeScript, esbuild, Node built-in test runner.

**Spec:** `docs/superpowers/specs/2026-11-01-sleep-command-design.md`

## Global Constraints

- Exactly 1–5 cycles of 90 minutes, plus 15 minutes before sleeping.
- Vietnamese output and `Asia/Ho_Chi_Minh` calendar dates.
- Preserve `/start`, `/stop`, authentication, and subscriber API behavior.
- No schema changes or deployment; reuse this checkout and existing local dependencies.

## Review Focus

- UTC versus Vietnam date and midnight/month/year rollover.
- `/sleep@bot_name` must match; `/sleepy` must not.
- Unauthorized requests must never send a Telegram message.
- Sleep must not write subscription state, including after `/stop`.
- Telegram network/API failures must not be acknowledged as successful sleep replies.

## Task 1: Restore source and implement the command

**Files:** Restore `worker/src/index.ts`; create `worker/src/sleep.ts`,
`worker/tests/sleep.test.ts`, `worker/tests/webhook.test.ts`, `worker/package.json`,
`worker/README.md`; update `.gitignore` and `README.vi.md`.

**Interfaces:** `formatSleepMessage(now: Date = new Date()): string` supplies
Vietnamese plain text to the existing Worker `fetch(request, env)` webhook.

- [x] Restore the existing source byte-for-byte from `sourcesContent`, and add local build/test scripts.
- [x] Add webhook tests: command sends five cycle results; private-only and exact command matching; no DB access; authentication; failed sends return 503; start/stop regression.
- [x] Run tests against restored source: new sleep behavior must fail while existing behavior passes.
- [x] Add formatter tests with literal expected times for 23:00, 00:00, end of month, and end of year Vietnam time; verify failure before implementation.
- [x] Implement the formatter and `/sleep` routing, preserving subscription logic.
- [x] Run `npm test` in `worker`, build with `npm run build`, and run `.venv/Scripts/python.exe -m pytest -q` at the repository root.
- [x] Document private chat usage and deployment prerequisites, review all changed files, and record verification.

## Verification

- Worker: 16 tests passed; TypeScript checking and esbuild passed.
- Python digest regression suite: 29 tests passed.
- Built ESM smoke test: authenticated `/sleep` sent five results without D1.
- Independent read-only review found no actionable bugs and independently reran
  the Worker tests and TypeScript check. A malformed Telegram response test is
  optional future coverage; the existing catch already returns 503.
- The restored subscription handlers are unchanged except for the new sleep
  command branch. No production deployment, commits, or pushes were performed.
