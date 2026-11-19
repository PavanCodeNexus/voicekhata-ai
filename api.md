# VoiceKhata AI: API

Base path: /api. JSON everywhere. Auth: PIN login returns a short-lived token (HttpOnly cookie). Roles: owner, worker.

## WebSocket

| Endpoint | Direction | Purpose |
|---|---|---|
| WS /ws/voice | browser to server | Binary frames: 16 kHz 16-bit mono PCM while the mic is held |
| WS /ws/voice | browser to server | JSON control: {"type":"commit"}, {"type":"cancel"} (barge-in), {"type":"lang","value":"kn-IN"} |
| WS /ws/voice | server to browser | JSON events: transcript (partial and final), understood (parsed entry), saved, timings, error |
| WS /ws/voice | server to browser | Binary frames: reply audio chunks (play as they arrive) |

The server opens the Gnani STT and TTS connections itself. The browser never gets the key.

## REST

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | /auth/login | any | PIN login |
| POST | /auth/logout | any | End session |
| GET | /customers?q= | any | Search by name, alias, phonetic |
| POST | /customers | any | Create (consent flag required for memory) |
| GET | /customers/{id}/ledger | any | Entries and running balance |
| DELETE | /customers/{id}/data | owner | Delete customer data (memory, aliases, consents) |
| GET | /transactions?from=&to=&kind= | any | List active entries |
| POST | /transactions | any | Manual entry (fallback to voice) |
| POST | /transactions/{id}/void | owner (worker: own last entry, 5 min) | Void with reason |
| GET | /daybook?date= | any | Day-book for a date |
| GET | /stats?range=today\|3d\|7d\|30d | owner | Sales, credit, collections, outstanding, ageing, top debtors, top items, busy hours |
| POST | /bills/{txn_id} | any | Create bill PDF (and voice receipt if opted in) |
| GET | /bills/{id}/pdf | any | Download bill |
| GET | /exports?type=csv\|xlsx\|pdf&kind=statement\|daybook\|range&... | owner | Export file |
| POST | /consents | any | Record consent (voiceprint, customer_memory, whatsapp_bills, reminders) |
| DELETE | /consents/{id} | any | Revoke |
| GET | /memory/{customer_id}/greeting | any | Greeting card and matching offers |
| POST | /memory/{customer_id}/notes | any | Add a dictated note |
| POST | /voiceprints/enroll | owner | Shop Lock enrolment (stretch) |
| GET | /health | none | Liveness |

## Conventions

- Amounts in responses are integer paise plus a formatted rupee string for display.
- Errors: {"error": {"code": "...", "message": "..."}} with correct HTTP status.
- Every write adds an audit_log row. No transcripts or phone numbers in logs.
- Rate limits on /auth/login and /ws/voice connections.
