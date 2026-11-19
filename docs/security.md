# VoiceKhata AI: Security and Privacy

Goals: protect the ledger and personal data, keep the ledger tamper-evident, be accountable (who did what), and keep AI behaviour safe. This is a hackathon build with synthetic data. The same design carries over to production.

## Trust boundaries

- Browser (untrusted) to our backend (trusted) over HTTPS and WSS.
- Backend to Gnani (audio out, transcripts and audio back) and to the LLM provider (utterance text only, plus candidate customer names; never phone numbers or full ledgers).
- Share targets (WhatsApp via the phone's share sheet) are outside our control.

## Threats and controls

| Threat | Control |
|---|---|
| API key leaked in repo or browser | Key only in server .env; .env in .gitignore; relay architecture; gitleaks pre-commit and CI; rotate if exposed |
| Eavesdropping | TLS everywhere (HTTPS, WSS) |
| Unauthorised use of the app | PIN login, HttpOnly SameSite cookies, short expiry, auto-lock |
| Worker doing owner-only actions | Server-side RBAC; void, export, delete need the owner role and PIN |
| Ledger tampering | Append-only, void-and-replace, DB guard, audit log |
| Voice replay or lookalike voice (Shop Lock) | Treated as convenience, not security; PIN for risky actions |
| Prompt injection through speech or names | LLM returns schema-constrained JSON only; allow-listed intents; code validates amounts and customers; names are data, never instructions |
| Wrong amounts from model errors | Rules first; two readings must agree; confidence zones; large-amount confirm; undo |
| Data breach at rest | Storage-level encryption plus AES-GCM or Fernet on phone, notes, transcripts, voiceprints; keys outside the DB |
| PII in logs | Redaction helper; no transcripts, audio or phone numbers in logs |
| SQL injection, XSS | ORM with bound parameters; Pydantic validation; output encoding; CSP headers |
| Abuse or DoS | Rate limits, message size limits, idle timeouts on WebSockets |
| Vulnerable dependencies | pip-audit and npm audit before the demo; pin versions after first install |
| Unsafe exports | Owner only; short-lived files; auto-delete after 24 h |
| Messaging without consent | Opt-in flag per customer; sharing only by the shopkeeper's explicit tap |

## Identity and access

| Action | Owner | Worker |
|---|---|---|
| Record entries, view balances, create bills | Yes | Yes |
| Undo own last entry (5 min) | Yes | Yes |
| Void any entry | Yes (PIN) | No |
| Exports, stats | Yes | No |
| Manage users, Shop Lock, delete data | Yes (PIN) | No |

PINs are hashed with argon2id. Tokens are short-lived.

## Encryption and keys

- Field-level encryption with the cryptography library (AES-GCM or Fernet). Keys come from environment variables. In production use a secrets manager or KMS.
- Generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
- Rotate keys by re-encrypting columns with a script. Never commit keys.

## Privacy by design

- Consent first: ask in the user's language, record it in the consents table, save only on yes.
- Data minimisation: Customer Memory stores name, language, visit count, ledger purchases and dictated notes. Nothing else.
- No ambient recording. No customer voiceprints. Voiceprints (staff only, with consent) are encrypted vectors, never audio.
- No inference of religion, caste, politics or health. Do not store opinions heard in chat.
- Rejected audio (Shop Lock) is dropped and never stored.
- Deletion by voice or API removes memory, aliases and consents and writes an audit entry.
- Transcripts expire after 24 h (TTL) and are purged; everything is removed after judging.
- Demo data is synthetic. Teammates who enrol voices or phone numbers give consent.

## AI safety

- First spoken turn says it is an AI, in the user's language.
- The LLM never writes to the database. Only the commit node does, after validation.
- No lending, credit-limit or collection advice. No pressure wording. Reminders are opt-in drafts only.
- Offers are rule-based and capped at 20 percent. The AI only phrases the greeting.
- Local info answers come from trusted sources, show source and time, and carry no opinions.
- Stock Timbre voices only. No cloning.

## Before-the-demo checklist

- [ ] gitleaks clean; .env not in git history
- [ ] .env.example has placeholders only
- [ ] Debug logs off; no transcripts in logs
- [ ] HTTPS/WSS on the hosted link
- [ ] Owner PIN set; demo data is synthetic
- [ ] Purge job tested; plan to wipe data after judging
- [ ] pip-audit and npm audit reviewed
- [ ] Consent screens work in Kannada, Hindi, English
