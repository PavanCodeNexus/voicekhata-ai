# VoiceKhata AI: Features

Priority: P0 = must work in the live demo. P1 = build in the 24 hours. P2 = stretch. Tick the box when it works in the demo path.

## A. Core voice ledger (P0)

| ID | Feature | Acceptance criteria | Done |
|---|---|---|---|
| F1 | Voice entry | Spoken entry saves the right customer, kind, amount and date; spoken confirmation follows | [ ] |
| F2 | Kannada, Hindi, English code-mix | Same entry works in all three and mixed | [ ] |
| F3 | Number understanding | "340", "three-forty", "teen sau chaalis", "munnooru nalavattu", "dhai sau" all give the right paise | [ ] |
| F4 | Direction guard | "Ramesh ne 200 diye" = payment, "Ramesh ko 200 diye" = credit; bare "diya" triggers read-back | [ ] |
| F5 | Relative dates | "kal 200 diya tha" = yesterday; future tense is not saved as a transaction | [ ] |
| F6 | Corrections and undo | "alla, 430" voids the last entry and saves a replacement; "cancel last entry" voids it | [ ] |
| F7 | Name disambiguation | Two matches trigger "Which Ramesh?" and the next utterance resolves it | [ ] |
| F8 | Spoken answers | "Ramesh ka total?" and "Aaj kitna udhaar gaya?" answered by voice, p95 within 2 s | [ ] |
| F9 | AI disclosure | First spoken turn says it is an AI, in the user's language | [ ] |
| F10 | Customer ledger | Per-customer entries, running balance, statement | [ ] |

## B. Business layer (P1)

| ID | Feature | Acceptance criteria | Done |
|---|---|---|---|
| F11 | Daily day-book | Every transaction appears in the day-book for its date, with totals | [ ] |
| F12 | Bill PDF | Bill number, time, items, amount, balance; labelled "receipt, not a GST invoice" | [ ] |
| F13 | Exports | Excel, CSV and PDF for statement, day-book, date range; owner only | [ ] |
| F14 | Owner dashboard | Today, 3, 7, 30 days: sales, credit given, collections, outstanding with ageing, top debtors, top items, busy hours | [ ] |
| F15 | Share bill | Share sheet or wa.me link; always an explicit tap | [ ] |
| F16 | Safety nets | Confirm large amounts, duplicate check, "340 or 3,400?" sanity check | [ ] |
| F17 | Roles and PIN | Owner and worker roles; PIN for void, export, delete | [ ] |

## C. Judge-impact extras (pick by team size)

| ID | Feature | Why | Effort (rough) | Done |
|---|---|---|---|---|
| E1 | Show-your-work panel + latency HUD | Heard, understood, saved with timings per stage | 1.5 h | [ ] |
| E2 | Language switch + code-mix tags | Judge switches Kannada, Hindi, English mid-session; words colour-tagged | 1.5 h | [ ] |
| E3 | Explain balance by voice | "Why is Ramesh's balance 140?" reads the entries | 1 h | [ ] |
| E4 | Delete my data by voice + purge log | Shows consent is real | 1 h | [ ] |
| E5 | Eval scoreboard in README | Measured accuracy and latency, one command to rerun | 1-2 h | [ ] |
| E6 | Customer Memory (lite, opt-in) | Consent, saved name and purchases, greeting card, rule-based offer (max 20 percent) | 2-3 h | [ ] |
| E7 | Talking Bill | Spoken receipt in the customer's language, only for opted-in customers | 2-3 h | [ ] |
| E8 | Evening voice summary | 20-second spoken day summary from SQL | 1 h | [ ] |

## D. Stretch (P2)

| ID | Feature | Notes | Done |
|---|---|---|---|
| S1 | Shop Lock (speaker verification) | Owner + 3 workers, Open mode default, guest mode, stamps who recorded each entry | [ ] |
| S2 | Local info corner | Weather, mandi price, headlines from trusted sources with source and time; no opinions | [ ] |
| S3 | Big-text counter mode | Readable at arm's length on a low-end phone | [ ] |
| S4 | UPI pay link or QR on bill | Informational only, no pressure wording | [ ] |
| S5 | Opt-in reminders | Polite drafts only; customer must have opted in | [ ] |
| S6 | Offline queue | Entries kept offline, synced later | [ ] |
| S7 | Automatic WhatsApp sending | Needs WhatsApp Business API and approved templates; not for the 24 hours | [ ] |

## Guardrails that apply to every feature

- No lending, no pressure language, no collections.
- No voice cloning. Stock Timbre voices only.
- No ambient recording. No customer voiceprints. No sensitive inference.
- Synthetic or consented data only. Transcripts encrypted and deleted after judging.
- API key only in .env.

## Suggested cut if the team is small (2-3 people)

Core A, then F11-F14, then E1, E2, E3, E4, E5. Move E6 and E7 to the roadmap slide.
