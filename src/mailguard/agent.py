import json
import os
import urllib.request

from dotenv import load_dotenv

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from mailguard.db import get_emails, save_email

load_dotenv()

contacts = {
    "ravi": "ravi@gmail.com",
    "rahul": "rahul@gmail.com",
    "aman": "aman@gmail.com",
    "srijan": "srijan@gmail.com"
}

@tool
def sendEmail(to: str, subject: str, body: str) -> str:
    """Send an email to a specified recipient with a subject and body.
    Use this tool when the user explicitly wants to send an email."""


    print(f'Sending email to {to}')
    print(f'Subject: {subject}')
    print(f'Body: {body}')

    save_email(to,subject,body)
    return f'Email successfully sent to {to}'


@tool
def readEmail(mail: str) -> str:
    """Retrieve previously stored emails for a specific email address.
    Use this tool when the user wants to read, view, retrieve, or find
    emails that have already been stored in the email database.
    The input must be an email address, not a person's name.
    """
    result = ""
    emails = get_emails(mail)

    if not emails:
        return f'No emails found for {mail}'

    for email in emails:
        id, recipient, subject, body, timestamp, status = email

        result += (
            f"Email ID: {id}\n"
            f"From/To: {recipient}\n"
            f"Subject: {subject}\n"
            f"Body: {body}\n"
            f"Time: {timestamp}\n"
            f"Status: {status}\n"
            f"{'-' * 40}\n"
        )

    return result

@tool
def searchContact(name: str) -> str:
    """Find a person's email address using their name.
    Use this tool when the user provides a person's name and you need
    to find their email address.
    Do not use this tool to retrieve or read stored emails.
    The input should be a person's name, not an email address.
    """

    name = name.lower().strip()
    email = contacts.get(name)

    if name in contacts.keys():
        return f'{name} found and email id is <{email}>'

    return f'{name} not found.'


def ollama_ready():
    """Check that the local ollama server is up and has the model we want."""

    host = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "hermes3:latest")

    try:
        with urllib.request.urlopen(f'{host}/api/tags', timeout=2) as response:
            tags = json.load(response)
    except Exception:
        return False

    names = [tag['name'] for tag in tags.get('models', [])]
    return any(name.startswith(model.split(':')[0]) for name in names)


def build_model():
    """Return the first model that connects, fall back to the next one if not."""

    providers = [
        ("ollama", os.getenv("OLLAMA_MODEL", "hermes3:latest"), None),
        ("openai", os.getenv("OPENAI_MODEL", "gpt-4o-mini"), "OPENAI_API_KEY"),
        ("google_genai", os.getenv("GEMINI_MODEL", "gemini-2.0-flash"), "GOOGLE_API_KEY"),
        ("xai", os.getenv("GROK_MODEL", "grok-2-latest"), "XAI_API_KEY"),
    ]

    for provider, model, key in providers:
        if provider == "ollama":
            if not ollama_ready():
                print(f'Skipping {provider}, server not reachable or model not pulled')
                continue
        elif not os.getenv(key):
            print(f'Skipping {provider}, {key} not set')
            continue

        try:
            if provider == "ollama":
                return init_chat_model(
                    model=model,
                    model_provider=provider,
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                )

            return init_chat_model(model=model, model_provider=provider)
        except Exception as error:
            print(f'Skipping {provider}, {error}')

    raise SystemExit('No model provider available, check your .env file')


def build_agent(checkpointer=None):
    model = build_model()

    return create_agent(
        model=model,
        tools=[sendEmail, readEmail, searchContact],
        checkpointer=checkpointer or InMemorySaver(),
        middleware=[
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "sendEmail" : {"allowed_decisions":["approve", "edit", "reject"]},
                    "readEmail" : False,
                    "searchContact" : False
                }
            )
        ]

    )
