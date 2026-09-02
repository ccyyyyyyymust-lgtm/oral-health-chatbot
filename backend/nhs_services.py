import os
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

import httpx


SERVICE_SEARCH_BASE_URL = (
    "https://int.api.service.nhs.uk/service-search-api/"
)

DENTIST_SEARCH_TERMS = (
    "find a dentist",
    "find dentist",
    "dentist near",
    "nearby dentist",
    "local dentist",
    "register with a dentist",
    "牙医",
    "牙科诊所",
)

UK_POSTCODE_PATTERN = re.compile(
    r"\b("
    r"(?:GIR\s?0AA)|"
    r"(?:(?:[A-PR-UWYZ][0-9][0-9A-HJKSTUW]?)|"
    r"(?:[A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRV-Y]?))"
    r"\s?[0-9][ABD-HJLNP-UW-Z]{2}"
    r"|"
    r"(?:[A-PR-UWYZ][0-9][A-HJKSTUW]?|"
            r"[A-PR-UWYZ][A-HK-Y][0-9][0-9ABEHMNPRV-Y]?)"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DentalService:
    ods_code: str
    name: str
    address: str
    postcode: str
    phone: str = ""

    @property
    def map_url(self) -> str:
        query = ", ".join(
            part for part in (self.name, self.address, self.postcode) if part
        )
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"


class ServiceSearchError(RuntimeError):
    pass


def is_dentist_search_query(message: str) -> bool:
    lowered = message.casefold()
    return any(term in lowered for term in DENTIST_SEARCH_TERMS)


def extract_uk_postcode(message: str) -> str | None:
    match = UK_POSTCODE_PATTERN.search(message.upper())
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(1)).upper()


def format_uk_postcode(postcode: str) -> str:
    compact = re.sub(r"\s+", "", postcode.upper())
    if re.fullmatch(r".+[0-9][A-Z]{2}", compact):
        return f"{compact[:-3]} {compact[-3:]}"
    return compact


def is_wales_postcode(postcode: str) -> bool:
    """Identify postcode areas wholly or predominantly associated with Wales."""
    compact = re.sub(r"\s+", "", postcode.upper())
    return compact.startswith(("CF", "LD", "LL", "NP", "SA"))


def _first_phone(contacts: object) -> str:
    if not isinstance(contacts, list):
        return ""
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        contact_type = str(
            contact.get("ContactType")
            or contact.get("type")
            or contact.get("name")
            or ""
        ).casefold()
        value = str(
            contact.get("ContactValue")
            or contact.get("value")
            or contact.get("telephone")
            or ""
        ).strip()
        if value and (
            not contact_type
            or "phone" in contact_type
            or "telephone" in contact_type
        ):
            return value
    return ""


def _normalise_service(item: dict[str, object]) -> DentalService | None:
    name = str(item.get("OrganisationName") or "").strip()
    if not name:
        return None
    postcode = str(item.get("Postcode") or "").strip()
    address_parts = [
        str(item.get(field) or "").strip()
        for field in ("Address1", "Address2", "Address3", "City", "County")
    ]
    address = ", ".join(
        part for index, part in enumerate(address_parts)
        if part and part not in address_parts[:index]
    )
    return DentalService(
        ods_code=str(item.get("ODSCode") or "").strip(),
        name=name,
        address=address,
        postcode=postcode,
        phone=_first_phone(item.get("Contacts")),
    )


async def search_england_dentists(
    postcode: str,
    *,
    limit: int = 5,
) -> list[DentalService]:
    api_key = os.getenv("NHS_API_KEY", "").strip()
    if not api_key:
        raise ServiceSearchError("NHS_API_KEY is not configured.")

    safe_postcode = re.sub(r"[^A-Z0-9]", "", postcode.upper())
    if not safe_postcode:
        return []

    search_postcodes = [safe_postcode]
    # A full postcode describes the parent's address, not necessarily a dental
    # practice's address. If no exact-postcode listing exists, retry using the
    # outward code (for example CW91AA -> CW9) to search the local district.
    if re.fullmatch(r".+[0-9][A-Z]{2}", safe_postcode):
        outward_code = safe_postcode[:-3]
        if outward_code and outward_code != safe_postcode:
            search_postcodes.append(outward_code)
    base_url = os.getenv(
        "NHS_SERVICE_SEARCH_BASE_URL",
        SERVICE_SEARCH_BASE_URL,
    ).strip()
    timeout = float(os.getenv("NHS_API_TIMEOUT_SECONDS", "10"))

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            for search_postcode in search_postcodes:
                params = {
                    "api-version": "3",
                    "$filter": (
                        f"search.ismatch('{search_postcode}', 'Postcode') "
                        "and OrganisationTypeId eq 'DEN'"
                    ),
                    "$top": str(max(1, min(limit, 10))),
                    "$select": (
                        "ODSCode,OrganisationName,Address1,Address2,Address3,"
                        "City,County,Postcode,Contacts,OrganisationTypeId"
                    ),
                }
                response = await client.get(
                    base_url,
                    params=params,
                    headers={"apikey": api_key},
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("value", []) if isinstance(data, dict) else []
                services = [
                    service
                    for item in items
                    if isinstance(item, dict)
                    and (service := _normalise_service(item)) is not None
                ]
                if services:
                    return services[:limit]
    except (httpx.HTTPError, ValueError) as exc:
        raise ServiceSearchError("NHS Service Search is unavailable.") from exc
    return []


def format_services_for_model(services: list[DentalService]) -> str:
    lines = [
        (
            "The following records came from the NHS Directory of Healthcare "
            "Services. Treat them only as directory listings. Do not claim that "
            "a practice is accepting NHS patients or has appointments available. "
            "Tell the user to contact the practice to confirm."
        )
    ]
    for index, service in enumerate(services, start=1):
        details = [
            f"name={service.name}",
            f"postcode={service.postcode}",
        ]
        if service.address:
            details.append(f"address={service.address}")
        if service.phone:
            details.append(f"phone={service.phone}")
        if service.ods_code:
            details.append(f"ODS code={service.ods_code}")
        lines.append(f"{index}. " + "; ".join(details))
    return "\n".join(lines)


def format_services_fallback(
    postcode: str,
    services: list[DentalService],
) -> str:
    lines = [
        f"I found these NHS directory listings for postcode {postcode}:"
    ]
    for service in services:
        location = ", ".join(
            part for part in (service.address, service.postcode) if part
        )
        contact = f" Tel: {service.phone}." if service.phone else ""
        lines.append(
            f"\n- {service.name}"
            + (f" — {location}." if location else ".")
            + contact
        )
    lines.append(
        "Directory listing does not confirm that a practice is accepting NHS "
        "patients or has appointments available. Contact the practice to check."
    )
    return "\n".join(lines)
