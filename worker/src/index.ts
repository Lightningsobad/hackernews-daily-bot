export interface Env {
  DB: D1Database;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  SUBSCRIBER_API_TOKEN: string;
}

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: { "Cache-Control": "no-store" } });
}

async function authorized(actual: string | null, expected: string): Promise<boolean> {
  if (!actual || !expected) return false;
  const encoder = new TextEncoder();
  const [a, b] = await Promise.all([actual, expected].map(value =>
    crypto.subtle.digest("SHA-256", encoder.encode(value))));
  const left = new Uint8Array(a), right = new Uint8Array(b);
  let difference = 0;
  for (let i = 0; i < left.length; i++) difference |= left[i] ^ right[i];
  return difference === 0;
}

async function body(request: Request): Promise<any> {
  try { return await request.json(); }
  catch { return null; }
}

async function webhook(request: Request, env: Env): Promise<Response> {
  if (!env.TELEGRAM_WEBHOOK_SECRET || !env.TELEGRAM_BOT_TOKEN) return json({ error: "Not configured" }, 503);
  if (!await authorized(request.headers.get("X-Telegram-Bot-Api-Secret-Token"), env.TELEGRAM_WEBHOOK_SECRET)) {
    return json({ error: "Unauthorized" }, 401);
  }
  const update = await body(request);
  if (!update || !Number.isSafeInteger(update.update_id) || update.update_id < 0) {
    return json({ error: "Invalid update" }, 400);
  }
  const message = update.message;
  if (message?.chat?.type !== "private" || typeof message.text !== "string") return json({ ok: true });
  const match = /^\/(start|stop)(?:@\w+)?(?:\s|$)/.exec(message.text);
  if (!match) return json({ ok: true });
  if (!Number.isSafeInteger(message.chat.id) || message.chat.id <= 0) return json({ error: "Invalid chat" }, 400);
  if (!Number.isSafeInteger(message.message_id) || message.message_id <= 0) return json({ error: "Invalid message" }, 400);
  const active = match[1] === "start" ? 1 : 0;
  // Telegram can reset update_id after inactivity. Private-chat message order stays
  // independent of that reset; persist both watermarks in the same atomic statement.
  const result = await env.DB.prepare(`
    INSERT INTO subscribers (chat_id, active, version, last_update_id, last_message_id)
    VALUES (?, ?, 1, ?, ?)
    ON CONFLICT(chat_id) DO UPDATE SET
      active = excluded.active,
      version = subscribers.version + 1,
      last_update_id = excluded.last_update_id,
      last_message_id = excluded.last_message_id,
      updated_at = CURRENT_TIMESTAMP
    WHERE excluded.last_message_id > subscribers.last_message_id
  `).bind(String(message.chat.id), active, update.update_id, message.message_id).run();
  if (result.meta.changes > 0) {
    // A failed acknowledgement must not cause Telegram to replay a committed command.
    try {
      const acknowledgement = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: String(message.chat.id), text: active
          ? "Bạn đã đăng ký nhận bản tin hằng ngày. Bản tin sẽ đến từ lượt gửi tiếp theo. Gõ /stop để hủy."
          : "Bạn đã hủy đăng ký nhận bản tin. Gõ /start để đăng ký lại." }),
        signal: AbortSignal.timeout(10_000), redirect: "error",
      });
      if (!acknowledgement.ok) console.warn("Telegram acknowledgement failed");
    } catch { console.warn("Telegram acknowledgement failed"); }
  }
  return json({ ok: true });
}

async function handle(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  if (url.pathname === "/webhook" && request.method === "POST") return webhook(request, env);
  if (url.pathname !== "/subscribers" && url.pathname !== "/subscribers/disable") {
    return json({ error: "Not found" }, 404);
  }
  if (!env.SUBSCRIBER_API_TOKEN) return json({ error: "Not configured" }, 503);
  if (!await authorized(request.headers.get("Authorization"), `Bearer ${env.SUBSCRIBER_API_TOKEN}`)) {
    return json({ error: "Unauthorized" }, 401);
  }
  if (url.pathname === "/subscribers" && request.method === "GET") {
    const cursor = url.searchParams.get("cursor") ?? "";
    if (cursor && !/^\d{1,20}$/.test(cursor)) return json({ error: "Invalid cursor" }, 400);
    const { results } = await env.DB.prepare(`
      SELECT chat_id, version FROM subscribers
      WHERE active = 1 AND chat_id > ? ORDER BY chat_id LIMIT 101
    `).bind(cursor).all<{ chat_id: string; version: number }>();
    const page = results.slice(0, 100);
    return json({ subscribers: page, next_cursor: results.length > 100 ? page[99].chat_id : null });
  }
  if (url.pathname === "/subscribers/disable" && request.method === "POST") {
    const data = await body(request);
    if (!data || typeof data.chat_id !== "string" || !/^[1-9]\d{0,19}$/.test(data.chat_id)
        || !Number.isSafeInteger(data.version) || data.version < 1) {
      return json({ error: "Invalid subscriber" }, 400);
    }
    const result = await env.DB.prepare(`
      UPDATE subscribers SET active = 0, version = version + 1, updated_at = CURRENT_TIMESTAMP
      WHERE chat_id = ? AND version = ? AND active = 1
    `).bind(data.chat_id, data.version).run();
    return json({ disabled: result.meta.changes > 0 });
  }
  return json({ error: "Method not allowed" }, 405);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try { return await handle(request, env); }
    catch {
      // Do not log exceptions: upstream request URLs can contain bot tokens.
      console.error("Subscription request failed");
      return json({ error: "Service temporarily unavailable" }, 503);
    }
  },
};
