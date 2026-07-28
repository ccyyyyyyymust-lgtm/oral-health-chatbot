from dataclasses import dataclass

from schemas import Category, SourceLink


NHS_URGENT_DENTIST = SourceLink(
    title="NHS - Emergency or urgent dentist appointments",
    url=(
        "https://www.nhs.uk/nhs-services/dentists/"
        "how-to-find-an-nhs-dentist-in-an-emergency/"
    ),
)


@dataclass(frozen=True)
class SafetyDecision:
    reply: str
    category: Category
    urgent: bool
    sources: tuple[SourceLink, ...]


IMMEDIATE_EMERGENCY_TERMS = (
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
    "serious face injury",
    "serious facial injury",
    "serious jaw injury",
    "呼吸困难",
    "无法呼吸",
    "吞咽困难",
    "大量出血",
    "止不住血",
    "面部严重受伤",
    "下颌严重受伤",
)

URGENT_DENTAL_TERMS = (
    "severe tooth pain",
    "severe mouth pain",
    "facial swelling",
    "face swelling",
    "swollen face",
    "knocked out tooth",
    "knocked-out tooth",
    "dental injury",
    "tooth injury",
    "worsening swelling",
    "严重牙痛",
    "严重口腔疼痛",
    "面部肿胀",
    "牙齿脱落",
    "牙齿受伤",
)


def contains_any(text: str, terms: tuple[str, ...] | list[str]) -> bool:
    lowered = text.casefold()
    return any(term.casefold() in lowered for term in terms)


def check_safety(message: str) -> SafetyDecision | None:
    if contains_any(message, IMMEDIATE_EMERGENCY_TERMS):
        return SafetyDecision(
            reply=(
                "This may be a medical emergency. Call 999 or go to A&E now "
                "for heavy mouth bleeding that will not stop, severe swelling "
                "affecting breathing or swallowing, or a serious injury to the "
                "face or jaw. Do not rely on this chatbot in an emergency."
            ),
            category="urgent",
            urgent=True,
            sources=(NHS_URGENT_DENTIST,),
        )

    if contains_any(message, URGENT_DENTAL_TERMS):
        return SafetyDecision(
            reply=(
                "Seek urgent dental advice now from a dentist or NHS 111 for "
                "severe pain, worsening swelling, a knocked-out tooth, or a "
                "dental injury. Call 999 or go to A&E if there is heavy bleeding "
                "that will not stop, serious facial or jaw injury, or swelling "
                "affecting breathing or swallowing."
            ),
            category="urgent",
            urgent=True,
            sources=(NHS_URGENT_DENTIST,),
        )

    return None

