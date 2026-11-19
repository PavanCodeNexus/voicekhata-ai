# VoiceKhata AI: Project Structure

Monorepo with a Python backend and a React PWA frontend.

```text
voicekhata/
├── README.md
├── .env.example            # copy to .env (never commit .env)
├── .gitignore
├── docker-compose.yml
├── docs/                   # prd.md, structure.md, workflow.md, database.md,
│                           # features.md, api.md, security.md, testing.md
├── backend/
│   ├── requirements.txt
│   ├── requirements-optional.txt     # Shop Lock (speaker verification)
│   ├── alembic.ini
│   ├── app/
│   │   ├── main.py                   # FastAPI app, routers, CORS, startup
│   │   ├── config.py                 # settings from .env (pydantic-settings)
│   │   ├── api/                      # REST routes (see api.md)
│   │   │   ├── auth.py
│   │   │   ├── customers.py
│   │   │   ├── transactions.py
│   │   │   ├── stats.py
│   │   │   ├── bills.py
│   │   │   ├── exports.py
│   │   │   ├── consents.py
│   │   │   └── memory.py
│   │   ├── voice/                    # real-time audio
│   │   │   ├── ws_voice.py           # browser WebSocket endpoint
│   │   │   ├── gnani_stt.py          # Prisma v3.0 streaming client
│   │   │   ├── gnani_tts.py          # Timbre v3.0 client
│   │   │   └── session.py            # per-connection state, barge-in, timings
│   │   ├── agent/                    # LangGraph brain
│   │   │   ├── graph.py              # builds the graph
│   │   │   ├── state.py              # AgentState (pydantic)
│   │   │   ├── nodes/                # route_intent, parse_rules, parse_llm,
│   │   │   │                         # resolve_customer, ask_clarify,
│   │   │   │                         # confidence_gate, read_back, commit,
│   │   │   │                         # apply_correction, answer_query, respond
│   │   │   ├── llm.py                # LangChain model wrapper, JSON schema output
│   │   │   └── templates/            # spoken reply templates: kn.py, hi.py, en.py
│   │   ├── nlu/                      # plain-code understanding (fast path)
│   │   │   ├── numbers.py            # digits, words, idioms -> paise
│   │   │   ├── dates.py              # kal / ninne / naale, tense rules
│   │   │   ├── direction.py          # credit vs payment, ne/ko, -ge
│   │   │   ├── names.py              # alias + phonetic matching
│   │   │   └── lexicon/              # json word lists (en, hi, kn)
│   │   ├── ledger/
│   │   │   ├── service.py            # write once, void-and-replace
│   │   │   ├── queries.py            # balances, day-book, top debtors
│   │   │   └── stats.py              # periods, ageing (FIFO)
│   │   ├── documents/
│   │   │   ├── bill_pdf.py
│   │   │   ├── voice_receipt.py      # Talking Bill (Timbre)
│   │   │   ├── export_xlsx.py
│   │   │   ├── export_csv.py
│   │   │   └── export_pdf.py
│   │   ├── memory/                   # Customer Memory (opt-in)
│   │   │   ├── customer_memory.py
│   │   │   ├── offers.py             # rule-based, capped at 20 percent
│   │   │   └── greetings.py
│   │   ├── speaker/                  # stretch: Shop Lock
│   │   │   ├── enroll.py
│   │   │   └── verify.py
│   │   ├── security/
│   │   │   ├── crypto.py             # AES-GCM/Fernet field encryption
│   │   │   ├── auth.py               # PIN login, tokens
│   │   │   ├── rbac.py               # owner / worker
│   │   │   └── redact.py             # log redaction
│   │   ├── db/
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   ├── session.py
│   │   │   └── migrations/           # Alembic
│   │   └── jobs/
│   │       └── purge.py              # delete expired transcripts
│   └── tests/
│       ├── unit/                     # numbers, dates, direction, names
│       ├── integration/              # graph flows, ledger, exports
│       └── fixtures/
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── public/manifest.webmanifest   # PWA
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── audio/
│       │   ├── mic.ts                # getUserMedia, push-to-talk
│       │   ├── pcm-worklet.js        # 16 kHz 16-bit PCM
│       │   └── player.ts             # streaming playback, stop on barge-in
│       ├── api/                      # REST + WebSocket clients
│       ├── pages/                    # Home, Customers, Ledger, DayBook,
│       │                             # Dashboard, Bills, Settings
│       ├── components/               # MicButton, WorkPanel, LatencyHud,
│       │                             # LedgerTable, Charts
│       └── styles/
├── eval/
│   ├── phrases.csv                   # test utterances with expected output
│   ├── audio/                        # self-recorded or Timbre clips (synthetic)
│   ├── noise/                        # street / market noise
│   ├── run_eval.py                   # prints the scoreboard
│   └── scoreboard.md                 # latest results (goes in the README)
└── scripts/
    ├── seed_demo.py                  # synthetic shop, customers, entries
    ├── mix_noise.py                  # mix noise at set SNR
    └── purge_transcripts.py
```

## Conventions

- Python 3.11 or newer, type hints, ruff for lint and format. Async routes and WebSockets.
- Money is integer paise everywhere. Convert to rupees only in the UI and spoken text.
- Times are stored in UTC. Day boundaries and relative dates use Asia/Kolkata.
- Spoken reply text lives only in agent/templates. No hard-coded strings in nodes.
- The LLM never writes to the database. Only the commit node does, after validation.
- Secrets come from .env through config.py. Never log transcripts, phone numbers or keys.
- One feature per branch, small commits, tests with the code (see workflow.md).

## Where does it go?

| I am adding | Put it in |
|---|---|
| A new number word or idiom | backend/app/nlu/lexicon + numbers.py + a test |
| A new spoken reply | backend/app/agent/templates |
| A new stat | ledger/stats.py + api/stats.py + Dashboard component |
| A new export | documents/ + api/exports.py |
| A new table or column | db/models.py + an Alembic migration + database.md |
