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
IADT_FRACTURES_LUXATIONS = SourceLink(
    title="IADT 2020 - Fractures and luxations",
    url="https://doi.org/10.1111/edt.12578",
)
IADT_AVULSION = SourceLink(
    title="IADT 2020 - Avulsion of permanent teeth",
    url="https://doi.org/10.1111/edt.12573",
)
IADT_PRIMARY_DENTITION = SourceLink(
    title="IADT 2020 - Injuries in the primary dentition",
    url="https://doi.org/10.1111/edt.12576",
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
        entry_id="trauma-knocked-out-permanent-tooth",
        text=(
            "A knocked-out permanent tooth needs immediate dental care. Hold it by the crown, "
            "not the root. If it is dirty, rinse it gently. Replant it immediately if possible. "
            "If that is not possible, keep it moist in milk or another suitable storage medium "
            "and go to a dentist at once. Do not replant a baby tooth."
        ),
        keywords=(
            "knocked out tooth", "knocked-out tooth", "avulsion", "avulsed", "tooth fell out",
            "dental injury", "dental trauma", "撞掉", "牙齿脱落", "牙外伤",
        ),
        source=IADT_AVULSION,
    ),
    KnowledgeEntry(
        entry_id="trauma-primary-tooth",
        text=(
            "Do not put a knocked-out baby tooth back into the socket. Arrange prompt dental "
            "assessment. The dentist will check the injury and whether the developing permanent "
            "tooth may be affected."
        ),
        keywords=(
            "baby tooth knocked out", "primary tooth", "deciduous tooth", "milk tooth",
            "baby tooth injury", "乳牙", "乳牙外伤",
        ),
        source=IADT_PRIMARY_DENTITION,
        age_groups=("0-3", "3-6"),
    ),
    KnowledgeEntry(
        entry_id="trauma-fracture-luxation",
        text=(
            "A broken, displaced, or loose tooth after an injury should be assessed promptly by "
            "a dentist. Treatment and follow-up depend on the tooth, the injury, root development, "
            "and whether supporting tissues are involved."
        ),
        keywords=(
            "broken tooth", "chipped tooth", "cracked tooth", "loose tooth", "pushed tooth",
            "displaced tooth", "luxation", "fracture", "dental trauma", "牙齿断了", "牙外伤",
        ),
        source=IADT_FRACTURES_LUXATIONS,
    ),
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
            "toothache", "teethache", "teeth ache", "tooth pain", "teeth pain",
            "mouth pain", "hurts", "uncomfortable",
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
