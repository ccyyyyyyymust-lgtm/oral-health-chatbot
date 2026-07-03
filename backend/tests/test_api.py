from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def send_message(
    message: str,
    region: str = "England",
    age_group: str = "Not provided",
) -> dict:
    response = client.post(
        "/api/chat",
        json={
            "message": message,
            "region": region,
            "age_group": age_group,
        },
    )

    assert response.status_code == 200

    return response.json()


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_brushing_question_asks_for_age_group_when_missing():
    data = send_message("How can I help my child brush their teeth?")

    assert data["category"] == "general"
    assert data["urgent"] is False
    assert data["needs_age_group"] is True
    assert "age group" in data["reply"].lower()


def test_brushing_question_uses_selected_age_group():
    data = send_message(
        "How can I help my child brush their teeth?",
        age_group="3-6",
    )

    assert data["category"] == "brushing"
    assert data["urgent"] is False
    assert data["age_group"] == "3-6"
    assert data["sources"]
    assert data["sources"][0]["url"].startswith("https://www.nhs.uk/")
    assert "twice a day" in data["reply"].lower()


def test_question_with_age_infers_age_group():
    data = send_message("How should my 8-year-old brush their teeth?")

    assert data["category"] == "brushing"
    assert data["urgent"] is False
    assert data["age_group"] == "7+"
    assert data["needs_age_group"] is False


def test_not_sure_location_still_allows_general_brushing_sources():
    data = send_message(
        "How should my 8-year-old brush their teeth?",
        region="Not sure",
    )

    assert data["category"] == "brushing"
    assert data["source_gap"] is False
    assert data["sources"]
    assert any("Children's teeth" in source["title"] for source in data["sources"])


def test_chinese_question_with_age_infers_age_group():
    data = send_message("八岁的小孩应该怎么刷牙？")

    assert data["category"] == "brushing"
    assert data["urgent"] is False
    assert data["age_group"] == "7+"
    assert data["needs_age_group"] is False


def test_toothache_question_uses_toothache_pathway():
    data = send_message("My child has toothache. What should I do?")

    assert data["category"] == "toothache"
    assert data["urgent"] is False
    assert "dentist" in data["reply"].lower()


def test_urgent_dental_question_uses_urgent_pathway():
    data = send_message(
        "When should I seek urgent dental care?",
        region="Wales",
    )

    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert data["region"] == "Wales"
    assert any("111.wales.nhs.uk" in source["url"] for source in data["sources"])
    assert "nhs 111" in data["reply"].lower()


def test_scotland_dental_question_reports_source_gap():
    data = send_message(
        "How do I find an emergency dental appointment?",
        region="Scotland",
    )

    assert data["category"] == "general"
    assert data["urgent"] is False
    assert data["source_gap"] is True
    assert data["sources"] == []
    assert "official sources" in data["reply"].lower()


def test_breathing_difficulty_is_treated_as_an_emergency():
    data = send_message(
        "My child has facial swelling and difficulty breathing"
    )

    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert data["source_gap"] is False
    assert data["sources"]
    assert "999" in data["reply"]


def test_unrecognised_question_uses_general_pathway():
    data = send_message("What can I do to support healthy teeth?")

    assert data["category"] == "general"
    assert data["urgent"] is False


def test_empty_message_is_rejected():
    response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422
