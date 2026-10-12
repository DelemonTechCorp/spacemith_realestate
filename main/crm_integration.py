import logging
import requests

from django.conf import settings

logger = logging.getLogger(__name__)

CRM_URL = (
    "https://x-opperp.com/api/v1/integrations/"
    "webhooks/website-lead/"
)
SITE_URL = getattr(settings, "SITE_URL", "https://spacesmith.ae").rstrip("/")


def _build_message(enquiry):
    """
    Works for GeneralEnquiry (contact, popup, blog) AND PropertyEnquiry.
    Fields that a model doesn't have are simply skipped.
    """
    parts = []

    if getattr(enquiry, "source", None):
        parts.append(f"Source: {enquiry.source}")

    subject = getattr(enquiry, "subject", "")
    if subject:
        parts.append(f"Subject: {subject}")

    # Property enquiries — add the property name, area and link
    if getattr(enquiry, "property_id", None):
        prop = enquiry.property
        location = ", ".join(
            x for x in [
                prop.district.name if prop.district_id else "",
                prop.city.name if prop.city_id else "",
            ] if x
        )
        parts.append(f"Property: {prop.title}" + (f" — {location}" if location else ""))
        parts.append(f"{SITE_URL}/properties/{prop.slug}/")
    
    elif getattr(enquiry, "page_title", ""):
        parts.append(f"Project: {enquiry.page_title}")

    if getattr(enquiry, "page_url", ""):
        parts.append(f"Page: {enquiry.page_url}")
    

    whatsapp = getattr(enquiry, "whatsapp", "")
    if whatsapp and whatsapp != enquiry.phone:
        parts.append(f"WhatsApp: {whatsapp}")

    if enquiry.message:
        parts.append(enquiry.message)

    return "\n".join(parts)


def send_lead_to_crm(enquiry):
    """
    Send a saved enquiry to X-Opp CRM.
    Returns True on a successful HTTP response.
    """
    if not settings.XOPP_CRM_ENABLED:
        logger.info("CRM integration is disabled.")
        return False

    token = settings.XOPP_CRM_API_TOKEN
    if not token:
        logger.error("X-Opp CRM token is missing.")
        return False

    name_parts = (enquiry.name or "").strip().split(maxsplit=1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    payload = {
        "api_token": token,
        "first_name": first_name,
        "last_name": last_name,
        "email": enquiry.email,
        "phone": enquiry.phone,
        "message": _build_message(enquiry),
    }

    label = type(enquiry).__name__   # "GeneralEnquiry" or "PropertyEnquiry"

    try:
        response = requests.post(CRM_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("CRM API accepted %s ID %s", label, enquiry.pk)
        return True

    except requests.HTTPError as exc:
        logger.warning(
            "CRM rejected %s ID %s: %s %s",
            label, enquiry.pk,
            exc.response.status_code, exc.response.text[:500],
        )
        return False

    except requests.RequestException as exc:
        logger.warning("CRM request failed for %s ID %s: %r", label, enquiry.pk, exc)
        return False