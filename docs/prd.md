# VoiceKhata AI: Product Requirements Document

| Item | Detail |
|---|---|
| Product | VoiceKhata AI |
| Event | BOLBHARAT - The Gnani Voice AI Innovation Challenge (Track PS2: Voice Khata for kirana stores) |
| Developer | Pavan B C (@PavanCodeNexus) |
| Version | 0.1, design baseline |
| Updated | 17 November 2026 |
| Build window | 24 hours, 21-22 November 2026 |

Related: features.md, structure.md, workflow.md, database.md, api.md, security.md, testing.md

## 1. Summary

VoiceKhata AI is a hands-free, multilingual voice ledger for kirana (neighbourhood grocery) stores. A shopkeeper or counter worker holds a mic button and says an entry in Kannada, Hindi or English, or a mix. The agent records it in the customer's account and in the daily day-book at the same time, speaks a short confirmation, and answers questions like "Ramesh ka total?" by voice. Around that core it makes bills, exports reports, shows owner statistics, and (opt-in) remembers returning customers so the shopkeeper can greet them personally.

## 2. Problem

Many kirana stores sell on credit (udhaar in Hindi, udri in Kannada) and track it in a paper khata book. At the counter nobody can stop to type. Shop talk is fast, code-mixed, full of names and numbers, and happens over street noise. Result: wrong or missing entries, disputes over balances, no bill, and no daily view of sales and dues.

Brief question (Gnani PS2): how can a shopkeeper say "Ramesh ka 340 udhaar, kal 200 diya tha" during a sale, in any supported Indic language with English mixed in, and have the ledger update correctly without touching the screen?

## 3. Goals and non-goals

### Goals
| ID | Goal | Target |
|---|---|---|
| G1 | Exact amounts under noise | 95% or more exact match on the test set |
| G2 | Correct credit vs payment direction | 98% or more |
| G3 | Spoken corrections and name disambiguation | Work in the live demo |
| G4 | Spoken answers | 1.5 s median, 2 s at p95 (end of question to first audio) |
| G5 | One source of truth | Customer ledger and day-book never disagree |
| G6 | Useful business output | Bills, Excel/CSV/PDF exports, owner stats |
| G7 | Responsible AI baseline | All rules met in the live demo |
| G8 | A demo judges remember | Show-your-work panel, Talking Bill, Customer Memory |

### Non-goals
- Lending, credit scoring, credit-limit decisions
- Collections, pressure messages, reminders without opt-in
- Telephony or phone calls (WebSocket streaming only)
- Voice cloning of any real person
- Payment processing, GST tax invoices, bank integrations
- Real customer data or real recordings (synthetic or consented only)
- Always-on listening to or recording of shop conversations
- Inferring sensitive traits (religion, caste, politics, health) about customers

## 4. Users

| Persona | Needs | Pain today |
|---|---|---|
| Owner | Daily totals, who owes what, exports, control over data | Paper books, no summary, disputes |
| Counter worker | Record entries fast with no typing | Rush hour, mistakes, wrong name |
| Customer | A clear bill, a fair balance | Cannot read a written bill, argues over amounts |
| Judge (demo) | Speak any language and see it work | n/a |

## 5. User stories

| ID | As a | I want | So that | Features |
|---|---|---|---|---|
| US1 | Worker | to hold the mic and say an entry | it is saved without typing | F1-F5 |
| US2 | Worker | to fix a mistake by voice | I do not touch the screen | F6 |
| US3 | Worker | the agent to ask "Which Ramesh?" | the entry goes to the right account | F7 |
| US4 | Owner | to ask "Ramesh ka total?" | I hear the balance in about 2 s | F8 |
| US5 | Owner | stats for today, 3 days, 7 days, 30 days | I see how the shop is doing | F14 |
| US6 | Owner | Excel, CSV and PDF exports | I can share and keep records | F13 |
| US7 | Worker | to give a bill and share it to WhatsApp | the customer has proof | F12, F15 |
| US8 | Customer | to hear a short receipt in my language | I understand even if I cannot read | E7 |
| US9 | Owner | returning customers remembered (opt-in) | I can greet them and offer a loyalty discount | E6 |
| US10 | Owner | to delete a customer's data by voice | privacy is real | E4 |
| US11 | Judge | to see timings per step | I can judge speed | E1 |

## 6. Functional requirements

### Voice
- FR-V1 Push-to-talk audio streams (16 kHz, 16-bit mono PCM) through our relay to Gnani Prisma v3.0. The API key never reaches the browser.
- FR-V2 Releasing the mic sends a commit so the utterance finalises. No guessing when the speaker stopped.
- FR-V3 Pressing the mic while the agent speaks stops playback at once (barge-in).
- FR-V4 Replies are spoken with Gnani Timbre v3.0 stock voices only. No cloning.
- FR-V5 The reply language follows the user's last utterance.
- FR-V6 The first spoken turn says it is an AI, in the user's language.

