from llm import _conversation_for_model
from schemas import ConversationMessage


def test_qwen3_gets_no_think_without_mutating_user_message():
    original = ConversationMessage(role="user", content="Find a dentist near CW9")

    prepared = _conversation_for_model([original], "Qwen/Qwen3-8B")

    assert prepared[-1]["content"].endswith("\n/no_think")
    assert original.content == "Find a dentist near CW9"


def test_other_models_do_not_get_qwen_control_token():
    message = ConversationMessage(role="user", content="Hello")

    prepared = _conversation_for_model(
        [message],
        "deepseek-ai/DeepSeek-V3-0324",
    )

    assert prepared[-1]["content"] == "Hello"
