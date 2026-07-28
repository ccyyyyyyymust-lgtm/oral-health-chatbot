from nhs_services import (
    DentalService,
    extract_uk_postcode,
    format_services_for_model,
    is_dentist_search_query,
)


def test_extracts_full_or_outward_postcode():
    assert extract_uk_postcode("Find a dentist near CW9 1AA") == "CW91AA"
    assert extract_uk_postcode("Find a dentist near CW9") == "CW9"


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
