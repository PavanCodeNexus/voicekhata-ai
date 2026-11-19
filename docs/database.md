# VoiceKhata AI: Database

Dialect: PostgreSQL (production). SQLite for the demo with SQLAlchemy models; notes at the end.

## Rules

1. Money is stored as integer paise (BIGINT). Never floats.
2. Timestamps are stored in UTC. Day boundaries and relative dates use the shop time zone (Asia/Kolkata).
3. The ledger is append-only. A correction marks the old row void and inserts a replacement linked by replaces_txn_id. Nothing is deleted.
4. Write once, read many. Balances, day-book and statistics are views, not copies.
5. Every table carries shop_id (or reaches it through a parent) so the design can grow to many shops.
6. Sensitive columns (phone, notes, transcript text, voiceprint) are encrypted in the app (AES-GCM or Fernet) on top of storage-level encryption.
7. Demo data is synthetic. Transcripts expire and are purged.

## Tables

```sql
CREATE TABLE shops (
  id            UUID PRIMARY KEY,
  name          TEXT NOT NULL,
  timezone      TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  default_lang  TEXT NOT NULL DEFAULT 'kn-IN',
  upi_vpa       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  id            UUID PRIMARY KEY,
  shop_id       UUID NOT NULL REFERENCES shops(id),
  display_name  TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN ('owner','worker')),
  pin_hash      TEXT NOT NULL,                 -- argon2id
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE consents (
  id            UUID PRIMARY KEY,
  shop_id       UUID NOT NULL REFERENCES shops(id),
  subject_type  TEXT NOT NULL CHECK (subject_type IN ('user','customer')),
  subject_id    UUID NOT NULL,
  purpose       TEXT NOT NULL CHECK (purpose IN
                  ('voiceprint','whatsapp_bills','reminders','customer_memory','data_storage')),
  granted_at    TIMESTAMPTZ NOT NULL,
  revoked_at    TIMESTAMPTZ
);

CREATE TABLE voiceprints (                       -- Shop Lock (stretch)
  id            UUID PRIMARY KEY,
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  embedding_enc BYTEA NOT NULL,                -- encrypted vector, never raw audio
  model         TEXT NOT NULL,
  consent_id    UUID NOT NULL REFERENCES consents(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE customers (
  id              UUID PRIMARY KEY,
  shop_id         UUID NOT NULL REFERENCES shops(id),
  name            TEXT NOT NULL,
  phonetic_key    TEXT NOT NULL,
  phone_enc       BYTEA,                       -- synthetic in demos
  language        TEXT,                        -- for Talking Bill
  whatsapp_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE customer_aliases (
  id            UUID PRIMARY KEY,
  customer_id   UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  alias         TEXT NOT NULL,                 -- e.g. 'Dairy Ramesh'
  phonetic_key  TEXT NOT NULL
);

CREATE TABLE customer_memory (                   -- Customer Memory (opt-in)
  customer_id   UUID PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
  notes_enc     BYTEA,                         -- dictated by the shopkeeper
  interests     TEXT,                          -- JSON array of short tags
  visit_count   INTEGER NOT NULL DEFAULT 0,
  last_visit_at TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE offers (
  id            UUID PRIMARY KEY,
  shop_id       UUID NOT NULL REFERENCES shops(id),
  name          TEXT NOT NULL,
  rule_type     TEXT NOT NULL CHECK (rule_type IN ('visit_count','spend_total')),
  threshold     BIGINT NOT NULL,               -- visits, or paise
  window_days   INTEGER NOT NULL DEFAULT 30,
  discount_pct  NUMERIC(4,1) NOT NULL CHECK (discount_pct > 0 AND discount_pct <= 20),
  active        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE transcripts (
  id            UUID PRIMARY KEY,
  shop_id       UUID NOT NULL REFERENCES shops(id),
  text_enc      BYTEA NOT NULL,
  language      TEXT,
  speaker_id    UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ NOT NULL           -- default now() + 24 h
);

CREATE TABLE transactions (
  id               UUID PRIMARY KEY,
  shop_id          UUID NOT NULL REFERENCES shops(id),
  customer_id      UUID REFERENCES customers(id),
  kind             TEXT NOT NULL CHECK (kind IN
                     ('credit_sale','payment_received','cash_sale','expense')),
  amount_paise     BIGINT NOT NULL CHECK (amount_paise > 0),
  txn_time         TIMESTAMPTZ NOT NULL,       -- when it happened ('kal' = yesterday)
  recorded_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  recorded_by      UUID REFERENCES users(id),
  source           TEXT NOT NULL DEFAULT 'voice' CHECK (source IN ('voice','manual')),
  transcript_id    UUID REFERENCES transcripts(id),
  parse_confidence REAL,
  note             TEXT,
  status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','void')),
  voided_at        TIMESTAMPTZ,
  void_reason      TEXT,
  replaces_txn_id  UUID REFERENCES transactions(id),
  CHECK (kind IN ('cash_sale','expense') OR customer_id IS NOT NULL)
);

CREATE TABLE transaction_items (
  id               UUID PRIMARY KEY,
  transaction_id   UUID NOT NULL REFERENCES transactions(id),
  name             TEXT NOT NULL,
  qty              NUMERIC(10,3),
  unit             TEXT,
  unit_price_paise BIGINT,
  line_total_paise BIGINT
);

CREATE TABLE bills (
  id             UUID PRIMARY KEY,
  shop_id        UUID NOT NULL REFERENCES shops(id),
  bill_no        BIGINT NOT NULL,
  transaction_id UUID NOT NULL REFERENCES transactions(id),
  customer_id    UUID REFERENCES customers(id),
  pdf_ref        TEXT NOT NULL,                -- file path or object key
  voice_ref      TEXT,                         -- Talking Bill audio
  language       TEXT,
  shared_via     TEXT,                         -- 'share_sheet' or 'wa_link'
  shared_at      TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (shop_id, bill_no)
);

CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  shop_id     UUID NOT NULL,
  actor_id    UUID,
  action      TEXT NOT NULL,                   -- txn.create, txn.void, export, login, data.delete
  entity      TEXT,
  entity_id   UUID,
  detail      JSONB,                           -- no secrets, no raw PII
  at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE info_cache (                        -- Local info corner (stretch)
  id          UUID PRIMARY KEY,
  topic       TEXT NOT NULL,                   -- 'weather', 'mandi_price', 'news'
  payload     TEXT NOT NULL,
  source_url  TEXT NOT NULL,
  fetched_at  TIMESTAMPTZ NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL
);
```

