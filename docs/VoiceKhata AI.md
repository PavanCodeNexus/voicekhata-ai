# VoiceKhata AI

**A hands-free, multilingual voice ledger for kirana stores**

Project report · Build Bengaluru 2.0 · Gnani Voice Hackathon, Track PS2 (Voice Khata for kirana stores)

Prepared by Pavan B C and team, DSATM, Bengaluru · Team name and ID: \[to be filled\] · Version 1.0 · 11 November 2026

Status: design baseline. The product is built during the 24-hour hackathon on 21–22 November 2026. “VoiceKhata AI” is a working title.

## 1. Executive Summary

VoiceKhata AI lets a shopkeeper or counter worker run the shop’s credit book (khata) by talking. In the middle of a sale, over street noise, someone says “Ramesh avrige three-forty udri, ninne two hundred kottidru” (Kannada mixed with English) or “Ramesh ka 340 udhaar, kal 200 diya tha” (Hindi). The system records a ₹340 credit for Ramesh today and a ₹200 payment from him yesterday, speaks a short confirmation, and updates Ramesh’s account and the shop’s day-book at the same moment. Later, an authorised user can ask “Ramesh ka total?” and hear the balance within two seconds.

The platform is a voice-first AI agent. It streams audio to Gnani’s Prisma v3.0 speech-to-text and speaks with Gnani’s Timbre v3.0 text-to-speech over WebSockets. The decision logic runs on LangGraph and LangChain inside a FastAPI backend, the interface is a React progressive web app (PWA), and all data sits in an encrypted SQL database.

Around the voice core, VoiceKhata AI adds what a shop actually needs: PDF bills, a spoken “Talking Bill” voice receipt in the customer’s own language, exports to Excel, CSV and PDF, and an owner dashboard with statistics for today, 3 days, 7 days and 30 days. An optional Shop Lock feature accepts only the enrolled voices of the owner and workers.

**What makes it different**

- Accuracy first: exact amounts, correct credit-versus-payment direction, relative dates and spoken corrections are the core of the design.
- Fast by design: plain-code parsing handles common phrases and an LLM is only a fallback, so spoken answers stay inside the 2-second target.
- One write, many views: every transaction is written once to an append-only ledger. The customer account and the daily book are views of it and cannot disagree.
- Voice in, voice out: the voice that records an entry also queries balances, and customers can receive a spoken receipt.
- Responsible by default: AI disclosure, consent, encryption at rest, polite language and no voice cloning.

**Targets** (to be validated, see Section 11): at least 95% exact-amount match and 98% correct direction on a noisy test set; spoken answers in 1.5 seconds at the median and 2 seconds at the 95th percentile; no secrets in the repository.

## 2. Problem Statement

### 2.1 Background

Many kirana (neighbourhood grocery) stores sell on credit, called udhaar in Hindi and udri in Kannada, and track it in a paper khata (ledger) book. At the counter during rush hour nobody can stop to type into an app. Shop talk is fast, mixes an Indian language with English, is full of names and numbers, and happens over the noise of a busy street.

### 2.2 Problem statement

How can a shopkeeper say an entry such as “Ramesh ka 340 udhaar, kal 200 diya tha” during a sale, in any supported Indic language mixed with English, and have the ledger update correctly without touching the screen? The agent must also answer questions such as “Ramesh ka total?” by voice within two seconds. (Source: Gnani Voice Hackathon brief, PS2, Reference 1.)

### 2.3 Who is affected

- Shop owners and counter workers lose time to book-keeping and make mistakes under pressure.
- Customers face disputes about what they owe, and often get no bill, or a bill they cannot read.
- Owners have no quick daily view of sales, collections and outstanding credit.

### 2.4 Pain points

| Pain point | Consequence |
| --- | --- |
| Writing or typing during rush hour | Entries are delayed, forgotten or batched at night |
| Numbers misheard or mis-noted | Wrong balances and disputes |
| Credit and payment mixed up | A customer who paid still shows as owing |
| Two customers with the same name | The entry lands in the wrong account |
| Relative dates such as “kal” (yesterday or tomorrow) | Entries are dated wrongly |
| Corrections made by overwriting | No audit trail and less trust |
| No daily summary | The owner cannot see sales, collections or outstanding credit |
| Paper books lost or damaged | Permanent loss of records |

### 2.5 Existing solutions and gaps

