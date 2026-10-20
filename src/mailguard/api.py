import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel

from mailguard.agent import build_agent
from mailguard.db import get_emails, list_emails

TOKEN = os.getenv("MAILGUARD_TOKEN", "")
CHECKPOINT_DB = os.getenv("MAILGUARD_CHECKPOINT_DB", "checkpoints.db")

locks = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        app.state.agent = build_agent(checkpointer=saver)
        yield


app = FastAPI(title="MailGuard", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("MAILGUARD_CORS_ORIGINS", "*").split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    decision: str
    to: str | None = None
    subject: str | None = None
    body: str | None = None
    feedback: str | None = None


class ChatResponse(BaseModel):
    status: str
    thread_id: str
    reply: str | None = None
    pending: dict | None = None


class Email(BaseModel):
    id: int
    recipient: str
    subject: str
    body: str
    timestamp: str
    status: str


def auth(authorization: str = Header(None)):
    if not TOKEN:
        return

    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="bad or missing token")


def get_lock(thread_id):
    if thread_id not in locks:
        locks[thread_id] = asyncio.Lock()

    return locks[thread_id]


def to_email(row):
    return {
        "id": row[0],
        "recipient": row[1],
        "subject": row[2],
        "body": row[3],
        "timestamp": row[4],
        "status": row[5]
    }


def make_reply(result, thread_id):
    if "__interrupt__" in result:
        action = result["__interrupt__"][0].value["action_requests"][0]
        return {
            "status": "approval_required",
            "thread_id": thread_id,
            "pending": action["args"]
        }

    return {
        "status": "done",
        "thread_id": thread_id,
        "reply": str(result["messages"][-1].content)
    }


def make_decision(req):
    match req.decision.lower().strip():
        case "approve":
            return {"type": "approve"}
        case "edit":
            if not (req.to and req.subject and req.body):
                raise HTTPException(status_code=400, detail="edit needs to, subject and body")
            return {
                "type": "edit",
                "edited_action": {
                    "name": "sendEmail",
                    "args": {
                        "to": req.to,
                        "subject": req.subject,
                        "body": req.body
                    }
                }
            }
        case "reject":
            return {"type": "reject", "message": req.feedback or "Rejected by user"}
        case _:
            raise HTTPException(status_code=400, detail="decision must be approve, edit or reject")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(auth)])
async def chat(req: ChatRequest):
    thread_id = req.thread_id or uuid.uuid4().hex

    try:
        async with get_lock(thread_id):
            result = await app.state.agent.ainvoke(
                {
                    "messages": [
                        HumanMessage(content=req.message)
                    ]
                },
                config={"configurable": {"thread_id": thread_id}}
            )
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"model call failed: {error}")

    return make_reply(result, thread_id)


@app.post("/resume", response_model=ChatResponse, dependencies=[Depends(auth)])
async def resume(req: ResumeRequest):
    decision = make_decision(req)
    config = {"configurable": {"thread_id": req.thread_id}}

    checkpoint = await app.state.agent.checkpointer.aget_tuple(config)
    pending = checkpoint.pending_writes if checkpoint else []
    pending = [write for write in (pending or []) if write[1] == "__interrupt__"]

    if not pending:
        raise HTTPException(status_code=400, detail="nothing pending on this thread")

    try:
        async with get_lock(req.thread_id):
            result = await app.state.agent.ainvoke(
                Command(resume={"decisions": [decision]}),
                config=config
            )
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"could not resume: {error}")

    return make_reply(result, req.thread_id)


@app.get("/emails", response_model=list[Email], dependencies=[Depends(auth)])
def emails():
    return [to_email(row) for row in list_emails()]


@app.get("/emails/{recipient}", response_model=list[Email], dependencies=[Depends(auth)])
def emails_for(recipient: str):
    return [to_email(row) for row in get_emails(recipient)]


def run():
    import uvicorn

    uvicorn.run(
        "mailguard.api:app",
        host=os.getenv("MAILGUARD_HOST", "127.0.0.1"),
        port=int(os.getenv("MAILGUARD_PORT", "8000"))
    )
