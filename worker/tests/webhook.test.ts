import assert from 'node:assert/strict';
import { test } from 'node:test';
import worker from '../src/index.ts';

test('exception diagnostics identify sleep fetch and redact secrets and URLs', async (t) => {
  const logs: string[] = [];
  t.mock.method(console, 'error', (...args) => { logs.push(args.join(' ')); });
  t.mock.method(globalThis, 'fetch', async () => {
    throw new TypeError('fetch failed https://api.telegram.org/bottest-token/sendMessage test-secret api-secret');
  });
  assert.equal((await worker.fetch(request(), environment())).status, 503);
  const entry = JSON.parse(logs[0]);
  assert.equal(entry.stage, 'telegram_fetch');
  assert.equal(entry.command, 'sleep');
  assert.equal(entry.update_id, 50);
  assert.equal(entry.error_name, 'TypeError');
  assert.match(entry.error_message, /fetch failed/);
  assert.doesNotMatch(logs.join(' '), /test-token|test-secret|api-secret|https:\/\//);
});

test('timeout creation failure is distinguished from a Telegram network failure', async (t) => {
  const logs: string[] = [];
  t.mock.method(console, 'error', (...args) => { logs.push(args.join(' ')); });
  t.mock.method(AbortSignal, 'timeout', () => { throw new TypeError('timeout is not a function'); });
  assert.equal((await worker.fetch(request(), environment())).status, 503);
  assert.equal(JSON.parse(logs[0]).stage, 'telegram_timeout');
});

function request(text = '/sleep', { secret = 'test-secret', type = 'private', chatId = 123, messageId = 10 } = {}) {
  return new Request('https://worker.example/webhook', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Telegram-Bot-Api-Secret-Token': secret },
    body: JSON.stringify({ update_id: 50, message: {
      message_id: messageId, chat: { id: chatId, type }, text,
    } }),
  });
}

function environment(db = { prepare() { throw new Error('Sleep must not use the database'); } }) {
  return { DB: db, TELEGRAM_BOT_TOKEN: 'test-token', TELEGRAM_WEBHOOK_SECRET: 'test-secret', SUBSCRIBER_API_TOKEN: 'api-secret' };
}

test('/sleep replies to the requesting chat without a database', async (t) => {
  const calls: { url: string; payload: any }[] = [];
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    assert.equal(init.redirect, 'manual');
    calls.push({ url: String(url), payload: JSON.parse(init.body) });
    return Response.json({ ok: true, result: { message_id: 11 } });
  });
  const response = await worker.fetch(request(), environment());
  assert.equal(response.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://api.telegram.org/bottest-token/sendMessage');
  assert.equal(calls[0].payload.chat_id, '123');
  assert.equal(calls[0].payload.parse_mode, 'HTML');
  const text = calls[0].payload.text;
  assert.match(text, /15 phút/);
  assert.match(text, /1 chu kỳ/);
  assert.match(text, /5 chu kỳ/);
  assert.doesNotMatch(text, /6 chu kỳ/);
  assert.match(text, /ước tính/);
});

test('/sleep@bot_name is accepted', async (t) => {
  const sends = t.mock.method(globalThis, 'fetch', async () => Response.json({ ok: true }));
  assert.equal((await worker.fetch(request('/sleep@my_bot'), environment())).status, 200);
  assert.equal(sends.mock.callCount(), 1);
});

test('ignores unrelated commands and non-private chats', async (t) => {
  const sends = t.mock.method(globalThis, 'fetch', async () => Response.json({ ok: true }));
  for (const input of [request('/sleepy'), request('sleep'), request('/sleep', { type: 'group' })]) {
    assert.equal((await worker.fetch(input, environment())).status, 200);
  }
  assert.equal(sends.mock.callCount(), 0);
});

test('rejects unauthorized and invalid sleep updates without sending', async (t) => {
  const sends = t.mock.method(globalThis, 'fetch', async () => Response.json({ ok: true }));
  assert.equal((await worker.fetch(request('/sleep', { secret: 'wrong' }), environment())).status, 401);
  assert.equal((await worker.fetch(request('/sleep', { chatId: 0 }), environment())).status, 400);
  assert.equal((await worker.fetch(request('/sleep', { messageId: 0 }), environment())).status, 400);
  assert.equal(sends.mock.callCount(), 0);
});

for (const failure of ['http', 'network', 'api', 'redirect']) {
  test(`sleep reply ${failure} failure returns 503 so Telegram can retry`, async (t) => {
    t.mock.method(console, 'error', () => {});
    t.mock.method(globalThis, 'fetch', async () => {
      if (failure === 'network') throw new Error('network failure');
      if (failure === 'redirect') return new Response(null, { status: 302, headers: { Location: 'https://other.example/' } });
      if (failure === 'http') return new Response('unavailable', { status: 503 });
      return Response.json({ ok: false, error_code: 429, description: 'Too Many Requests' });
    });
    assert.equal((await worker.fetch(request(), environment())).status, 503);
  });
}

for (const command of ['start', 'stop']) {
  test(`/${command} still updates subscribers and sends its acknowledgement`, async (t) => {
    let bindings: unknown[] = [];
    let sql = '';
    let reply = '';
    const db = { prepare(query) {
      sql = query;
      return { bind(...args) { bindings = args; return { async run() { return { meta: { changes: 1 } }; } }; } };
    } };
    t.mock.method(globalThis, 'fetch', async (_url, init) => {
      assert.equal(init.redirect, 'manual');
      reply = JSON.parse(init.body).text;
      return Response.json({ ok: true });
    });
    assert.equal((await worker.fetch(request(`/${command}`), environment(db))).status, 200);
    assert.notEqual(reply, '');
    assert.match(sql, /INSERT INTO subscribers/);
    assert.deepEqual(bindings, ['123', command === 'start' ? 1 : 0, 50, 10]);
    assert.match(reply, command === 'start' ? /đã đăng ký/ : /đã hủy đăng ký/);
  });
}