- **Paper khata:** familiar and free, but slow, error-prone, hard to search and easy to lose.
- **Digital khata apps:** OkCredit, for example, confirms each entry to the customer by SMS and sends WhatsApp or SMS reminders that carry a UPI link, and its paid plans add GST billing (Reference 6). It has also offered a voice-note feature for recording transactions (Reference 7), but we found no public detail on how it handles code-mixed speech, corrections or spoken answers.
- **Gap:** from the public pages we reviewed, we could not find a product that combines accurate understanding of messy, code-mixed, multi-entry speech (with spoken corrections and name disambiguation), spoken answers within two seconds, spoken receipts for customers, and voice-aware access for a shared counter. This is not proof that none exists.

## 3. Objectives and Scope

### 3.1 Objectives

1. Record credit, payment, cash-sale and expense entries by voice with exact amounts, correct direction and correct dates.
2. Handle spoken corrections (“alla, 430”) and ask a short spoken question when two customers share a name.
3. Answer balance and daily-total questions by voice within 2 seconds of the question ending.
4. Keep a customer-wise ledger and a separate daily day-book from a single source of truth.
5. Generate bills and spoken receipts, and export reports as Excel, CSV and PDF.
6. Give the owner clear statistics for today, 3 days, 7 days and 30 days.
7. Meet every Responsible AI rule in the hackathon baseline.

### 3.2 In scope

- A voice ledger for one shop with an owner and up to three workers
- Kannada, Hindi and English (with code-mixing) as demo languages; other Prisma v3.0 languages use the same pipeline
- A PWA for Android phones and low-end browsers with push-to-talk
- Bills, Talking Bill, exports, dashboard and the optional Shop Lock

### 3.3 Out of scope

- Lending, credit scoring or credit-limit decisions
- Debt collection, pressure messaging, or reminders without opt-in
- Telephony or phone-call channels (the brief allows WebSocket streaming only)
- Voice cloning of any real person
- Payment processing, GST-compliant tax invoices and bank integrations
- Real customer data or real call recordings (synthetic or consented data only)

### 3.4 Assumptions

- Each team receives 5,000 Gnani API Platform credits and can create an API key; Prisma v3.0 and Timbre v3.0 are available.
- Judges speak to the agent live, so the default mode accepts any speaker.
- Test audio is recorded by the team or generated with Timbre, then mixed with noise.

## 4. Proposed Solution

### 4.1 Overview

VoiceKhata AI is a voice agent with a business application around it. A push-to-talk button streams the speaker’s voice to the backend, which relays it to Gnani Prisma v3.0. The transcript goes through a LangGraph agent that understands the intent, resolves the customer, checks confidence and writes the entry. The reply is spoken back with Timbre v3.0. Everything else (bills, exports, statistics, the dashboard) reads from the same ledger.

### 4.2 How one voice entry flows

1. The user presses and holds the mic button; the app streams 16 kHz audio to the backend.
2. The backend relays the audio to Prisma v3.0 and receives transcript events; on button release it commits the utterance.
3. With Shop Lock on, speaker verification runs in parallel on the same audio and identifies who spoke.
4. The agent classifies the intent: entry, query, correction, undo, bill or report.
5. A rules-first parser extracts customer, amount, direction, date and items; the LLM is called only if the rules are unsure.
6. The customer is matched by name, alias and phonetic key. If two match, the agent asks “Which Ramesh?” and waits.
7. If confidence is low or the amount is large, the agent reads the entry back and waits for “yes” or a correction.
8. The entry is committed once to the ledger; the customer account and the day-book update automatically.
9. The agent speaks a short confirmation in the user’s language.
10. In the background the system creates the bill PDF and the Talking Bill, ready to share.

### 4.3 Design principles

- Accuracy before features: the judged behaviours (amounts, direction, corrections) are tuned first.
- Rules first, LLM second: deterministic code for common phrases, a model for the rest.
- Write once, read many: no duplicate writes, so no drift between ledgers.
- Ask when unsure: a short spoken question is cheaper than a wrong entry.
- Never delete: corrections void and replace, so every change is auditable.
- Responsible by default: consent, encryption, AI disclosure and polite language are built in.

### 4.4 Differentiators

| Differentiator | What it does | Why it matters |
| --- | --- | --- |
| Number cross-check | Compares two independent readings of an amount (for example the transcript’s digits and our own number-word parser) and asks only if they disagree | Exact amounts under noise |
| Direction guard | Separates “Ramesh ne 200 diye” (he paid) from “Ramesh ko 200 diye” (the shop gave credit) and reads direction back when unclear | Prevents credit and payment mix-ups |
| Spoken answers | Balances and totals come from the database through templates, with no LLM call | Meets the 2-second target |
| Talking Bill | A 10–15 second voice receipt in the customer’s language, shared with the PDF bill | Helps customers who cannot read well; fewer disputes |
| Shop Lock | Accepts only enrolled voices of the owner and workers and stamps each entry with who recorded it | Accountability and rejection of other voices |
| One-write ledger | Customer ledger and day-book are views of one append-only table | Consistent numbers |

