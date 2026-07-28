import re
from dataclasses import dataclass

from schemas import AgeGroup, Region, SourceLink


NHS_CHILDRENS_TEETH = SourceLink(
    title="NHS - Children's teeth",
    url=(
        "https://www.nhs.uk/live-well/healthy-teeth-and-gums/"
        "taking-care-of-childrens-teeth/"
    ),
)
NHS_URGENT_DENTIST = SourceLink(
    title="NHS - Emergency or urgent dentist appointments",
    url=(
        "https://www.nhs.uk/nhs-services/dentists/"
        "how-to-find-an-nhs-dentist-in-an-emergency/"
    ),
)
NHS_FIND_DENTIST = SourceLink(
    title="NHS - How to find an NHS dentist",
    url=(
        "https://www.nhs.uk/nhs-services/dentists/"
        "how-to-find-an-nhs-dentist/"
    ),
)
NHS_111_WALES = SourceLink(
    title="NHS 111 Wales - Dental Helplines",
    url="https://111.wales.nhs.uk/localservices/dentistinformation/",
)
DBOH_GUIDANCE = SourceLink(
    title="GOV.UK - Delivering better oral health",
    url=(
        "https://www.gov.uk/government/publications/"
        "delivering-better-oral-health-an-evidence-based-toolkit-for-prevention"
    ),
)


@dataclass(frozen=True)
class KnowledgeEntry:
    entry_id: str
    text: str
    keywords: tuple[str, ...]
    source: SourceLink
    age_groups: tuple[AgeGroup, ...] = ()
    regions: tuple[Region, ...] = ()


# These short, reviewed summaries are based on NHS pages and DBOH PDF pages
# 9-11. They are intentionally stored locally so retrieval is deterministic.
ENTRIES = (
    KnowledgeEntry(
        entry_id="england-find-nhs-dentist",
        text=(
            "In England, you can contact any NHS dentist and ask for an NHS "
            "appointment for symptoms or a routine check-up. A practice may "
            "offer both NHS and private care, so ask specifically for an NHS "
            "appointment. You may be placed on a waiting list. If you cannot "
            "find a practice offering NHS appointments, contact your local "
            "integrated care board (ICB), which may be able to tell you where "
            "a local appointment is available."
        ),
        keywords=(
            "find dentist", "find an nhs dentist", "nhs dentist", "dentist near me",
            "dental appointment", "routine check-up", "waiting list", "icb",
            "accepting nhs patients", "register with a dentist",
        ),
        source=NHS_FIND_DENTIST,
        regions=("England",),
    ),
    KnowledgeEntry(
        entry_id="brush-0-3",
        text=(
            "For children up to age 3, start when the first tooth erupts. A "
            "parent or carer should brush twice daily for about two minutes, "
            "including last thing at night, using at least 1,000 ppm fluoride "
            "toothpaste and only a smear of toothpaste."
        ),
        keywords=("brush", "toothpaste", "fluoride", "first tooth", "clean teeth"),
        source=DBOH_GUIDANCE,
        age_groups=("0-3",),
    ),
    KnowledgeEntry(
        entry_id="brush-3-6",
        text=(
            "For children aged 3 to 6, brush at least twice daily for about "
            "two minutes, including last thing at night. A parent or carer "
            "should supervise. Use fluoride toothpaste and a pea-sized amount; "
            "spit after brushing and do not rinse."
        ),
        keywords=("brush", "toothpaste", "fluoride", "rinse", "clean teeth"),
        source=DBOH_GUIDANCE,
        age_groups=("3-6",),
    ),
    KnowledgeEntry(
        entry_id="brush-7-plus",
        text=(
            "For children aged 7 and over, brush at least twice daily for about "
            "two minutes, including last thing at night, with 1,350 to 1,500 ppm "
            "fluoride toothpaste. Spit after brushing and do not rinse."
        ),
        keywords=("brush", "toothpaste", "fluoride", "rinse", "clean teeth"),
        source=DBOH_GUIDANCE,
        age_groups=("7+",),
    ),
    KnowledgeEntry(
        entry_id="healthy-routine",
        text=(
            "Regular brushing with fluoride toothpaste helps prevent tooth "
            "decay. Reduce how often and how much sugary food and drink children "
            "have, and attend dental check-ups as advised by a dentist."
        ),
        keywords=("healthy", "prevent", "decay", "sugar", "routine", "diet"),
        source=NHS_CHILDRENS_TEETH,
    ),
    KnowledgeEntry(
        entry_id="toothache-urgent",
        text=(
            "Contact a dentist or NHS 111 for tooth or mouth pain that is severe, "
            "affects sleep or daily activities, or does not go away, and for "
            "swelling that is getting bigger or not going away."
        ),
        keywords=(
            "toothache", "tooth pain", "mouth pain", "hurts", "uncomfortable",
            "sore", "sensitive", "swelling", "painful", "不舒服", "牙痛", "疼",
        ),
        source=NHS_URGENT_DENTIST,
    ),
    KnowledgeEntry(
        entry_id="wales-access",
        text=(
            "In Wales, people with an urgent dental problem should contact their "
            "local Dental Helpline; the correct service depends on where they live."
        ),
        keywords=("dentist", "urgent", "appointment", "helpline", "wales"),
        source=NHS_111_WALES,
        regions=("Wales",),
    ),
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.casefold()))


def retrieve_knowledge(
    query: str,
    age_group: AgeGroup,
    region: Region,
    limit: int = 3,
) -> list[KnowledgeEntry]:
    query_tokens = _tokens(query)
    ranked: list[tuple[int, KnowledgeEntry]] = []

    for entry in ENTRIES:
        if entry.regions and region not in entry.regions:
            continue
        keyword_score = sum(
            3 if keyword.casefold() in query.casefold() else 0
            for keyword in entry.keywords
        )
        token_score = len(query_tokens & _tokens(" ".join(entry.keywords)))
        context_score = 0
        if entry.age_groups and age_group in entry.age_groups:
            context_score += 4
        elif entry.age_groups and age_group != "Not provided":
            context_score -= 3
        if entry.regions and region in entry.regions:
            context_score += 4

        score = keyword_score + token_score + context_score
        if score > 0:
            ranked.append((score, entry))

    ranked.sort(key=lambda item: (-item[0], item[1].entry_id))
    return [entry for _, entry in ranked[:limit]]


def unique_sources(entries: list[KnowledgeEntry]) -> list[SourceLink]:
    sources: dict[str, SourceLink] = {}
    for entry in entries:
        sources[entry.source.url] = entry.source
    return list(sources.values())
