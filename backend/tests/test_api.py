import pytest
from fastapi.testclient import TestClient

import main
from main import app
from nhs_services import DentalService
from rate_limit import InMemoryRateLimiter


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_real_llm(monkeypatch):
    # Unit/API tests must never consume the developer's hosted inference credits.
    monkeypatch.setenv("HF_TOKEN", "")


def send_message(
    message: str,
    region: str = "England",
    age_group: str = "Not provided",
) -> dict:
    response = client.post(
        "/api/chat",
        json={"message": message, "region": region, "age_group": age_group},
    )
    assert response.status_code == 200
    return response.json()


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_brushing_question_asks_for_age_group_when_missing():
    data = send_message("How can I help my child brush their teeth?")
    assert data["needs_age_group"] is True
    assert "age group" in data["reply"].lower()


def test_brushing_age_gate_runs_before_configured_llm(monkeypatch):
    async def unexpected_model_call(*args, **kwargs):
        raise AssertionError("The model must not run before age is provided.")

    monkeypatch.setenv("HF_TOKEN", "configured-for-test")
    monkeypatch.setenv("HF_MODEL", "Qwen/Qwen3-8B")
    monkeypatch.setattr(main, "generate_reply", unexpected_model_call)

    data = send_message("How can I help my child brush their teeth?")

    assert data["needs_age_group"] is True
    assert data["response_mode"] == "fallback"


def test_brushing_question_uses_selected_age_group_and_sources():
    data = send_message("How can I help my child brush their teeth?", age_group="3-6")
    assert data["category"] == "brushing"
    assert data["age_group"] == "3-6"
    assert data["sources"]
    assert "twice" in data["reply"].lower()


def test_question_with_age_infers_age_group():
    data = send_message("How should my 8-year-old brush their teeth?")
    assert data["age_group"] == "7+"
    assert data["needs_age_group"] is False


def test_chinese_question_with_age_infers_age_group():
    data = send_message("8岁的小孩应该怎么刷牙？")
    assert data["category"] == "brushing"
    assert data["age_group"] == "7+"


def test_toothache_question_uses_toothache_pathway():
    data = send_message("My child has toothache. What should I do?")
    assert data["category"] == "toothache"
    assert data["urgent"] is False
    assert "dentist" in data["reply"].lower()


def test_natural_language_discomfort_uses_toothache_fallback():
    data = send_message("My child's teeth feel really uncomfortable.")
    assert data["category"] == "toothache"
    assert data["response_mode"] == "fallback"
    assert "dentist" in data["reply"].lower()
    assert data["sources"]


def test_urgent_dental_question_uses_urgent_pathway():
    data = send_message("When should I seek urgent dental care?", region="Wales")
    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert any("111.wales.nhs.uk" in source["url"] for source in data["sources"])


def test_scotland_dental_question_reports_source_gap():
    data = send_message("How do I find an emergency dental appointment?", region="Scotland")
    assert data["category"] == "general"
    assert data["source_gap"] is True
    assert data["sources"] == []


def test_breathing_difficulty_is_treated_as_an_emergency():
    data = send_message("My child has facial swelling and difficulty breathing")
    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert data["response_mode"] == "safety"
    assert "999" in data["reply"]


def test_general_prevention_question_retrieves_reviewed_source():
    data = send_message("What can I do to support healthy teeth?")
    assert data["category"] == "general"
    assert data["sources"]


def test_find_nhs_dentist_question_asks_for_postcode():
    data = send_message("How can I find an NHS dentist near me?", region="England")
    assert data["category"] == "general"
    assert "postcode" in data["reply"].lower()
    assert any("service-search/find-a-dentist" in source["url"] for source in data["sources"])


def test_find_nhs_dentist_uses_service_search_results(monkeypatch):
    async def fake_search(postcode: str, *, limit: int = 5):
        assert postcode == "CW9"
        return [
            DentalService(
                ods_code="ABC01",
                name="Example Dental Practice",
                address="1 Example Street, Northwich",
                postcode="CW9 1AA",
                phone="01632 960000",
            )
        ]

    monkeypatch.setattr(main, "search_england_dentists", fake_search)
    data = send_message("Find a dentist near CW9", region="England")

    assert data["response_mode"] == "fallback"
    assert "Example Dental Practice" in data["reply"]
    assert "accepting NHS patients" in data["reply"]
    assert data["sources"][0]["url"].endswith("/find-a-dentist")


def test_find_nhs_dentist_source_is_not_used_outside_england():
    data = send_message("How can I find an NHS dentist near me?", region="Scotland")
    assert not any(
        source["url"].endswith("/how-to-find-an-nhs-dentist/")
        for source in data["sources"]
    )


def test_conversation_history_request_is_supported():
    response = client.post(
        "/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "My child's tooth feels sore."},
                {"role": "assistant", "content": "How long has it lasted?"},
                {"role": "user", "content": "Since yesterday."},
            ],
            "region": "England",
            "age_group": "3-6",
        },
    )
    assert response.status_code == 200
    assert response.json()["reply"]


def test_messages_must_end_with_user_message():
    response = client.post(
        "/api/chat",
        json={"messages": [{"role": "assistant", "content": "Hello"}]},
    )
    assert response.status_code == 422


def test_empty_message_is_rejected():
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_rate_limiter_rejects_requests_over_limit(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "2")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    limiter = InMemoryRateLimiter()

    assert limiter.allow("test-client") is True
    assert limiter.allow("test-client") is True
    assert limiter.allow("test-client") is False
