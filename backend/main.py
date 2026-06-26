from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Children's Oral Health Support API",
    version="0.2.0",
    description=(
        "A safety-first demonstration API for general child oral-health "
        "information in a UK context."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    reply: str
    category: Literal["general", "brushing", "toothache", "urgent"]
    urgent: bool


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def get_demo_response(message: str) -> ChatResponse:
    question = message.lower()

    emergency_terms = [
        "difficulty breathing",
        "trouble breathing",
        "cannot breathe",
        "can't breathe",
        "difficulty swallowing",
        "trouble swallowing",
        "cannot swallow",
        "can't swallow",
        "heavy bleeding",
        "uncontrolled bleeding",
        "bleeding that will not stop",
        "serious injury",
        "face injury",
        "jaw injury",
    ]

    urgent_dental_terms = [
        "urgent dental",
        "emergency dental",
        "urgent care",
        "facial swelling",
        "face swelling",
        "swollen face",
        "knocked out",
        "knocked-out",
        "dental injury",
        "tooth injury",
    ]

    toothache_terms = [
        "toothache",
        "tooth pain",
        "tooth hurts",
        "painful tooth",
    ]

    brushing_terms = [
        "brush",
        "brushing",
        "toothbrush",
        "toothpaste",
    ]

    if contains_any(question, emergency_terms):
        return ChatResponse(
            reply=(
                "This may be a medical emergency. Call 999 or go to A&E now "
                "if there is heavy mouth bleeding that will not stop, severe "
                "swelling affecting breathing or swallowing, or a serious "
                "injury to the face or jaw. For urgent dental problems that "
                "do not have these emergency signs, contact a dentist or NHS 111."
            ),
            category="urgent",
            urgent=True,
        )

    if contains_any(question, urgent_dental_terms):
        return ChatResponse(
            reply=(
                "Seek urgent dental advice from your dentist or NHS 111 if "
                "your child has worsening swelling, a knocked-out tooth, a "
                "dental injury, or pain that is severe or not settling. Call "
                "999 or go to A&E if there is heavy bleeding that will not "
                "stop, serious facial or jaw injury, or swelling affecting "
                "breathing or swallowing."
            ),
            category="urgent",
            urgent=True,
        )

    if contains_any(question, toothache_terms):
        return ChatResponse(
            reply=(
                "Toothache should be assessed by a dentist. Arrange a dental "
                "appointment, particularly if the pain lasts, does not settle, "
                "or is accompanied by fever, pain on biting, a bad taste, or "
                "cheek or jaw swelling. If you cannot access a dentist, use "
                "NHS 111 for advice. Go to A&E if swelling affects breathing, "
                "swallowing, or speaking."
            ),
            category="toothache",
            urgent=False,
        )

    if contains_any(question, brushing_terms):
        return ChatResponse(
            reply=(
                "Brush your child's teeth twice a day for about two minutes "
                "with fluoride toothpaste, including last thing before bed. "
                "Parents or carers should brush young children's teeth or "
                "supervise brushing until the child can do it effectively."
            ),
            category="brushing",
            urgent=False,
        )

    return ChatResponse(
        reply=(
            "This demonstration prototype currently supports three parent "
            "pathways: everyday toothbrushing, toothache, and urgent symptoms. "
            "It provides general information only and does not diagnose "
            "dental conditions."
        ),
        category="general",
        urgent=False,
    )


@app.get("/")
def root():
    return {
        "message": "Children's Oral Health Support API is running.",
        "version": "0.2.0",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return get_demo_response(request.message)
