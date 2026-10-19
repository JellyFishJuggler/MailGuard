from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_ollama import ChatOllama
from langchain.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import tool
from langgraph.types  import Command

from db import get_emails, save_email

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


user_input = input('Prompt: ')


model = ChatOllama(
    model='hermes3:latest'
)
config = {"configurable": {"thread_id" : "test_1"}}


llm = create_agent(
    model=model,
    tools=[sendEmail, readEmail, searchContact],
    checkpointer=InMemorySaver(),
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


# print(llm.invoke('Hello beauty'))
response = llm.invoke({
    "messages":[
        HumanMessage(content=user_input)
    ]},
    config=config
)
if "__interrupt__" in response:
    print("Approval Required")
    print(response["__interrupt__"])

    choice = input("Approve/Edit/Reject: ")

    match choice.lower().strip():
        case "approve":
            response = llm.invoke(
                Command(
                    resume={
                        "decisions": [
                            {"type": "approve"}
                        ]
                    }
                ),
                config=config
            )
        case "edit":
            mail = input("Enter the person's mail ID: ")
            subject = input("Enter new subject: ")
            content = input("Enter new content: ")

            response = llm.invoke(
                Command(
                    resume={
                        "decisions": [
                            {
                                "type": "edit",
                                "edited_action": {
                                    "name": "sendEmail",
                                    "args": {
                                        "to": mail,
                                        "subject": subject,
                                        "body": content
                                    }
                                }
                            }
                        ]
                    }
                ),
                config=config
            )
        case "reject":
            response = llm.invoke(
                Command(
                    resume={
                        "decisions": [
                            {"type": "reject"}
                        ]
                    }
                ),
                config=config
            )
        case _:
            print("Invalid choice. Use approve, edit, or reject.")

print(response['messages'][-1].content)