import { test, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "../src/index.ts";

let db: DatabaseSync;
let env: any;
let originalFetch: typeof fetch;
let acknowledgements: any[];

beforeEach(() => {
  db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../migrations/0001_subscribers.sql", import.meta.url), "utf8"));
  // Execute the Worker's real SQL against SQLite through the D1 prepared-statement interface.
  env = {
    TELEGRAM_BOT_TOKEN: "fake", TELEGRAM_WEBHOOK_SECRET: "webhook-secret", SUBSCRIBER_API_TOKEN: "api-secret",
    DB: { prepare(sql: string) {
      let values: any[] = [];
      return {
        bind(...args: any[]) { values = args; return this; },
        async run() { const result = db.prepare(sql).run(...values); return { meta: { changes: Number(result.changes) } }; },
        async all() { return { results: db.prepare(sql).all(...values) }; },
      };
    } },
  };
  acknowledgements = [];
  originalFetch = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    acknowledgements.push(JSON.parse(options!.body as string));
    return Response.json({ ok: true });
  };
});
afterEach(() => { globalThis.fetch = originalFetch; db.close(); });

function call(path: string, options: RequestInit = {}, key = "api-secret") {
  return worker.fetch(new Request(`https://bot.example${path}`, {
    ...options, headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json", ...options.headers },
  }), env);
}
function command(text: string, update = 1, chat = 123, type = "private", key = "webhook-secret", messageId = update) {
  return call("/webhook", {
    method: "POST", headers: { "X-Telegram-Bot-Api-Secret-Token": key },
    body: JSON.stringify({ update_id: update, message: { message_id: messageId, text, chat: { id: chat, type } } }),
  });
}
function rows() { return db.prepare("SELECT * FROM subscribers").all() as any[]; }

test("webhook rejects invalid and absent secrets without writing", async () => {
  assert.equal((await command("/start", 1, 123, "private", "wrong")).status, 401);
  delete env.TELEGRAM_WEBHOOK_SECRET;
  assert.notEqual((await command("/start", 1, 123, "private", "")).status, 200);
  assert.equal(rows().length, 0);
});
test("start, duplicate update, repeated start, stop, and re-registration", async () => {
  assert.equal((await command("/start")).status, 200);
  assert.equal(rows()[0].active, 1);
  assert.equal(rows()[0].chat_id, "123");
  assert.equal(rows()[0].version, 1);
  await command("/start");
  assert.equal(rows()[0].version, 1);
  assert.equal(acknowledgements.length, 1);
  await command("/start", 2);
  assert.equal(rows().length, 1);
  assert.equal(rows()[0].version, 2);
  await command("/stop", 3);
  assert.equal(rows()[0].active, 0);
  await command("/start", 4);
  assert.equal(rows()[0].active, 1);
  assert.equal(rows()[0].version, 4);
});
test("out of order updates cannot undo a newer stop", async () => {
  await command("/stop", 10);
  await command("/start", 9);
  assert.equal(rows()[0].active, 0);
  assert.equal(rows()[0].last_update_id, 10);
});
test("a newer command with a lower update ID still applies after Telegram reset", async () => {
  await command("/start", 900000, 123, "private", "webhook-secret", 10);
  await command("/stop", 100000, 123, "private", "webhook-secret", 11);
  assert.equal(rows()[0].active, 0);
  assert.equal(rows()[0].last_update_id, 100000);
  // An old command replay with a larger update ID cannot undo the newer stop.
  await command("/start", 900000, 123, "private", "webhook-secret", 10);
  assert.equal(rows()[0].active, 0);
  assert.equal(rows()[0].version, 2);
});
test("group commands and unrelated messages do not subscribe", async () => {
  await command("/start", 1, -123, "group");
  await command("hello", 2);
  await command("/starter", 3);
  assert.equal(rows().length, 0);
});
test("start with deep-link payload registers", async () => {
  await command("/start referral", 2);
  assert.equal(rows()[0].active, 1);
});
test("acknowledgement failure does not roll back or replay subscription", async () => {
  globalThis.fetch = async () => { throw new Error("fake token in URL"); };
  assert.equal((await command("/start")).status, 200);
  assert.equal(rows()[0].active, 1);
  await command("/start");
  assert.equal(rows()[0].version, 1);
});
test("subscriber APIs require a separate secret", async () => {
  assert.equal((await call("/subscribers", {}, "webhook-secret")).status, 401);
  assert.equal((await call("/subscribers/disable", { method: "POST", body: "{}" }, "wrong")).status, 401);
});
test("list paginates active subscribers with stable cursors", async () => {
  const insert = db.prepare("INSERT INTO subscribers(chat_id, active, version, last_update_id) VALUES (?, ?, 1, 1)");
  for (let i = 1000; i < 1205; i++) insert.run(String(i), i === 1050 ? 0 : 1);
  let cursor: string | null = null;
  const ids: string[] = [];
  do {
    const response = await call(`/subscribers${cursor ? `?cursor=${cursor}` : ""}`);
    assert.equal(response.headers.get("Cache-Control"), "no-store");
    const page: any = await response.json();
    assert.ok(page.subscribers.length <= 100);
    ids.push(...page.subscribers.map((s: any) => s.chat_id));
    cursor = page.next_cursor;
  } while (cursor);
  assert.equal(ids.length, 204);
  assert.equal(new Set(ids).size, 204);
  assert.ok(!ids.includes("1050"));
});
test("disable is conditional on subscription version", async () => {
  await command("/start", 1);
  await command("/stop", 2);
  await command("/start", 3);
  const stale = await call("/subscribers/disable", { method: "POST", body: JSON.stringify({ chat_id: "123", version: 1 }) });
  assert.deepEqual(await stale.json(), { disabled: false });
  assert.equal(rows()[0].active, 1);
  const current = await call("/subscribers/disable", { method: "POST", body: JSON.stringify({ chat_id: "123", version: 3 }) });
  assert.deepEqual(await current.json(), { disabled: true });
  assert.equal(rows()[0].active, 0);
  await command("/start", 4);
  assert.equal(rows()[0].active, 1);
});
test("invalid request bodies and cursors are rejected", async () => {
  assert.equal((await call("/subscribers?cursor=bad")).status, 400);
  assert.equal((await call("/subscribers/disable", { method: "POST", body: "{" })).status, 400);
  assert.equal((await call("/subscribers/disable", { method: "POST", body: JSON.stringify({ chat_id: "123", version: -1 }) })).status, 400);
});
test("database errors return retryable status without leaking details", async () => {
  env.DB.prepare = () => { throw new Error("sensitive connection info"); };
  const response = await command("/start");
  assert.equal(response.status, 503);
  assert.ok(!(await response.text()).includes("sensitive"));
});
