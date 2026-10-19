import sys

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from mailguard.agent import build_agent
from mailguard.db import list_emails


def main():
    if "--list" in sys.argv:
        for email in list_emails():
            print(email)
        return

    user_input = input('Type your message: ')

    llm = build_agent()
    config = {"configurable": {"thread_id" : "test_1"}}

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


if __name__ == "__main__":
    main()
