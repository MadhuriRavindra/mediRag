# MediRAG

A personal, lifelong health record assistant. A patient uploads medical reports, asks questions in plain language, and compares values over time. Only the patient, and doctors the patient chooses, can see the records.

> **Status: work in progress.** Phase 1 (accounts and access) is done. Report upload, question answering, trends and doctor access are planned (see the roadmap).

> **Disclaimer:** MediRAG is a learning and portfolio project. It does not give medical advice or diagnoses. Use synthetic data only, not real patient records.

## Goals

- Patients register, log in and upload their medical reports.
- The system extracts values (blood sugar, cholesterol, BP, weight and so on) and stores the report text.
- Patients ask questions such as "explain my report" or "compare my BP from two years ago with now".
- Doctors can see a patient's records only after the patient grants access.
- Later: connect to a nutrition agent (diet plans) and to phone health data (calories burned).

## What works now (Phase 1)

- Registration with input validation (username 3+ characters, password 10+ characters, role `patient` or `doctor`)
- Login with JWT tokens that expire after 30 minutes
- Passwords hashed with argon2, never stored in plain text
- Lockout after 5 failed logins, with a message showing the attempts left and the remaining lock time
- Audit log of registrations, successful and failed logins, and lockouts
- Streamlit login and register screen
- Interactive API docs at `/docs`

## Architecture

| Layer | Responsibility | Technology |
|---|---|---|
| Client | Login, register, later upload and chat | Streamlit |
| API and security | Authentication, roles, access rules, audit log | FastAPI, JWT, argon2 |
| Storage | Users, access grants, audit log (reports and vectors come later) | SQLite via SQLAlchemy |

Planned layers: an ingestion pipeline (text, table and value extraction), an agent (LangGraph) with read-only tools, and a vector store for report text.

### Core security rule

The backend takes the patient identity from the login token. The language model never chooses or changes it. Every query and every vector search will apply that filter in code, so a clever prompt or a poisoned document cannot make the agent read another person's data.

## Project structure

```
medirag/
├── app/
│   ├── __init__.py
│   ├── config.py       # settings and secrets from environment
│   ├── database.py     # database engine and session
│   ├── models.py       # User, AccessGrant, AuditLog
│   ├── security.py     # password hashing, JWT creation and checking
│   └── main.py         # FastAPI routes: /register, /login, /me
├── frontend/
│   └── app.py          # Streamlit UI
├── requirements.txt
├── .env.example
└── README.md
```

## Getting started

### Requirements

- Python 3.10 or newer

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/medirag.git
cd medirag
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with a secret key:

```bash
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))" > .env
```

Never commit `.env`. Use `.env.example` as a reference.

### Run

Open two terminals, both in the project folder with the virtual environment active.

Terminal 1, the backend:

```bash
uvicorn app.main:app --reload
```

Terminal 2, the frontend:

```bash
streamlit run frontend/app.py
```

- Frontend: http://localhost:8501
- API docs: http://127.0.0.1:8000/docs

### Try it

1. Open the Register tab and create a patient account.
2. Log in on the Log in tab.
3. Enter a wrong password a few times and watch the attempts-left message, then the lockout.

## API overview

| Method | Path | Description |
|---|---|---|
| POST | `/register` | Create an account (patient or doctor) |
| POST | `/login` | Log in, returns an access token |
| GET | `/me` | Current user, requires a token |

## Security notes

- Passwords are hashed with argon2.
- Tokens expire after 30 minutes.
- Failed logins are counted per account and lock it for 15 minutes after 5 attempts.
- Security-relevant actions are written to an audit log.
- Secrets live in environment variables and are excluded from git.
- Known limitations in the current version:
  - Anyone can register as a doctor. Doctor accounts will later be created by an admin or require approval.
  - Messages such as "Username already taken" and "attempts left" reveal whether a username exists. This is a deliberate usability trade-off for now.
  - Attempts against an already locked account are not yet written to the audit log.
  - The token is kept only in the browser session, so a page refresh logs the user out.

## Roadmap

- [x] **Phase 1:** accounts, login, lockout, audit log, login UI
- [ ] **Phase 2:** secure report upload, text and table extraction, value extraction, patient confirmation screen
- [ ] **Phase 3:** question answering over a patient's reports, with a patient filter on every search
- [ ] **Phase 4:** trends and comparison across reports
- [ ] **Phase 5:** doctor access grants with expiry, revocation and a patient-visible access log
- [ ] **Phase 6:** red-team tests, evaluation of extraction and retrieval, rate limits, delete-my-data
- [ ] **Later:** diet planning link to a nutrition agent, daily calories burned from a health app

## Planned security tests

- Hidden instructions inside an uploaded report (prompt injection)
- Requests for another patient's records
- Attempts to reveal the system prompt or keys
- A doctor without a grant, and after a grant is revoked or expired
- Oversized files, wrong file types and path-trick file names
- Rapid repeated login attempts
- Questions that tempt the system to diagnose or change medication

## License

To be decided.