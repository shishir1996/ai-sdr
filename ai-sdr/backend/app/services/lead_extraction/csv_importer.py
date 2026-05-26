import csv
import io
from typing import Any, Union


def parse_csv(content: Union[str, bytes]) -> list[dict[str, Any]]:
    if isinstance(content, bytes):
        content = content.decode("utf-8")

    reader = csv.DictReader(io.StringIO(content))
    leads = []
    for row in reader:
        lead = {
            "first_name": row.get("first_name", row.get("FirstName", row.get("first name", ""))),
            "last_name": row.get("last_name", row.get("LastName", row.get("last name", ""))),
            "email": row.get("email", row.get("Email", "")),
            "phone": row.get("phone", row.get("Phone", "")),
            "title": row.get("title", row.get("Title", row.get("job_title", ""))),
            "company": row.get("company", row.get("Company", "")),
            "linkedin_url": row.get("linkedin_url", row.get("LinkedIn", row.get("linkedin", ""))),
            "website": row.get("website", row.get("Website", "")),
            "industry": row.get("industry", row.get("Industry", "")),
            "location": row.get("location", row.get("Location", "")),
            "source": "csv",
        }
        lead = {k: v for k, v in lead.items() if v}
        if lead.get("email") or lead.get("first_name"):
            leads.append(lead)
    return leads


def validate_lead_row(row: dict) -> list[str]:
    errors = []
    if not row.get("email") and not row.get("first_name"):
        errors.append("Row must have at least an email or first_name")
    return errors
