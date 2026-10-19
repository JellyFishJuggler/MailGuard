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
- LangGraph checkpointing, so a conversation keeps its state.

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
│       ├── db.py        # sqlite helpers
│       └── main.py      # entry point and the approval loop
├── .env.example
├── pyproject.toml
└── requirements.txt
```

`agent.py` holds the tools and builds the model, `db.py` keeps the sqlite helpers and
`main.py` runs the conversation and the approve/edit/reject loop.

## Notes

- `MAILGUARD_DB` in `.env` decides where the sqlite file goes, default is `email.db` in the
  current folder. It is gitignored, the table gets created automatically on first use.
- The `contacts` table inside `agent.py` is a hardcoded name to email map, swap it for
  something real if you need actual people.
