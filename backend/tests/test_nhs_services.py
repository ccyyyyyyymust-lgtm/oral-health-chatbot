from nhs_services import (
    DentalService,
    extract_uk_postcode,
    format_uk_postcode,
    format_services_for_model,
    is_dentist_search_query,
    is_wales_postcode,
)
import asyncio
import httpx


def test_extracts_full_or_outward_postcode():
    assert extract_uk_postcode("Find a dentist near CW9 1AA") == "CW91AA"
    assert extract_uk_postcode("Find a dentist near CW9") == "CW9"


def test_formats_and_identifies_wales_postcodes():
    assert format_uk_postcode("CF103UP") == "CF10 3UP"
    assert is_wales_postcode("CF10 3UP") is True
    assert is_wales_postcode("LL63 8AA") is True
    assert is_wales_postcode("CW9 1AA") is False


def test_does_not_treat_ordinary_words_as_postcodes():
    assert extract_uk_postcode("Where is a dentist near me?") is None
    assert extract_uk_postcode("This child has toothache") is None


def test_detects_dentist_search_intent():
    assert is_dentist_search_query("Find a dentist near CW9")
    assert not is_dentist_search_query("My child has toothache")


def test_model_context_warns_against_availability_claims():
    context = format_services_for_model(
        [
            DentalService(
                ods_code="ABC01",
                name="Example Dental Practice",
                address="1 Example Street",
                postcode="CW9 1AA",
            )
        ]
    )

    assert "Do not claim" in context
    assert "accepting NHS patients" in context
    assert "Example Dental Practice" in context


def test_map_url_uses_practice_address_and_postcode():
    service = DentalService(
        ods_code="ABC01",
        name="Example Dental Practice",
        address="1 Example Street",
        postcode="CW9 1AA",
    )

    assert service.map_url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Example+Dental+Practice" in service.map_url
    assert "CW9+1AA" in service.map_url


def test_full_postcode_falls_back_to_outward_district(monkeypatch):
    requested_filters: list[str] = []

    async def fake_get(self, url, *, params, headers):
        requested_filters.append(params["$filter"])
        if "CW91AA" in params["$filter"]:
            return httpx.Response(200, json={"value": []}, request=httpx.Request("GET", url))
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "ODSCode": "ABC01",
                        "OrganisationName": "Northwich Dental Practice",
                        "Postcode": "CW9 5EA",
                        "OrganisationTypeId": "DEN",
                    }
                ]
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setenv("NHS_API_KEY", "test-key")
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    from nhs_services import search_england_dentists

    services = asyncio.run(search_england_dentists("CW91AA"))

    assert len(requested_filters) == 2
    assert "CW91AA" in requested_filters[0]
    assert "CW9" in requested_filters[1]
    assert services[0].name == "Northwich Dental Practice"
