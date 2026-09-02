import pytest
from fastapi.testclient import TestClient

import main
from main import app
from nhs_services import DentalService, ServiceSearchError
from rate_limit import InMemoryRateLimiter


client = TestClient(app)


@pytest.fixture(autouse=True)
def disable_real_llm(monkeypatch):
    # Unit/API tests must never consume the developer's hosted inference credits.
    monkeypatch.setenv("HF_TOKEN", "")
    main.rate_limiter._requests.clear()


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


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://[::1]:5176",
    ],
)
def test_local_vite_ports_are_allowed_by_cors(origin):
    response = client.options(
        "/api/chat",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


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


def test_wales_postcode_offers_copy_instead_of_england_directory(monkeypatch):
    async def unexpected_search(*args, **kwargs):
        raise AssertionError("A Wales postcode must not use the England directory.")

    monkeypatch.setattr(main, "search_england_dentists", unexpected_search)
    data = send_message("Find a dentist near CF10 3UP", region="England")

    assert data["region"] == "Wales"
    assert data["copyable_postcode"] == "CF10 3UP"
    assert data["dental_services"] == []
    assert data["source_gap"] is True
    assert "do not currently have" in data["reply"].lower()
    assert any("111.wales.nhs.uk" in source["url"] for source in data["sources"])


def test_wales_postcode_only_followup_offers_copy(monkeypatch):
    async def unexpected_search(*args, **kwargs):
        raise AssertionError("A Wales postcode must not use the England directory.")

    monkeypatch.setattr(main, "search_england_dentists", unexpected_search)
    response = client.post(
        "/api/chat",
        json={
            "messages": [
                {"role": "user", "content": "Find a dentist near me"},
                {"role": "assistant", "content": "Please provide your postcode."},
                {"role": "user", "content": "CF10 3UP"},
            ],
            "region": "Not sure",
        },
    )

    assert response.status_code == 200
    assert response.json()["copyable_postcode"] == "CF10 3UP"


def test_england_directory_failure_preserves_postcode_actions(monkeypatch):
    async def failed_search(*args, **kwargs):
        raise ServiceSearchError("Temporary upstream failure")

    monkeypatch.setattr(main, "search_england_dentists", failed_search)
    data = send_message("Find a dentist near CW9 1AA", region="England")

    assert data["source_gap"] is True
    assert data["copyable_postcode"] == "CW9 1AA"
    assert data["dental_services"] == []
    assert "open a map search" in data["reply"].lower()


def test_empty_england_directory_result_preserves_postcode_actions(monkeypatch):
    async def empty_search(*args, **kwargs):
        return []

    monkeypatch.setattr(main, "search_england_dentists", empty_search)
    data = send_message("Find a dentist near CW9 1AA", region="England")

    assert data["source_gap"] is True
    assert data["copyable_postcode"] == "CW9 1AA"
    assert "open a map search" in data["reply"].lower()


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
    assert data["dental_services"][0]["postcode"] == "CW9 1AA"
    assert data["dental_services"][0]["map_url"].startswith("https://www.google.com/maps/")


def test_combined_dentist_search_and_toothache_answers_both_needs(monkeypatch):
    async def fake_search(postcode: str, *, limit: int = 5):
        assert postcode == "CW9"
        return [
            DentalService(
                ods_code="ABC01",
                name="Northwich Child Dental Practice",
                address="1 Example Street, Northwich",
                postcode="CW9 1AA",
                phone="01632 960000",
            )
        ]

    monkeypatch.setattr(main, "search_england_dentists", fake_search)
    data = send_message(
        "Where is a dentist near CW9 and what should I do about my child's toothache?",
        region="England",
    )

    assert data["category"] == "toothache"
    assert data["needs_age_group"] is True
    assert "Northwich Child Dental Practice" in data["reply"]
    assert "toothache" in data["reply"].lower()
    assert "NHS 111" in data["reply"]
    assert "age group" in data["reply"].lower()
    source_urls = {source["url"] for source in data["sources"]}
    assert any(url.endswith("/find-a-dentist") for url in source_urls)
    assert any("in-an-emergency" in url for url in source_urls)


def test_combined_dentist_search_with_age_does_not_repeat_age_request(monkeypatch):
    async def fake_search(postcode: str, *, limit: int = 5):
        return [
            DentalService(
                ods_code="ABC01",
                name="Northwich Child Dental Practice",
                address="1 Example Street, Northwich",
                postcode="CW9 1AA",
            )
        ]

    monkeypatch.setattr(main, "search_england_dentists", fake_search)
    data = send_message(
        "Find a dentist near CW9. My child has toothache.",
        region="England",
        age_group="3-6",
    )

    assert data["category"] == "toothache"
    assert data["needs_age_group"] is False
    assert "Northwich Child Dental Practice" in data["reply"]
    assert "Please choose" not in data["reply"]


def test_postcode_search_infers_england_when_location_is_not_sure(monkeypatch):
    async def fake_search(postcode: str, *, limit: int = 5):
        assert postcode == "CW91AA"
        return [
            DentalService(
                ods_code="ABC01",
                name="Northwich Dental Practice",
                address="1 Example Street, Northwich",
                postcode="CW9 1AA",
                phone="01632 960000",
            )
        ]

    monkeypatch.setattr(main, "search_england_dentists", fake_search)
    data = send_message(
        "my child have a teethache, we live near by cw9 1aa. How can we find a dentist",
        region="Not sure",
        age_group="7+",
    )

    assert data["region"] == "England"
    assert data["category"] == "toothache"
    assert "Northwich Dental Practice" in data["reply"]
    assert "01632 960000" in data["reply"]
    assert "NHS 111" in data["reply"]
    assert any(source["url"].endswith("/find-a-dentist") for source in data["sources"])


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
