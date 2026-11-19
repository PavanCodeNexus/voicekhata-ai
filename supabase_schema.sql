-- ==============================================================================
-- VoiceKhata AI — Dedicated Supabase PostgreSQL Schema
-- Project: voicekhata-ai (https://chymnlwzaztecurdhoaj.supabase.co)
-- ==============================================================================
-- Storage Rule: Money in integer paise (BIGINT) - Never floating point numbers.
-- Ledger Rule: Append-only ledger with void-and-replace auditability.
-- ==============================================================================

-- 1. Customers Table
CREATE TABLE IF NOT EXISTS public.customers (
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
CREATE TABLE IF NOT EXISTS public.transactions (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES public.customers(id),
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
    replaces_txn_id INTEGER REFERENCES public.transactions(id)
);

-- 3. Transaction Items (for itemized parchi billing)
CREATE TABLE IF NOT EXISTS public.transaction_items (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES public.transactions(id),
    name TEXT NOT NULL,
    qty REAL,
    unit TEXT,
    unit_price_paise BIGINT,
    line_total_paise BIGINT
);

-- 4. Bills Table (Parchi records)
CREATE TABLE IF NOT EXISTS public.bills (
    id SERIAL PRIMARY KEY,
    bill_no INTEGER NOT NULL UNIQUE,
    transaction_id INTEGER NOT NULL REFERENCES public.transactions(id),
    customer_id INTEGER REFERENCES public.customers(id),
    customer_name TEXT,
    amount_paise BIGINT NOT NULL,
    pdf_path TEXT,
    voice_path TEXT,
    shared_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Customer Memory (Opt-in)
CREATE TABLE IF NOT EXISTS public.customer_memory (
    customer_id INTEGER PRIMARY KEY REFERENCES public.customers(id),
    notes TEXT,
    visit_count INTEGER DEFAULT 1,
    last_visit_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Audit Log
CREATE TABLE IF NOT EXISTS public.audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    detail TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for sub-2s query speeds
CREATE INDEX IF NOT EXISTS idx_customers_name ON public.customers(name);
CREATE INDEX IF NOT EXISTS idx_txn_customer ON public.transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_txn_kind_status ON public.transactions(kind, status);
CREATE INDEX IF NOT EXISTS idx_txn_time ON public.transactions(txn_time);

-- Cross-compatibility views with vk_ prefix
CREATE OR REPLACE VIEW public.vk_customers AS SELECT * FROM public.customers;
CREATE OR REPLACE VIEW public.vk_transactions AS SELECT * FROM public.transactions;

-- Seed Synthetic Bangalore Kirana Customers
INSERT INTO public.customers (id, name, alias, phonetic_key, phone, language, whatsapp_opt_in) VALUES
(1, 'Ramesh Sharma', 'Sharma ji (Kirana)', 'RMSHRM', '+91 98765 43210', 'hi-IN', 1),
(2, 'Ramesh Verma', 'Verma ji (Tailor)', 'RMVRM', '+91 98765 43211', 'kn-IN', 1),
(3, 'Suresh Kumar', 'Dairy Suresh', 'SRSKMR', '+91 98765 43212', 'kn-IN', 1),
(4, 'Anand Gowda', 'Vegetable vendor', 'ANDGWD', '+91 98765 43213', 'kn-IN', 1),
(5, 'Murugan K', 'Auto driver', 'MRGNK', '+91 98765 43214', 'ta-IN', 1),
(6, 'Priya Reddy', 'Silk teacher', 'PRYRD', '+91 98765 43215', 'te-IN', 1)
ON CONFLICT (id) DO NOTHING;

SELECT setval('public.customers_id_seq', 6, true);

INSERT INTO public.transactions (customer_id, customer_name, kind, amount_paise, txn_time, note) VALUES
(1, 'Ramesh Sharma', 'credit_sale', 45000, CURRENT_TIMESTAMP - INTERVAL '1 day', 'Previous opening balance'),
(4, 'Anand Gowda', 'credit_sale', 65000, CURRENT_TIMESTAMP - INTERVAL '1 day', 'Previous opening balance'),
(3, 'Suresh Kumar', 'credit_sale', 20000, CURRENT_TIMESTAMP - INTERVAL '1 day', 'Previous opening balance')
ON CONFLICT DO NOTHING;
