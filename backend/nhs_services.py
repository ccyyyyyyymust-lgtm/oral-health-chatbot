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


# Offline snapshot of directory records published by NHS 111 Wales.  Keeping a
# small, geographically spread snapshot here means Wales searches still return
# useful practice cards when no live directory API is available.  The records
# are listings only; callers must not imply that a practice is accepting NHS
# patients or currently has appointments.
WALES_DENTAL_SERVICES: tuple[DentalService, ...] = (
    DentalService("", "Charles Street Dental Surgery", "54 Charles Street, City Centre, Cardiff", "CF10 2GF", "02920 230185"),
    DentalService("", "Park Place Dental Practice", "3-4 Park Place, Cardiff", "CF10 3DP", "02920 373831"),
    DentalService("", "Hywel Samuel & Associates - Golate Dental Practice", "Golate Court, Golate Street, Cardiff", "CF10 1EU", "02920 371393"),
    DentalService("", "Gentle Dental Surgery", "7 Victoria Square, Aberdare", "CF44 7LA", "01685 882800"),
    DentalService("", "Park Crescent Dental Practice", "29 Park Crescent, Barry", "CF62 6HE", "01446 733595"),
    DentalService("", "Little Owl Dental", "The Old Town Hall, Temple Street, Llandrindod Wells", "LD1 5DL", "01597 822404"),
    DentalService("", "Brecon Dental Care", "12 Castle Street, Brecon", "LD3 9BU", "01874 623357"),
    DentalService("", "Brecon Road Dental Surgery", "34 Brecon Road, Abergavenny", "NP7 5UG", "01873 856111"),
    DentalService("", "The Gateway Dental Practice", "44 Cross Street, Abergavenny", "NP7 5ER", "01873 737737"),
    DentalService("", "Malpas Road Dental Surgery", "48 Malpas Road, Newport", "NP20 5PB", "01633 857351"),
    DentalService("", "Malpas Dental Practice", "442 Malpas Road, Newport", "NP20 6WE", "01633 853866"),
    DentalService("", "Bettws Dental Surgery", "1 Bettws Shopping Centre, Newport", "NP20 7TN", "01633 821388"),
    DentalService("", "Belgrave Dental Centre", "91 Walter Road, Swansea", "SA1 4QF", "01792 473881"),
    DentalService("", "Brynteg Dental Practice", "26 Dilwyn Road, Sketty, Swansea", "SA2 9AE", "01792 204995"),
    DentalService("", "Chapel Street Dental Practice", "15 Chapel Street, Mumbles, Swansea", "SA3 4NH", "01792 368388"),
    DentalService("", "Bridge Street Dental Practice", "21-23 Bridge Street, Haverfordwest", "SA61 2AL", "01437 766958"),
    DentalService("", "Dew Street Dental Practice", "31 Dew Street, Haverfordwest", "SA61 1ST", "01437 762709"),
    DentalService("", "My Dentist, Quay Street", "Quay Street, Haverfordwest", "SA61 1BB", "01437 769816"),
    DentalService("", "Castlewood Dental Care", "Haulfryn, Lenton Pool, Denbigh", "LL16 3LH", "01745 817237"),
    DentalService("", "The Hollies Dental Practice", "65 Vale Street, Denbigh", "LL16 3AP", "01745 813198"),
    DentalService("", "Corwen Health Centre", "Green Lane, Corwen", "LL21 0DN", "03000 859377"),
    DentalService("", "Elwy Dental Practice", "1 Chapel Street, Abergele", "LL22 7AW", "01745 826885"),
    DentalService("", "Llanrwst Dental Practice", "24a Watling Street, Llanrwst", "LL26 0LS", "01492 641000"),
    DentalService("", "Clifton Dental Practice", "67 Clifton Terrace, Newtown", "SY16 1BG", "01686 626252"),
    DentalService("", "My Dentist, New Road", "New Road, Newtown", "SY16 1BD", "01686 248031"),
    DentalService("", "My Dentist, Troseley House", "67 Clifton Terrace, Newtown", "SY16 1BG", "01686 624344"),
)


def _postcode_area_and_district(postcode: str) -> tuple[str, int]:
    compact = re.sub(r"\s+", "", postcode.upper())
    match = re.match(r"([A-Z]{1,2})(\d{1,2})", compact)
    return (match.group(1), int(match.group(2))) if match else ("", 999)


def search_wales_dentists_offline(
    postcode: str,
    *,
    limit: int = 5,
) -> list[DentalService]:
    """Return the nearest available Wales snapshot records without networking.

    The outward postcode district is used as a deterministic geographic proxy:
    same-area records rank first, then neighbouring Wales records.  It is not a
    distance calculation, so the UI describes these as offline directory results.
    """
    area, district = _postcode_area_and_district(postcode)

    def rank(service: DentalService) -> tuple[int, int, str]:
        service_area, service_district = _postcode_area_and_district(service.postcode)
        return (
            0 if service_area == area else 1,
            abs(service_district - district) if service_area == area else 999,
            service.name,
        )

    return sorted(WALES_DENTAL_SERVICES, key=rank)[:max(3, min(limit, 5))]


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
