# VoiceKhata AI: Database Architecture & Supabase Integration

## Overview
VoiceKhata AI operates on a production-grade **dual-engine database architecture**:
1. **Primary Cloud Engine:** **Supabase PostgreSQL 17** (hosted in `ap-south-1` Mumbai for minimal India latency).
2. **Offline Fallback Engine:** **SQLite with Write-Ahead Logging (WAL)** for zero-network edge kirana counter execution.

---

## 1. Supabase Cloud Configuration

- **Supabase Project ID:** `byxffivsuqhijbdjphsp`
- **Project Name:** `uptime` / VoiceKhata AI
- **Region:** `ap-south-1` (AWS Mumbai)
- **Supabase URL:** `https://byxffivsuqhijbdjphsp.supabase.co`
- **Publishable Key:** `sb_publishable_TC4rn5IotxU75UzR2aU_3Q_0A8NyKf_`
- **Database Engine:** PostgreSQL 17.11 (GA)
- **Direct DB Host:** `db.byxffivsuqhijbdjphsp.supabase.co:5432`

---

## 2. Core Ledger Design Rules

1. **Integer Paise Storage (`BIGINT`):** Money is never stored in floating-point representations to eliminate floating-point arithmetic errors across currencies (₹100 = `10000` paise).
2. **Append-Only Immutable Ledger:** Rows are never mutated or deleted (`DELETE` prohibited). Corrections mark the row status `void` and insert an audited replacement referencing `replaces_txn_id`.
3. **UTC Timestamps + Shop Timezone:** Timestamps are recorded with timezone (`TIMESTAMPTZ` / UTC), with daybook boundaries computed according to `Asia/Kolkata`.
4. **Sub-2s Realtime Query Latency:** Indexed on `(customer_id)`, `(kind, status)`, and `(txn_time)` for instantaneous aggregations.
5. **Multi-Tenant Schema Isolation:** VoiceKhata tables reside in a dedicated PostgreSQL schema `voicekhata` and are exposed via `public.vk_*` views with `INSTEAD OF INSERT` triggers for Supabase PostgREST compatibility.

---

## 3. Schema Definition (`supabase_schema.sql`)

```sql
CREATE SCHEMA IF NOT EXISTS voicekhata;

-- 1. Customers Table
CREATE TABLE IF NOT EXISTS voicekhata.customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    alias TEXT,
    phonetic_key TEXT,
    phone TEXT,
    language TEXT DEFAULT 'kn-IN',
    whatsapp_opt_in INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Append-Only Transactions Table (Money in integer paise)
CREATE TABLE IF NOT EXISTS voicekhata.transactions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES voicekhata.customers(id),
    customer_name TEXT,
    kind TEXT NOT NULL CHECK (kind IN ('credit_sale','payment_received','cash_sale','expense')),
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    txn_time TIMESTAMP WITH TIME ZONE NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    recorded_by TEXT DEFAULT 'worker',
    source TEXT DEFAULT 'voice' CHECK (source IN ('voice','manual')),
    parse_confidence REAL DEFAULT 1.0,
    note TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','void')),
    voided_at TIMESTAMP WITH TIME ZONE,
    void_reason TEXT,
    replaces_txn_id INTEGER REFERENCES voicekhata.transactions(id)
);

-- 3. Itemized Parchi Items
CREATE TABLE IF NOT EXISTS voicekhata.transaction_items (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES voicekhata.transactions(id),
    name TEXT NOT NULL,
    qty REAL,
    unit TEXT,
    unit_price_paise BIGINT,
    line_total_paise BIGINT
);

-- 4. Bills Table
CREATE TABLE IF NOT EXISTS voicekhata.bills (
    id SERIAL PRIMARY KEY,
    bill_no INTEGER NOT NULL UNIQUE,
    transaction_id INTEGER NOT NULL REFERENCES voicekhata.transactions(id),
    customer_id INTEGER REFERENCES voicekhata.customers(id),
    customer_name TEXT,
    amount_paise BIGINT NOT NULL,
    pdf_path TEXT,
    voice_path TEXT,
    shared_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Customer Memory (Opt-In)
CREATE TABLE IF NOT EXISTS voicekhata.customer_memory (
    customer_id INTEGER PRIMARY KEY REFERENCES voicekhata.customers(id),
    notes TEXT,
    visit_count INTEGER DEFAULT 1,
    last_visit_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Audit Log
CREATE TABLE IF NOT EXISTS voicekhata.audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    detail TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Supabase Views with INSTEAD OF Triggers

To allow seamless queries via both the standard Supabase PostgREST API and direct SQL without modifying exposed schema permissions:

```sql
-- Public Views
CREATE OR REPLACE VIEW public.vk_customers AS SELECT * FROM voicekhata.customers;
CREATE OR REPLACE VIEW public.vk_transactions AS SELECT * FROM voicekhata.transactions;
CREATE OR REPLACE VIEW public.vk_transaction_items AS SELECT * FROM voicekhata.transaction_items;
CREATE OR REPLACE VIEW public.vk_bills AS SELECT * FROM voicekhata.bills;

-- Writable View Trigger
CREATE OR REPLACE FUNCTION public.vk_transactions_insert_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO voicekhata.transactions (
        customer_id, customer_name, kind, amount_paise, txn_time,
        recorded_at, recorded_by, source, parse_confidence, note,
        status, voided_at, void_reason, replaces_txn_id
    ) VALUES (
        NEW.customer_id, NEW.customer_name, NEW.kind, NEW.amount_paise, COALESCE(NEW.txn_time, CURRENT_TIMESTAMP),
        COALESCE(NEW.recorded_at, CURRENT_TIMESTAMP), COALESCE(NEW.recorded_by, 'worker'),
        COALESCE(NEW.source, 'voice'), COALESCE(NEW.parse_confidence, 1.0), NEW.note,
        COALESCE(NEW.status, 'active'), NEW.voided_at, NEW.void_reason, NEW.replaces_txn_id
    ) RETURNING id INTO NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_vk_transactions_insert
INSTEAD OF INSERT ON public.vk_transactions
FOR EACH ROW EXECUTE FUNCTION public.vk_transactions_insert_trigger();
```

---

## 5. Dual-Mode Connection Logic (`app/db/session.py` & `supabase_service.py`)

1. **Local SQLite Connection:**
   - WAL mode enabled: `PRAGMA journal_mode = WAL;`
   - Normal synchronous mode: `PRAGMA synchronous = NORMAL;`
   - Foreign key integrity: `PRAGMA foreign_keys = ON;`
2. **Supabase Cloud Sync:**
   - On every voice transaction committed locally, `supabase_service.record_transaction()` asynchronously syncs the row to Supabase `vk_transactions`.
   - The health check at `/api/health` reports `{ "database": { "mode": "supabase", "supabase_connected": true } }`.
   - The frontend displays a green pulsating **Supabase PG (Live)** badge.
