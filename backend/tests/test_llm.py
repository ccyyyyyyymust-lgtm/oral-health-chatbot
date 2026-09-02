from llm import _assistant_question_count, _conversation_for_model, _limit_questions
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


def test_counts_assistant_questions_across_conversation():
    messages = [
        ConversationMessage(role="assistant", content="Did you find the tooth?"),
        ConversationMessage(role="user", content="Yes."),
        ConversationMessage(role="assistant", content="Is it a baby tooth? How old is your child?"),
    ]

    assert _assistant_question_count(messages) == 3


def test_removes_questions_after_conversation_limit_but_keeps_advice():
    reply = "Keep the tooth in milk. Go to a dentist now. Did you replant it?"

    assert _limit_questions(reply, 0) == "Keep the tooth in milk. Go to a dentist now."


def test_allows_only_one_question_per_reply():
    reply = "Go to a dentist now. Did you find the tooth? Is it permanent?"

    assert _limit_questions(reply, 1) == "Go to a dentist now. Did you find the tooth?"


def test_chinese_question_limit_is_enforced():
    reply = "请立即联系牙医。孩子多大？这是恒牙吗？"

    assert _limit_questions(reply, 1) == "请立即联系牙医。孩子多大？"