LangGraph checkpoint tables are created by the checkpointer library, not by us.

## Append-only guard (PostgreSQL)

```sql
CREATE OR REPLACE FUNCTION txn_guard() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'transactions are append-only';
  END IF;
  IF NEW.shop_id <> OLD.shop_id OR NEW.kind <> OLD.kind
     OR NEW.amount_paise <> OLD.amount_paise OR NEW.txn_time <> OLD.txn_time
     OR NEW.customer_id IS DISTINCT FROM OLD.customer_id THEN
    RAISE EXCEPTION 'only status, voided_at and void_reason may change';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_txn_guard BEFORE UPDATE OR DELETE ON transactions
  FOR EACH ROW EXECUTE FUNCTION txn_guard();
```

## Views

```sql
CREATE VIEW v_customer_balance AS
SELECT customer_id,
       SUM(CASE kind WHEN 'credit_sale' THEN amount_paise
                     WHEN 'payment_received' THEN -amount_paise ELSE 0 END) AS balance_paise
FROM transactions
WHERE status = 'active' AND customer_id IS NOT NULL
GROUP BY customer_id;

CREATE VIEW v_day_book AS
SELECT shop_id,
       (txn_time AT TIME ZONE 'Asia/Kolkata')::date AS day,
       kind, COUNT(*) AS entries, SUM(amount_paise) AS total_paise
FROM transactions
WHERE status = 'active'
GROUP BY shop_id, day, kind;

CREATE VIEW v_daily_summary AS
SELECT shop_id,
       (txn_time AT TIME ZONE 'Asia/Kolkata')::date AS day,
       SUM(CASE WHEN kind IN ('cash_sale','credit_sale') THEN amount_paise ELSE 0 END) AS sales_paise,
       SUM(CASE WHEN kind = 'credit_sale' THEN amount_paise ELSE 0 END)       AS credit_given_paise,
       SUM(CASE WHEN kind = 'payment_received' THEN amount_paise ELSE 0 END)  AS collected_paise,
       SUM(CASE WHEN kind = 'expense' THEN amount_paise ELSE 0 END)           AS expenses_paise,
       SUM(CASE WHEN kind IN ('cash_sale','payment_received') THEN amount_paise
                WHEN kind = 'expense' THEN -amount_paise ELSE 0 END)          AS net_cash_paise,
       COUNT(*) AS entries
FROM transactions
WHERE status = 'active'
GROUP BY shop_id, day;
```

## Indexes

```sql
CREATE INDEX ix_txn_shop_time   ON transactions (shop_id, txn_time);
CREATE INDEX ix_txn_customer    ON transactions (customer_id, txn_time);
CREATE INDEX ix_txn_shop_kind   ON transactions (shop_id, kind, txn_time);
CREATE INDEX ix_cust_phonetic   ON customers (shop_id, phonetic_key);
CREATE INDEX ix_alias_phonetic  ON customer_aliases (phonetic_key);
CREATE INDEX ix_transcript_exp  ON transcripts (expires_at);
```

## Useful queries

Top debtors:
```sql
SELECT c.name, b.balance_paise
FROM v_customer_balance b JOIN customers c ON c.id = b.customer_id
WHERE c.shop_id = :shop AND b.balance_paise > 0
ORDER BY b.balance_paise DESC LIMIT 5;
```

Busy hours (last 30 days):
```sql
SELECT EXTRACT(HOUR FROM (txn_time AT TIME ZONE 'Asia/Kolkata')) AS hr, COUNT(*) AS entries
FROM transactions
WHERE shop_id = :shop AND status = 'active' AND txn_time >= now() - INTERVAL '30 days'
GROUP BY hr ORDER BY hr;
```

Ageing is computed in ledger/stats.py: for each customer, apply payments to the oldest credit first (FIFO), then bucket what is left by age: 0-7, 8-30, 31+ days.

## Retention

| Table | Retention |
|---|---|
| transcripts | 24 h TTL, purge job; all removed after judging |
| voiceprints | Until consent is revoked or deleted on request |
| customer_memory, consents | Deleted with the customer on request |
| transactions, bills | Kept for the shop; demo data wiped after judging |
| audit_log | Actions only, no raw PII |

## SQLite notes (demo)

- UUID as TEXT, BYTEA as BLOB, TIMESTAMPTZ as ISO text in UTC, JSONB as TEXT, BIGSERIAL as INTEGER PRIMARY KEY.
- No trigger required: enforce append-only in ledger/service.py (only status, voided_at, void_reason may change).
- For day grouping use date(txn_time, '+5 hours', '+30 minutes').
- Seed with scripts/seed_demo.py (synthetic shop and customers only).
