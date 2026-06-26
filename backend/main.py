from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Children's Oral Health Chatbot API",
    version="0.1.0",
    description="A prototype API for general child oral-health information.",
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


def get_demo_response(message: str) -> ChatResponse:
    question = message.lower()

    urgent_terms = [
        "difficulty breathing",
        "difficulty swallowing",
        "heavy bleeding",
        "uncontrolled bleeding",
        "facial swelling",
        "face swelling",
        "mouth swelling",
        "neck swelling",
        "swollen face",
        "knocked out",
        "knocked-out",
        "serious injury",
    ]

    if any(term in question for term in urgent_terms):
        return ChatResponse(
            reply=(
                "This may need urgent assessment. Contact a dentist or NHS 111 "
                "for urgent dental advice. Call 999 or go to A&E if there is "
                "heavy bleeding that will not stop, severe swelling affecting "
                "breathing, or a serious injury to the face or jaw."
            ),
            category="urgent",
            urgent=True,
        )

    toothache_terms = ["toothache", "tooth pain", "tooth hurts", "painful tooth"]

    if any(term in question for term in toothache_terms):
        return ChatResponse(
            reply=(
                "Toothache needs a dental assessment. Arrange an appointment "
                "with a dentist as soon as possible. Seek urgent advice if "
                "there is swelling, severe worsening pain, or your child "
                "becomes unwell."
            ),
            category="toothache",
            urgent=False,
        )

    brushing_terms = ["brush", "brushing", "toothbrush", "toothpaste"]

    if any(term in question for term in brushing_terms):
        return ChatResponse(
            reply=(
                "Brush your child's teeth twice a day for around two minutes "
                "using fluoride toothpaste. Brush last thing before bed and "
                "on one other occasion. Parents or carers should help or "
                "supervise young children while they brush."
            ),
            category="brushing",
            urgent=False,
        )

    return ChatResponse(
        reply=(
            "This prototype currently provides general information about "
            "children's oral health. Try asking about tooth brushing, "
            "toothache, or when urgent dental care may be needed."
        ),
        category="general",
        urgent=False,
    )


@app.get("/")
def root():
    return {"message": "Children's Oral Health Chatbot API is running."}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    return get_demo_response(request.message)