### Understanding
- FR-N1 Amounts accepted as digits, English words, Hindi words, Kannada words and idioms (dhai sau = 250).
- FR-N2 Two independent readings of the amount must agree, otherwise the agent asks.
- FR-N3 Direction from verbs and grammar (ne/ko, -ge); a bare "diya" triggers read-back.
- FR-N4 Relative dates resolved by tense in the shop time zone (Asia/Kolkata).
- FR-N5 Customer matched by exact name, alias and phonetic key; ties trigger a spoken question.
- FR-N6 Corrections void the last entry and insert a replacement.
- FR-N7 Confidence zones: high commits, medium reads back, low asks one question.

### Ledger
- FR-L1 Transactions are append-only. Money is stored as integer paise.
- FR-L2 A transaction is written once. Customer ledger, day-book and stats are views.
- FR-L3 Kinds: credit_sale, payment_received, cash_sale, expense.
- FR-L4 Large amounts (default above Rs 5,000) and duplicates need confirmation.

### Business layer
- FR-B1 Daily day-book per date.
- FR-B2 Bill PDF with bill number, time, items, amount and balance, labelled "receipt, not a GST invoice".
- FR-B3 Exports: customer statement, day-book, date range as Excel, CSV and PDF (owner only).
- FR-B4 Share through the phone share sheet or a wa.me link. No automatic sending in v1.

### Customer Memory (lite, opt-in)
- FR-M1 Ask consent in the user's language before saving anything. Save only on a yes.
- FR-M2 Store name, language, visit count, purchases from the ledger, and notes the shopkeeper dictates.
- FR-M3 Greeting card for the shopkeeper plus rule-based offers (visit count or spend), capped at 20 percent.
- FR-M4 No ambient recording, no customer voiceprints, no sensitive inference, deletion on request.

## 7. Statistics definitions

| Stat | Definition |
|---|---|
| Sales | cash_sale + credit_sale |
| Credit given | credit_sale |
| Collections | payment_received |
| Expenses | expense |
| Net cash movement | cash_sale + payment_received - expense |
| Outstanding | sum of credit_sale minus sum of payment_received (active only) |
| Ageing | FIFO buckets 0-7, 8-30, 31+ days |
| Periods | today, 3 days, 7 days, 30 days |

## 8. Non-functional requirements

- Performance: spoken answers 1.5 s median, 2 s p95. LLM stays out of the answer path.
- Accuracy: see targets in section 10, measured by the eval harness in testing.md.
- Reliability: if the LLM is down, rules still work and the agent asks instead of guessing.
- Device: Android Chrome on a low-end phone, PWA, large touch targets.
- Languages: Kannada, Hindi, English as demo languages; other Prisma v3.0 languages use the same pipeline.
- Security and privacy: see security.md.

## 9. Hackathon constraints (from the brief)

- Build on the Gnani API Platform. STT must be Prisma v3.0, TTS must be Timbre v3.0.
- WebSocket streaming only. No telephony and no phone numbers on the voice channel.
- LLM and orchestration are open. A hosted end-to-end agent platform cannot be the core loop.
- No voice cloning. 5,000 credits per team. Test audio is sourced by the team.
- Responsible AI baseline: AI disclosure in the first turn, synthetic or consented data, transcripts encrypted and deleted after judging, no lending or pressure language, API key in .env and .gitignore.
- Deliverables: working prototype, public GitHub repo with README (setup, architecture diagram, Gnani services used), 2-3 minute demo video, pitch deck of up to 6 slides, live demo.
- Judging (100): live judge test 30, speech depth 20, fit for target user 20, innovation 10, Responsible AI 10, demo and docs 10.

## 10. Success metrics

| Metric | Target | How measured |
|---|---|---|
| Exact amount match | 95% or more | eval/run_eval.py on the noisy set |
| Direction accuracy | 98% or more | same |
| Date accuracy | 95% or more | same |
| Correction success | 90% or more | same |
| Disambiguation success | 90% or more | same |
| Spoken answer latency | p50 1.5 s, p95 2 s | latency HUD and eval script |
| Secrets in repo | 0 | gitleaks in pre-commit and CI |

## 11. Assumptions, risks, open questions

Assumptions: the API key and credits work; Timbre v3.0 streams audio; judges speak live, so the default mode accepts any speaker.

Risks: STT errors in heavy noise; Hindi coverage in tests; scope creep; WhatsApp sending limits; LLM latency; API downtime.

Open questions to confirm with the organizers:
1. Is pre-written code allowed before the event?
2. How are the 5,000 credits applied to the account?
3. Is storing synthetic customer phone numbers for bills allowed under "no phone numbers"?
4. Exact Timbre v3.0 streaming endpoint and supported audio formats.
5. Exact language codes to use with Prisma v3.0.

## 12. Timeline

- 17-20 November: account and key, API spikes (STT, TTS), test phrases and word lists (data only), noise clips, README and deck skeleton, team roles.
- 21-22 November: 24-hour build. See the build plan in workflow.md.
- After judging: purge transcripts and demo data.
