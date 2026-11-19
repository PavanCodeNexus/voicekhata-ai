# VoiceKhata AI: Database Architecture & Supabase Integration

## Overview
VoiceKhata AI operates on a production-ready **dual-engine database architecture**:
1. **Primary Cloud Engine:** **Dedicated Supabase PostgreSQL 17** (hosted in `ap-south-1` AWS Mumbai).
2. **Offline Fallback Engine:** **SQLite with Write-Ahead Logging (WAL)** for zero-network edge kirana counter execution.

---

## 1. Supabase Cloud Project Configuration

- **Supabase Project Name:** `voicekhata-ai`
- **Supabase Project ID:** `chymnlwzaztecurdhoaj`
- **Region:** `ap-south-1` (AWS Mumbai)
- **Supabase API URL:** `https://chymnlwzaztecurdhoaj.supabase.co`
- **Publishable Key:** `sb_publishable_xbaO8_-rAHU6ew6rxP6Dsw_lSBVy5fp`
- **Status:** `ACTIVE_HEALTHY`
- **Database Engine:** PostgreSQL 17.11 (GA)

---

## 2. Core Ledger Design Rules

1. **Integer Paise Storage (`BIGINT`):** Money is stored as integer paise (`amount_paise BIGINT`) to eliminate rounding discrepancies. (₹100 = `10000` paise).
2. **Append-Only Immutable Ledger:** Transactions are never deleted (`DELETE` prohibited). Corrections mark the row `void` and insert an audited replacement referencing `replaces_txn_id`.
3. **UTC Timestamps + Shop Timezone:** Timestamps are recorded in UTC, with daybook boundaries computed in `Asia/Kolkata`.
4. **Sub-2s Query Latency:** Indexed on `(customer_id)`, `(kind, status)`, and `(txn_time)`.
5. **Real-Time Edge-to-Cloud Sync:** Every voice transaction confirmed locally is automatically pushed to the cloud Supabase ledger asynchronously.

---

## 3. Dedicated Tables

- `public.customers`: Customer demographic info, phonetic keys, preferred languages, and WhatsApp opt-in.
- `public.transactions`: Append-only financial ledger with void-and-replace auditability.
- `public.transaction_items`: Itemized line items for voice-generated bills (parchi).
- `public.bills`: Issued PDF bills and voice memo links.
- `public.customer_memory`: Personal Kirana context (e.g. "prefers loose tea").
- `public.audit_log`: Audit trail for compliance and dispute resolution.

---

## 4. Verification

Live HTTP query against `https://chymnlwzaztecurdhoaj.supabase.co/rest/v1/customers` returns `HTTP 200` with Bangalore Kirana seed data.
