# MailGuard

A human-in-the-loop email agent built with **LangChain** + **LangGraph**.

The agent can look up contacts, read previously sent emails and draft new ones, but it can
never send anything without a human decision — `approve`, `edit` or `reject`.

Runs fully local on **Ollama** by default, and falls back to **OpenAI**, **Gemini** or
**Grok** if you drop in an API key, so anyone can pick it up and try it.

## Features

- Human in the loop — every send pauses and waits for an explicit decision.
- `approve` / `edit` / `reject` on each draft, edited mails go out with your text.
- Four providers with automatic fallback: ollama -> openai -> gemini -> grok.
- Three tools: `searchContact`, `readEmail`, `sendEmail`.
- SQLite storage for every mail that goes out (`email.db`).
- A REST API on top of the same agent, so other people can test it too.
- LangGraph checkpointing, so a conversation keeps its state even after a restart.

## Requirements

- Python 3.14+
- [Ollama](https://ollama.com/) for the local model (optional if you use a cloud key)
- An API key for whichever cloud provider you want to test with (optional)

## Setup

```bash
uv sync
cp .env.example .env
```

Then open `.env` and fill in a key if you have one, nothing needed for ollama.

To use the local model pull it once:

```bash
ollama pull hermes3:latest
```

Prefer pip?

```bash
python -m venv .venv
.venv\Scripts\activate          # . .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
```

## Usage

```bash
uv run mailguard
```

Type a message, for example:

```
Send an email to ravi about the meeting tomorrow
```

When the agent wants to send, it stops and prints the draft, then asks what to do:

| Choice  | What happens                                       |
| ------- | -------------------------------------------------- |
| approve | Sends the mail exactly as the agent drafted it     |
| edit    | You change the mail id, subject and body, then send |
| reject  | Nothing is sent and nothing is written to the db   |

To see what has been sent so far:

```bash
uv run mailguard --list
```

## API

Same agent, but over HTTP instead of the terminal. Start the server:

```bash
uv run mailguard-api
```

It listens on `http://127.0.0.1:8000`, and FastAPI gives you interactive docs at
**http://127.0.0.1:8000/docs** — open that and use "Try it out", no curl needed.

For development with auto reload:

```bash
uv run uvicorn mailguard.api:app --reload
```

### Endpoints

| Method | Path                | What it does                                    |
| ------ | ------------------- | ----------------------------------------------- |
| GET    | `/health`           | Is the server up                                 |
| POST   | `/chat`             | Send a message, get a reply or a pending approval |
| POST   | `/resume`           | Approve, edit or reject the pending approval     |
| GET    | `/emails`           | Every email that has been sent                    |
| GET    | `/emails/{to}`      | Emails sent to one address                       |

### How a conversation works

The agent cannot send on its own, so a conversation is always two steps. You send a
message, it answers with either a reply or a draft waiting for you.

**Step 1** — send a message:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "send an email to ravi about the meeting", "thread_id": "chat-1"}'
```

`thread_id` is optional, the server makes one and gives it back if you leave it out. Keep it
safe, you need the same one to approve the draft.

The answer is either done, or waiting for you:

```json
{
  "status": "approval_required",
  "thread_id": "chat-1",
  "pending": {"to": "ravi@gmail.com", "subject": "Meeting", "body": "See you at 10"}
}
```

**Step 2** — decide:

```bash
curl -X POST http://127.0.0.1:8000/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "chat-1", "decision": "approve"}'
```

`decision` is one of:

| Decision | Extra fields needed                    | What happens                             |
| -------- | -------------------------------------- | ---------------------------------------- |
| approve  | none                                   | Sends the draft as it is                 |
| edit     | `to`, `subject`, `body`                | Sends it with your changes              |
| reject   | `feedback` (optional)                  | Discards it, nothing is written to the db |

The reply is `{"status": "done", "reply": "..."}`. If the agent decides to send another mail
you get another `approval_required` back, so keep going until you see `done`.

### Locking it down

Set `MAILGUARD_TOKEN` in `.env` and every endpoint except `/health` needs a header:

```bash
curl -H "Authorization: Bearer your-token" http://127.0.0.1:8000/emails
```

Leave it empty and the API stays open, handy for local testing. `MAILGUARD_CORS_ORIGINS`
controls which browser frontends can call it, `*` by default.

## Providers

The agent walks the list below and takes the first one that actually connects, so you can
run it with no keys at all and it will just use your local ollama.

| Order | Provider | Needs                        | Env vars                        |
| ----- | -------- | ---------------------------- | ------------------------------- |
| 1     | ollama   | server running + model pulled | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |
| 2     | openai   | `OPENAI_API_KEY`             | `OPENAI_MODEL`                  |
| 3     | gemini   | `GOOGLE_API_KEY`             | `GEMINI_MODEL`                  |
| 4     | grok     | `XAI_API_KEY`                | `GROK_MODEL`                    |

The model names default to `hermes3:latest`, `gpt-4o-mini`, `gemini-2.0-flash` and
`grok-2-latest`, change them in `.env` if you want something else.

## Project layout

```
mailguard/
├── src/
│   └── mailguard/
│       ├── __init__.py
│       ├── agent.py     # tools, provider fallback, agent setup
│       ├── api.py       # fastapi app, routes, auth
│       ├── db.py        # sqlite helpers
│       └── main.py      # terminal entry point and the approval loop
├── .env.example
├── pyproject.toml
└── requirements.txt
```

`agent.py` holds the tools and builds the model, `db.py` keeps the sqlite helpers,
`main.py` runs the conversation in the terminal and `api.py` exposes the same thing over
HTTP.

## Notes

- `MAILGUARD_DB` in `.env` decides where the sqlite file goes, default is `email.db` in the
  current folder. It is gitignored, the table gets created automatically on first use.
- `MAILGUARD_CHECKPOINT_DB` is where the conversation state goes, default `checkpoints.db`.
  This one is also gitignored.
- The `contacts` table inside `agent.py` is a hardcoded name to email map, swap it for
  something real if you need actual people.