## 5. Features

Priority: P0 = must work in the live demo, P1 = build within the 24 hours, P2 = stretch or after the hackathon.

| ID | Feature | Description | Priority |
| --- | --- | --- | --- |
| F1 | Voice entry | Credit sale (udhaar), payment received, cash sale and expense by voice | P0 |
| F2 | Multilingual code-mix | Kannada, Hindi, English and other Prisma v3.0 languages, mixed with English | P0 |
| F3 | Number understanding | Digits, number words (teen sau chaalis, munnooru nalavattu, three-forty) and Hindi idioms such as dhai sau (250) | P0 |
| F4 | Direction guard | Credit versus payment detection, with read-back when unclear | P0 |
| F5 | Relative dates | kal, parso, ninne, naale, monne resolved using tense | P0 |
| F6 | Corrections and undo | “alla, 430” fixes the last amount; “cancel last entry” voids it | P0 |
| F7 | Name disambiguation | Aliases, phonetic matching and a spoken “Which Ramesh?” | P0 |
| F8 | Spoken answers | Balances and totals by voice in under 2 seconds | P0 |
| F9 | AI disclosure | The agent says it is an AI in its first turn, in the user’s language | P0 |
| F10 | Customer ledger | Per-customer entries, running balance and statement | P0 |
| F11 | Daily day-book | Separate daily record of all transactions with totals | P1 |
| F12 | Bills (PDF) | Time, items, amount and balance; labelled “receipt, not a GST invoice” | P1 |
| F13 | Exports | Excel, CSV and PDF for statements, the day-book and date ranges | P1 |
| F14 | Owner dashboard | Today, 3, 7 and 30 days: sales, credit given, collections, outstanding with ageing, top debtors and items, busy hours | P1 |
| F15 | Share bill | Phone share sheet (Web Share API) or wa.me link for the PDF and voice receipt | P1 |
| F16 | Talking Bill | Spoken receipt in the customer’s language with Timbre v3.0 | P1 |
| F17 | Safety nets | Large-amount confirmation, duplicate check, sanity check (“340 or 3,400?”), undo by voice | P1 |
| F18 | Roles and PIN | Owner and worker roles; PIN for void, export and delete | P1 |
| F19 | Shop Lock | Speaker verification for the owner and three workers, with guest mode | P2 |
| F20 | UPI pay link or QR | Informational payment link on the bill, no pressure wording | P2 |
| F21 | Opt-in reminders | Polite reminder drafts for customers who opted in | P2 |
| F22 | Offline queue | Queue entries offline and sync later | P2 |
| F23 | Automatic WhatsApp sending | WhatsApp Business API with approved templates | P2 |

## 6. Technology Stack

| Layer | Technology | Role |
| --- | --- | --- |
| Frontend | React with Vite, Tailwind CSS, Recharts | PWA for low-end Android browsers; dashboard charts |
| Audio capture | Web Audio API with AudioWorklet | Push-to-talk capture and down-sampling to 16 kHz, 16-bit mono PCM |
| Backend | Python 3.11 or newer, FastAPI, Uvicorn | Async WebSockets and REST in one service, same language as the AI stack |
| Speech to text | Gnani Prisma v3.0 (required) | Streaming recognition for Indian languages and code-mixing |
| Text to speech | Gnani Timbre v3.0 (required) | Spoken replies and voice receipts |
| Agent orchestration | LangGraph (open source, self-hosted) and LangChain | State graph with pause and resume; structured output with Pydantic |
| LLM | A low-latency hosted model (for example on Groq), temperature 0, JSON-schema output | Fallback parsing and clarification wording only |
| Fast path | Custom Python parsers for numbers, dates, direction and names | Millisecond parsing of common phrases |
| Speaker verification | SpeechBrain ECAPA-TDNN (Apache-2.0) with PyTorch | Voiceprint embeddings and cosine matching for Shop Lock |
| Database | SQLite for the demo, PostgreSQL for production; SQLAlchemy 2 and Alembic | Relational ledger with constraints and migrations |
| Encryption | Python cryptography library (AES-GCM), encrypted volume or managed-database encryption | Encryption at rest |
| Documents | ReportLab or WeasyPrint, openpyxl and pandas, qrcode | Bill PDF, Excel and CSV exports, UPI QR |
| Sharing | Web Share API, wa.me links | Bill delivery without WhatsApp Business approval |
| Testing | pytest, ffmpeg or pydub noise mixing, a 100-plus phrase test set | Accuracy and latency measurement |
| DevOps | Docker Compose, public GitHub repo, .env with .gitignore | Reproducible setup and secret hygiene |
| Hosting | Render, Railway or AWS (EC2 or Lightsail, S3 for PDFs) | Hosted demo link |

