# mail_approval

A human-in-the-loop email agent built with **LangChain** + **LangGraph**, running entirely on a
local **Ollama** model.

The agent can look up contacts, read previously sent emails, and draft new ones — but it can
never send anything without an explicit human decision (`approve` / `edit` / `reject`).

## Features

- Local inference via Ollama (`hermes3:latest`) — no data leaves your machine.
- `HumanInTheLoopMiddleware` pauses on `sendEmail` and resumes via a LangGraph `Command`.
- Three tools: `searchContact`, `readEmail`, `sendEmail`.
- SQLite persistence of every sent email (`email.db`).
- In-memory checkpointing (`InMemorySaver`) so a single conversation keeps its state.

## Requirements

- Python 3.14+
- [Ollama](https://ollama.com/) installed and running
- The `hermes3` model pulled: `ollama pull hermes3:latest`

## Setup

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run ollama pull hermes3:latest
```

Or with plain pip:

```bash
python -m venv .venv
.venv\Scripts\activate          # . .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
ollama pull hermes3:latest
```

## Usage

```bash
uv run python agent.py
```

You will be prompted for a message, e.g.:

```
Send an email to ravi about the meeting tomorrow
```

When the agent decides to send an email, execution stops and prints an approval request.
Pick one:

| Choice  | Result                                                     |
| ------- | ---------------------------------------------------------- |
| approve | Send the email exactly as the agent drafted it              |
| edit    | Change the recipient, subject and body, then send           |
| reject  | Discard the draft — nothing is written to the database      |

## Tools

| Tool            | Description                                                      |
| --------------- | ---------------------------------------------------------------- |
| `searchContact` | Resolves a person's name to an email address (from `contacts`)   |
| `readEmail`     | Returns all stored emails for a given email address              |
| `sendEmail`     | Stores the email in SQLite — **requires human approval**         |

## Project layout

| File            | Purpose                                                    |
| --------------- | ---------------------------------------------------------- |
| `agent.py`      | Agent definition, tools, and the approval loop             |
| `db.py`         | SQLite helpers: `save_email`, `get_emails`                 |
| `check.py`      | Utility script — dumps every row in `email.db`             |
| `main.py`       | Thin entry point that imports the agent                    |
| `email.db`      | SQLite database of sent emails                              |
| `contacts`      | Name → email lookup table (hard-coded inside `agent.py`)   |

## Notes

- `agent.py` is the real entry point: `main.py` simply imports it, and the whole flow runs
  on import.
- `pyproject.toml` declares a `mail-approval` script pointing at `mail_approval:main`, but the
  code currently lives in flat top-level modules — the packaged console script will not work
  until the code is moved into a `src/mail_approval/` package.
