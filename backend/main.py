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
    region: Literal[
        "England",
        "Wales",
        "Scotland",
        "Northern Ireland",
        "Not sure",
    ] = "Not sure"
    age_group: Literal[
        "Not provided",
        "0-3",
        "3-6",
        "7+",
    ] = "Not provided"


class SourceLink(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    category: Literal["general", "brushing", "toothache", "urgent"]
    urgent: bool
    region: Literal[
        "England",
        "Wales",
        "Scotland",
        "Northern Ireland",
        "Not sure",
    ]
    age_group: Literal[
        "Not provided",
        "0-3",
        "3-6",
        "7+",
    ]
    needs_age_group: bool = False
    source_gap: bool = False
    sources: list[SourceLink] = Field(default_factory=list)


NHS_CHILDRENS_TEETH = SourceLink(
    title="NHS - Children's teeth",
    url="https://www.nhs.uk/live-well/healthy-teeth-and-gums/taking-care-of-childrens-teeth/",
)

NHS_URGENT_DENTIST = SourceLink(
    title="NHS - How to find an emergency or urgent NHS dentist appointment",
    url="https://www.nhs.uk/nhs-services/dentists/how-to-find-an-nhs-dentist-in-an-emergency/",
)

NHS_111_WALES_DENTAL_HELPLINES = SourceLink(
    title="NHS 111 Wales - Dental Helplines",
    url="https://111.wales.nhs.uk/localservices/dentistinformation/",
)

DBH_LOCAL_PDF = SourceLink(
    title="Delivering better oral health PDF - local file, pages 9-11",
    url="file:///C:/Users/Cyb71/Desktop/Delivering_better_oral_health.pdf#page=9",
)


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def infer_age_group(question: str) -> Literal[
    "Not provided",
    "0-3",
    "3-6",
    "7+",
]:
    chinese_number_age_terms = {
        "0-3": ["0岁", "1岁", "2岁", "3岁", "一岁", "两岁", "二岁", "三岁"],
        "3-6": ["4岁", "5岁", "6岁", "四岁", "五岁", "六岁"],
        "7+": [
            "7岁",
            "8岁",
            "9岁",
            "10岁",
            "11岁",
            "12岁",
            "13岁",
            "14岁",
            "15岁",
            "16岁",
            "17岁",
            "七岁",
            "八岁",
            "九岁",
            "十岁",
            "十一岁",
            "十二岁",
            "十三岁",
            "十四岁",
            "十五岁",
            "十六岁",
            "十七岁",
        ],
    }

    for age_group, terms in chinese_number_age_terms.items():
        if contains_any(question, terms):
            return age_group  # type: ignore[return-value]

    digit_age_terms = {
        "0-3": [
            "0 year",
            "1 year",
            "2 year",
            "3 year",
            "0-year",
            "1-year",
            "2-year",
            "3-year",
        ],
        "3-6": [
            "4 year",
            "5 year",
            "6 year",
            "4-year",
            "5-year",
            "6-year",
        ],
        "7+": [
            "7 year",
            "8 year",
            "9 year",
            "10 year",
            "11 year",
            "12 year",
            "13 year",
            "14 year",
            "15 year",
            "16 year",
            "17 year",
            "7-year",
            "8-year",
            "9-year",
            "10-year",
            "11-year",
            "12-year",
            "13-year",
            "14-year",
            "15-year",
            "16-year",
            "17-year",
        ],
    }

    chinese_age_terms = {
        "0-2": ["0岁", "1岁", "2岁", "一岁", "两岁", "二岁"],
        "3-5": ["3岁", "4岁", "5岁", "三岁", "四岁", "五岁"],
        "6-12": [
            "6岁",
            "7岁",
            "8岁",
            "9岁",
            "10岁",
            "11岁",
            "12岁",
            "六岁",
            "七岁",
            "八岁",
            "九岁",
            "十岁",
            "十一岁",
            "十二岁",
        ],
        "13-17": [
            "13岁",
            "14岁",
            "15岁",
            "16岁",
            "17岁",
            "十三岁",
            "十四岁",
            "十五岁",
            "十六岁",
            "十七岁",
        ],
    }

    for age_group, terms in digit_age_terms.items():
        if contains_any(question, terms):
            return age_group  # type: ignore[return-value]

    for age_group, terms in chinese_age_terms.items():
        if age_group in {"0-3", "3-6", "7+"} and contains_any(question, terms):
            return age_group  # type: ignore[return-value]

    return "Not provided"


def age_group_needed(question: str) -> bool:
    age_sensitive_terms = [
        "brush",
        "brushing",
        "toothbrush",
        "toothpaste",
        "fluoride",
        "dentist",
        "dental visit",
        "first dental",
        "teething",
        "baby teeth",
        "milk teeth",
        "adult teeth",
        "lose teeth",
        "mouthwash",
        "刷牙",
        "牙刷",
        "牙膏",
        "含氟",
        "看牙医",
        "换牙",
        "漱口水",
        "漱口水",
        "刷牙",
        "牙膏",
        "含氟",
        "看牙医",
        "换牙",
    ]

    return contains_any(question, age_sensitive_terms)


def build_response(
    reply: str,
    category: Literal["general", "brushing", "toothache", "urgent"],
    urgent: bool,
    region: Literal[
        "England",
        "Wales",
        "Scotland",
        "Northern Ireland",
        "Not sure",
    ],
    age_group: Literal[
        "Not provided",
        "0-3",
        "3-6",
        "7+",
    ],
    needs_age_group: bool = False,
    source_gap: bool = False,
    sources: list[SourceLink] | None = None,
) -> ChatResponse:
    return ChatResponse(
        reply=reply,
        category=category,
        urgent=urgent,
        region=region,
        age_group=age_group,
        needs_age_group=needs_age_group,
        source_gap=source_gap,
        sources=sources or [],
    )


def dental_service_sources_for_region(
    region: Literal[
        "England",
        "Wales",
        "Scotland",
        "Northern Ireland",
        "Not sure",
    ],
) -> list[SourceLink]:
    if region == "Wales":
        return [NHS_111_WALES_DENTAL_HELPLINES, NHS_URGENT_DENTIST]

    if region == "England":
        return [NHS_URGENT_DENTIST]

    return []


def get_demo_response(
    message: str,
    region: Literal[
        "England",
        "Wales",
        "Scotland",
        "Northern Ireland",
        "Not sure",
    ] = "Not sure",
    age_group: Literal[
        "Not provided",
        "0-3",
        "3-6",
        "7+",
    ] = "Not provided",
) -> ChatResponse:
    question = message.lower()
    detected_age_group = infer_age_group(question)
    effective_age_group = (
        detected_age_group if detected_age_group != "Not provided" else age_group
    )

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
        "刷牙",
        "牙刷",
        "牙膏",
    ]

    if (
        age_group_needed(question)
        and effective_age_group == "Not provided"
        and not contains_any(question, emergency_terms + urgent_dental_terms)
    ):
        return build_response(
            reply=(
                "To give more age-appropriate guidance, please choose the "
                "child's age group: 0-3, 3-6, or 7+."
            ),
            category="general",
            urgent=False,
            region=region,
            age_group=effective_age_group,
            needs_age_group=True,
            sources=[NHS_CHILDRENS_TEETH, DBH_LOCAL_PDF],
        )

    if contains_any(question, emergency_terms):
        return build_response(
            reply=(
                "This may be a medical emergency. Call 999 or go to A&E now "
                "if there is heavy mouth bleeding that will not stop, severe "
                "swelling affecting breathing or swallowing, or a serious "
                "injury to the face or jaw. For urgent dental problems that "
                "do not have these emergency signs, contact a dentist or NHS 111."
            ),
            category="urgent",
            urgent=True,
            region=region,
            age_group=effective_age_group,
            sources=[NHS_URGENT_DENTIST],
        )

    if (
        region in ["Scotland", "Northern Ireland", "Not sure"]
        and contains_any(
            question,
            urgent_dental_terms + toothache_terms,
        )
    ):
        return build_response(
            reply=(
                "The current approved knowledge base does not yet contain "
                f"enough location-specific official sources for {region}. "
                "Please choose England or Wales if that applies, or use your "
                "local official dental or urgent-care service. Call 999 or go "
                "to A&E for life-threatening symptoms such as breathing "
                "difficulty, heavy bleeding, or serious face or jaw injury."
            ),
            category="general",
            urgent=False,
            region=region,
            age_group=effective_age_group,
            source_gap=True,
        )

    if contains_any(question, urgent_dental_terms):
        sources = dental_service_sources_for_region(region)
        return build_response(
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
            region=region,
            age_group=effective_age_group,
            sources=sources,
        )

    if contains_any(question, toothache_terms):
        sources = dental_service_sources_for_region(region)
        return build_response(
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
            region=region,
            age_group=effective_age_group,
            sources=sources,
        )

    if contains_any(question, brushing_terms):
        return build_response(
            reply=(
                f"For the {effective_age_group} age group, brush your child's teeth twice a day for about two minutes "
                "with fluoride toothpaste, including last thing before bed. "
                "Parents or carers should brush young children's teeth or "
                "supervise brushing until the child can do it effectively."
            ),
            category="brushing",
            urgent=False,
            region=region,
            age_group=effective_age_group,
            sources=[NHS_CHILDRENS_TEETH, DBH_LOCAL_PDF],
        )

    return build_response(
        reply=(
            "This demonstration prototype currently supports three parent "
            "pathways: everyday toothbrushing, toothache, and urgent symptoms. "
            "It provides general information only and does not diagnose "
            "dental conditions."
        ),
        category="general",
        urgent=False,
        region=region,
        age_group=effective_age_group,
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
    return get_demo_response(
        request.message,
        region=request.region,
        age_group=request.age_group,
    )
