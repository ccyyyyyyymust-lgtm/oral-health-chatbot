import re

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from knowledge import (
    DBOH_GUIDANCE,
    NHS_CHILDRENS_TEETH,
    NHS_111_WALES,
    NHS_URGENT_DENTIST,
    retrieve_knowledge,
    unique_sources,
)
from llm import generate_reply
from nhs_services import (
    ServiceSearchError,
    extract_uk_postcode,
    format_uk_postcode,
    format_services_fallback,
    format_services_for_model,
    is_dentist_search_query,
    is_wales_postcode,
    search_wales_dentists_offline,
    search_england_dentists,
)
from rate_limit import rate_limiter
from safety import check_safety, contains_any
from schemas import (
    AgeGroup,
    ChatRequest,
    ChatResponse,
    DentalServiceResult,
    Region,
    SourceLink,
)


load_dotenv()


app = FastAPI(
    title="Children's Oral Health Support API",
    version="0.3.0",
    description=(
        "A safety-first demonstration API for general child oral-health "
        "information in a UK context."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

NHS_DENTIST_DIRECTORY = SourceLink(
    title="NHS - Find a dentist",
    url="https://www.nhs.uk/service-search/find-a-dentist",
)

AGE_SENSITIVE_BRUSHING_TERMS = (
    "brush",
    "toothbrush",
    "toothpaste",
    "fluoride",
    "刷牙",
    "牙刷",
    "牙膏",
    "含氟",
)

TOOTHACHE_TERMS = (
    "toothache",
    "teethache",
    "teeth ache",
    "tooth pain",
    "teeth pain",
    "tooth hurts",
    "painful tooth",
    "uncomfortable",
    "sore tooth",
    "sensitive tooth",
    "牙痛",
    "牙疼",
    "牙齿不舒服",
    "牙齿疼",
)


def infer_age_group(question: str) -> AgeGroup:
    match = re.search(r"\b(\d{1,2})(?:\s|-)?(?:year|yr)s?(?:\s|-)?old\b", question.casefold())
    if match:
        age = int(match.group(1))
        if 0 <= age <= 3:
            return "0-3"
        if 4 <= age <= 6:
            return "3-6"
        if 7 <= age <= 17:
            return "7+"

    chinese_match = re.search(r"(\d{1,2})\s*岁", question)
    if chinese_match:
        age = int(chinese_match.group(1))
        if age <= 3:
            return "0-3"
        if age <= 6:
            return "3-6"
        return "7+"
    return "Not provided"


def effective_age_group(question: str, selected: AgeGroup) -> AgeGroup:
    inferred = infer_age_group(question)
    return inferred if inferred != "Not provided" else selected


def build_response(
    *,
    reply: str,
    category: str,
    urgent: bool,
    region: Region,
    age_group: AgeGroup,
    sources: list[SourceLink] | None = None,
    needs_age_group: bool = False,
    source_gap: bool = False,
    response_mode: str = "fallback",
    dental_services: list[DentalServiceResult] | None = None,
    copyable_postcode: str | None = None,
) -> ChatResponse:
    return ChatResponse(
        reply=reply,
        category=category,  # type: ignore[arg-type]
        urgent=urgent,
        region=region,
        age_group=age_group,
        sources=sources or [],
        needs_age_group=needs_age_group,
        source_gap=source_gap,
        response_mode=response_mode,  # type: ignore[arg-type]
        dental_services=dental_services or [],
        copyable_postcode=copyable_postcode,
    )


def fallback_response(message: str, region: Region, age_group: AgeGroup) -> ChatResponse:
    question = message.casefold()
    brushing_terms = ["brush", "toothbrush", "toothpaste", "fluoride", "刷牙", "牙刷", "牙膏", "含氟"]
    generic_urgent_terms = ["urgent dental", "emergency dental", "emergency dentist", "urgent care"]

    if contains_any(question, generic_urgent_terms):
        if region in ["Scotland", "Northern Ireland", "Not sure"]:
            return build_response(
                reply=(
                    f"The reviewed knowledge base does not yet contain enough location-specific "
                    f"official service information for {region}. Use your local official dental "
                    "or urgent-care service. Call 999 or go to A&E for heavy bleeding that will "
                    "not stop, serious facial or jaw injury, or breathing difficulty."
                ),
                category="general",
                urgent=False,
                region=region,
                age_group=age_group,
                source_gap=True,
            )
        sources = [NHS_URGENT_DENTIST]
        if region == "Wales":
            from knowledge import NHS_111_WALES
            sources.insert(0, NHS_111_WALES)
        return build_response(
            reply=(
                "Seek urgent dental advice from a dentist or NHS 111 for severe or persistent "
                "pain, worsening swelling, a knocked-out tooth, or a dental injury. Call 999 or "
                "go to A&E for heavy bleeding that will not stop, serious facial or jaw injury, "
                "or swelling affecting breathing or swallowing."
            ),
            category="urgent",
            urgent=True,
            region=region,
            age_group=age_group,
            sources=sources,
        )

    if contains_any(question, brushing_terms) and age_group == "Not provided":
        return build_response(
            reply="To give age-appropriate guidance, please choose the child's age group: 0-3, 3-6, or 7+.",
            category="general",
            urgent=False,
            region=region,
            age_group=age_group,
            needs_age_group=True,
            sources=[NHS_CHILDRENS_TEETH, DBOH_GUIDANCE],
        )

    if contains_any(question, TOOTHACHE_TERMS):
        return build_response(
            reply=(
                "I understand that your child's tooth feels uncomfortable. Tooth or mouth pain "
                "should be assessed by a dentist, especially if it is severe, affects sleep or "
                "daily activities, or does not go away. Contact a dentist or NHS 111 for urgent "
                "advice if symptoms worsen. If you can, tell me how long it has lasted and whether "
                "there is swelling, fever, an injury, or difficulty breathing or swallowing."
            ),
            category="toothache",
            urgent=False,
            region=region,
            age_group=age_group,
            sources=[NHS_URGENT_DENTIST],
        )

    if contains_any(question, brushing_terms):
        entries = retrieve_knowledge(message, age_group, region)
        reply = entries[0].text if entries else (
            "Brush twice daily with fluoride toothpaste, including last thing at night."
        )
        return build_response(
            reply=reply,
            category="brushing",
            urgent=False,
            region=region,
            age_group=age_group,
            sources=unique_sources(entries) or [NHS_CHILDRENS_TEETH],
        )

    entries = retrieve_knowledge(message, age_group, region)
    if entries:
        return build_response(
            reply=(
                f"{entries[0].text} This is general information and does not replace advice "
                "from a dentist."
            ),
            category="general",
            urgent=False,
            region=region,
            age_group=age_group,
            sources=unique_sources(entries),
        )

    return build_response(
        reply=(
            "I do not have enough reviewed information to answer that safely yet. Please describe "
            "the symptom, how long it has been present, and whether there is pain, swelling, fever, "
            "injury, or difficulty breathing or swallowing. This service does not provide a diagnosis."
        ),
        category="general",
        urgent=False,
        region=region,
        age_group=age_group,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Children's Oral Health Support API is running.", "version": "0.3.0"}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    client_id = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Please wait a minute and try again.",
            headers={"Retry-After": "60"},
        )

    message = payload.latest_message()
    age_group = effective_age_group(message, payload.age_group)

    safety = check_safety(message)
    if safety:
        return build_response(
            reply=safety.reply,
            category=safety.category,
            urgent=safety.urgent,
            region=payload.region,
            age_group=age_group,
            sources=list(safety.sources),
            response_mode="safety",
        )

    if (
        contains_any(message, AGE_SENSITIVE_BRUSHING_TERMS)
        and age_group == "Not provided"
    ):
        return build_response(
            reply=(
                "To give age-appropriate guidance, please choose the child's "
                "age group: 0-3, 3-6, or 7+."
            ),
            category="general",
            urgent=False,
            region=payload.region,
            age_group=age_group,
            needs_age_group=True,
            sources=[NHS_CHILDRENS_TEETH, DBOH_GUIDANCE],
        )

    postcode = extract_uk_postcode(message)
    postcode_follows_dentist_request = bool(
        postcode
        and any(
            item.role == "user" and is_dentist_search_query(item.content)
            for item in payload.messages[:-1]
        )
    )
    if is_dentist_search_query(message) or postcode_follows_dentist_request:
        if postcode and (payload.region == "Wales" or is_wales_postcode(postcode)):
            display_postcode = format_uk_postcode(postcode)
            services = search_wales_dentists_offline(postcode)
            return build_response(
                reply=(
                    f"I found {len(services)} nearby options from the offline NHS 111 "
                    "Wales directory snapshot. These are directory listings, not live "
                    "availability: call the practice to confirm that it can see your "
                    "child and whether it is accepting NHS patients."
                ),
                category="general",
                urgent=False,
                region="Wales",
                age_group=age_group,
                sources=[NHS_111_WALES],
                source_gap=False,
                copyable_postcode=display_postcode,
                dental_services=[
                    DentalServiceResult(
                        name=service.name,
                        address=service.address,
                        postcode=service.postcode,
                        phone=service.phone,
                        map_url=service.map_url,
                    )
                    for service in services
                ],
            )

        if payload.region not in ("England", "Not sure"):
            return fallback_response(message, payload.region, age_group)

        # A parent may reasonably leave the location selector at its default
        # while supplying an England postcode in the question. In that case,
        # use the England NHS directory instead of bypassing service search.
        service_region: Region = (
            "England" if payload.region == "Not sure" and postcode else payload.region
        )
        if not postcode:
            return build_response(
                reply=(
                    "Please provide an England postcode so I can search the NHS "
                    "directory for dental practices in that area."
                ),
                category="general",
                urgent=False,
                region=service_region,
                age_group=age_group,
                sources=[NHS_DENTIST_DIRECTORY],
            )

        try:
            services = await search_england_dentists(postcode)
        except ServiceSearchError:
            return build_response(
                reply=(
                    "The NHS dental-practice directory is temporarily unavailable. "
                    "You can still copy your postcode or open a map search below. "
                    "You can also use the official NHS Find a dentist service directly."
                ),
                category="general",
                urgent=False,
                region=service_region,
                age_group=age_group,
                sources=[NHS_DENTIST_DIRECTORY],
                source_gap=True,
                copyable_postcode=format_uk_postcode(postcode),
            )

        if not services:
            return build_response(
                reply=(
                    f"I could not find a dental-practice listing for {postcode} "
                    "in the NHS directory. You can still copy your postcode or "
                    "open a map search below, or use the official NHS Find a "
                    "dentist service."
                ),
                category="general",
                urgent=False,
                region=service_region,
                age_group=age_group,
                sources=[NHS_DENTIST_DIRECTORY],
                source_gap=True,
                copyable_postcode=format_uk_postcode(postcode),
            )

        service_context = format_services_for_model(services)
        has_toothache = contains_any(message, TOOTHACHE_TERMS)
        clinical_evidence = (
            retrieve_knowledge(message, age_group, service_region)
            if has_toothache
            else []
        )
        llm_reply = await generate_reply(
            payload.conversation(),
            clinical_evidence,
            service_region,
            age_group,
            additional_evidence=service_context,
        )
        fallback_reply = format_services_fallback(postcode, services)
        if has_toothache:
            fallback_reply += (
                "\n\nFor your child's toothache: arrange a dental assessment. "
                "Contact a dentist or NHS 111 if the pain is severe, affects sleep "
                "or daily activities, or does not go away, or if swelling is getting "
                "bigger. Call 999 or go to A&E if swelling affects breathing or "
                "swallowing, there is heavy bleeding that will not stop, or there is "
                "a serious face or jaw injury."
            )
            if age_group == "Not provided":
                fallback_reply += (
                    "\n\nPlease choose the child's age group (0-3, 3-6, or 7+) "
                    "so any follow-up guidance can be age appropriate."
                )
        return build_response(
            reply=llm_reply or fallback_reply,
            category="toothache" if has_toothache else "general",
            urgent=False,
            region=service_region,
            age_group=age_group,
            sources=[NHS_DENTIST_DIRECTORY, *unique_sources(clinical_evidence)],
            needs_age_group=has_toothache and age_group == "Not provided",
            response_mode="llm" if llm_reply else "fallback",
            dental_services=[
                DentalServiceResult(
                    name=service.name,
                    address=service.address,
                    postcode=service.postcode,
                    phone=service.phone,
                    map_url=service.map_url,
                )
                for service in services
            ],
        )

    evidence = retrieve_knowledge(message, age_group, payload.region)
    llm_reply = await generate_reply(
        payload.conversation(),
        evidence,
        payload.region,
        age_group,
    )
    if llm_reply:
        return build_response(
            reply=llm_reply,
            category="general",
            urgent=False,
            region=payload.region,
            age_group=age_group,
            sources=unique_sources(evidence),
            response_mode="llm",
        )

    return fallback_response(message, payload.region, age_group)