## 7. Platform Design

### 7.1 Architecture overview

| Component | Responsibility |
| --- | --- |
| React PWA | Push-to-talk, live transcript, ledger and day-book screens, dashboard, bill preview and sharing |
| Voice relay (FastAPI WebSocket) | Holds the Gnani API key, streams audio to Prisma, receives transcripts, streams Timbre audio back, cancels playback on barge-in |
| Agent service (LangGraph) | Intent, extraction, customer resolution, confidence policy, commit and reply |
| Parsers | Number, date, direction and name matching in plain code |
| Speaker service (optional) | Voiceprint enrolment and verification for Shop Lock |
| Ledger service | Transactions, balances, day-book, statistics and exports |
| Document service | Bill PDF, Talking Bill audio, and Excel, CSV and PDF reports |
| Database | Encrypted relational store |

End-to-end data flow:

```text
1. Phone (React PWA): hold the mic, send 16 kHz PCM frames over WSS
2. FastAPI voice relay: forward the audio to Gnani Prisma v3.0
3. Prisma v3.0: return transcript events
4. LangGraph agent: understand, resolve the customer, check confidence
   (speaker check runs in parallel when Shop Lock is on)
5. Ledger service: write the transaction once to the encrypted database;
   balances, day-book and statistics update as views
6. Agent: build the reply text in the user’s language
7. Gnani Timbre v3.0: synthesise speech and stream audio chunks
8. FastAPI voice relay: forward the audio to the phone, which plays it
Background: bill PDF, Talking Bill audio and exports are created and offered to the share sheet
```

### 7.2 Voice pipeline

- **Capture.** An AudioWorklet converts microphone input to 16 kHz, 16-bit mono PCM and sends 1,024-byte binary frames over a secure WebSocket to the voice relay. Push-to-talk streams audio only while the button is held, which reduces false triggers and saves API credits.
- **Relay.** The relay opens a streaming connection to Prisma v3.0. Gnani expects the API key and settings as headers on the WebSocket handshake. Browsers cannot set those headers, so the relay does it on the server, which also keeps the key off the device. The language setting is indic-auto or a list of language codes (Reference 3).
- **Endpointing.** Releasing the button sends the commit message that finalises the utterance, so the system never has to guess when the speaker has stopped.
- **Speaking.** Reply text goes to Timbre v3.0 and audio chunks are forwarded to the browser as they arrive, so playback starts before synthesis finishes. Only stock voices are used. Streaming support for v3.0 is to be confirmed in the first technical spike.
- **Barge-in.** Pressing the button while the agent is speaking stops playback, cancels the speech request and starts a new utterance.
- **Languages.** Prisma v3.0 covers Hindi, Bengali, Marathi, Gujarati, Punjabi, Kannada, Telugu, Tamil, Malayalam and English (Reference 4). Timbre v3.0 voices cover the same set (Reference 5). Replies follow the language of the user’s last utterance; the opening AI-disclosure line uses the shop’s saved language.

### 7.3 Agent design (LangGraph)

The agent is a state graph. The state holds the transcript, language, speaker and role, intent, extracted fields (customer candidates, amount in paise, direction, date, items), confidence, any pending question and the result. A checkpointer stores the state so that a pending question (for example “Which Ramesh?”) survives until the next utterance. LangGraph is used as an open-source library inside our own backend, not as a hosted platform, and the LLM stays outside the hot path unless the rules fall back to it.

| Node | Job |
| --- | --- |
| route\_intent | Classify the utterance: entry, query, correction, undo, bill, report or other |
| parse\_rules | Rule-based extraction of amount, direction, date, items and customer text |
| parse\_llm | Fallback structured extraction (JSON schema) when the rules are unsure |
| resolve\_customer | Match against customers by name, alias and phonetic key; detect ambiguity |
| ask\_clarify | Pause for a spoken question and resume on the next utterance |
| confidence\_gate | Apply the confidence policy and the large-amount rule |
| read\_back | Speak the entry and wait for “yes” or a correction |
| commit | Validate and write the transaction in one database transaction |
| apply\_correction | Void the previous entry and write the replacement |
| answer\_query | Run SQL, fill a template, return text (no LLM) |
| make\_documents | Background job: bill PDF and Talking Bill |
| respond | Build the reply text in the user’s language |
