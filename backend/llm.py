import asyncio
import logging
import os

from knowledge import KnowledgeEntry
from schemas import AgeGroup, ConversationMessage, Region


SYSTEM_PROMPT = """You are a children's oral-health information assistant for parents in the UK.
Give clear general information, not a diagnosis. Ask one concise follow-up question when important
details are missing. Use only the supplied reviewed evidence for clinical claims. Do not invent
sources, medicine doses, or facts. Tell users that the service does not replace a dentist. If the
evidence is insufficient, say so. The application has already handled explicit emergency wording.
Reply in the language used by the parent where practical."""

logger = logging.getLogger(__name__)


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
        max_tokens=400,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
    )
    content = result.choices[0].message.content
    if not content:
        raise RuntimeError("The configured model returned an empty response.")
    return content.strip()


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
