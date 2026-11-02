CREATE TABLE subscribers (
    chat_id TEXT PRIMARY KEY,
    active INTEGER NOT NULL CHECK (active IN (0, 1)),
    version INTEGER NOT NULL CHECK (version > 0),
    last_update_id INTEGER NOT NULL,
    last_message_id INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX subscribers_active_chat ON subscribers(active, chat_id);
