from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def send_message(message: str) -> dict:
    response = client.post("/api/chat", json={"message": message})

    assert response.status_code == 200

    return response.json()


def test_health_check():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_brushing_question_uses_brushing_pathway():
    data = send_message("How can I help my child brush their teeth?")

    assert data["category"] == "brushing"
    assert data["urgent"] is False
    assert "twice a day" in data["reply"].lower()


def test_toothache_question_uses_toothache_pathway():
    data = send_message("My child has toothache. What should I do?")

    assert data["category"] == "toothache"
    assert data["urgent"] is False
    assert "dentist" in data["reply"].lower()


def test_urgent_dental_question_uses_urgent_pathway():
    data = send_message("When should I seek urgent dental care?")

    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert "nhs 111" in data["reply"].lower()


def test_breathing_difficulty_is_treated_as_an_emergency():
    data = send_message(
        "My child has facial swelling and difficulty breathing"
    )

    assert data["category"] == "urgent"
    assert data["urgent"] is True
    assert "999" in data["reply"]


def test_unrecognised_question_uses_general_pathway():
    data = send_message("What can I do to support healthy teeth?")

    assert data["category"] == "general"
    assert data["urgent"] is False


def test_empty_message_is_rejected():
    response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422