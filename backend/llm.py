import asyncio
import logging
import os

from knowledge import KnowledgeEntry
from schemas import AgeGroup, ConversationMessage, Region


SYSTEM_PROMPT = """You are a children's oral-health information assistant for parents in the UK.
Give the useful answer immediately. Do not make the parent answer questions before giving safe,
actionable advice. Use short, plain sentences and everyday words. Keep most answers under 120
words. Do not repeat advice already given earlier in the conversation. If listing two or more
items, put each item on its own line with a hyphen; never run list items together in one paragraph.
Only ask a follow-up question when its answer could materially change the next advice. Ask no more
than one concise question in a reply and no more than three assistant questions in the entire
conversation. When the question allowance is exhausted, give the best safe answer and stop asking.
Give general information, not a diagnosis. Use only the supplied reviewed evidence for clinical
claims. Do not invent sources, medicine doses, availability, links, or facts. Tell users that the
service does not replace a dentist. If evidence is insufficient, say so. The application has
already handled explicit emergency wording. Reply in the language used by the parent where
practical."""

logger = logging.getLogger(__name__)

MAX_ASSISTANT_QUESTIONS = 3


def _assistant_question_count(messages: list[ConversationMessage]) -> int:
    return min(
        MAX_ASSISTANT_QUESTIONS,
        sum(
            item.content.count("?") + item.content.count("？")
            for item in messages
            if item.role == "assistant"
        ),
    )


def _limit_questions(text: str, allowance: int) -> str:
    """Keep direct advice while enforcing the remaining question allowance."""
    kept: list[str] = []
    segment: list[str] = []
    questions_kept = 0

    for character in text:
        segment.append(character)
        if character not in ".!?。！？\n":
            continue
        sentence = "".join(segment)
        segment = []
        is_question = character in "?？"
        if is_question and questions_kept >= allowance:
            continue
        if is_question:
            questions_kept += 1
        kept.append(sentence)

    remainder = "".join(segment)
    if remainder.strip():
        kept.append(remainder)
    return "".join(kept).strip()


def llm_is_configured() -> bool:
    return bool(os.getenv("HF_TOKEN") and os.getenv("HF_MODEL"))


def _conversation_for_model(
    messages: list[ConversationMessage],
    model: str,
) -> list[dict[str, str]]:
    conversation = [
        {"role": item.role, "content": item.content}
        for item in messages[-10:]
    ]
    if model.startswith("Qwen/Qwen3"):
        for item in reversed(conversation):
            if item["role"] == "user":
                item["content"] += "\n/no_think"
                break
    return conversation


def _completion_sync(
    messages: list[ConversationMessage],
    evidence: list[KnowledgeEntry],
    region: Region,
    age_group: AgeGroup,
    additional_evidence: str | None,
) -> str:
    from huggingface_hub import InferenceClient

    evidence_text = "\n".join(
        f"[{item.entry_id}] {item.text} Source: {item.source.title}"
        for item in evidence
    ) or "No directly relevant reviewed evidence was retrieved."
    extra_context = (
        f"\nAdditional trusted tool data:\n{additional_evidence}"
        if additional_evidence
        else ""
    )
    context = (
        f"Parent context: region={region}; child age group={age_group}.\n"
        f"Assistant questions already asked in this conversation: "
        f"{_assistant_question_count(messages)} of {MAX_ASSISTANT_QUESTIONS}.\n"
        f"Reviewed evidence:\n{evidence_text}"
        f"{extra_context}"
    )
    client = InferenceClient(
        provider=os.getenv("HF_PROVIDER", "auto"),
        api_key=os.environ["HF_TOKEN"],
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "12")),
    )
    conversation_messages = _conversation_for_model(
        messages,
        os.environ["HF_MODEL"],
    )

    chat_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context},
        *conversation_messages,
    ]
    result = client.chat_completion(
        model=os.environ["HF_MODEL"],
        messages=chat_messages,
        max_tokens=240,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    )
    content = result.choices[0].message.content
    if not content:
        raise RuntimeError("The configured model returned an empty response.")
    remaining_questions = max(
        0,
        MAX_ASSISTANT_QUESTIONS - _assistant_question_count(messages),
    )
    return _limit_questions(content.strip(), min(1, remaining_questions))


async def generate_reply(
    messages: list[ConversationMessage],
    evidence: list[KnowledgeEntry],
    region: Region,
    age_group: AgeGroup,
    additional_evidence: str | None = None,
) -> str | None:
    if not llm_is_configured():
        return None

    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                _completion_sync,
                messages,
                evidence,
                region,
                age_group,
                additional_evidence,
            ),
            timeout=timeout + 1,
        )
    except Exception as exc:
        # A model/provider failure must not make the safety-first service unusable.
        logger.warning("Hugging Face completion failed; using fallback: %s", exc)
        return None
