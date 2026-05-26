import csv
import io
from typing import Any


COLUMN_MAP = {
    "first_name": ["first_name", "firstname", "first name", "firstName", "given name", "given_name"],
    "last_name": ["last_name", "lastname", "last name", "lastName", "surname", "family name", "family_name"],
    "email": ["email", "e-mail", "email address", "email_address", "emailaddress"],
    "phone": ["phone", "phone number", "phone_number", "telephone", "mobile", "contact", "phone_no"],
    "title": ["title", "job title", "job_title", "position", "designation", "role"],
    "company": ["company", "organization", "organisation", "company name", "company_name", "business", "firm"],
    "linkedin_url": ["linkedin_url", "linkedin", "linkedin url", "linkedin profile", "linkedin_profile", "linkedinurl"],
    "website": ["website", "web", "site", "company website", "company_website", "web address", "url"],
    "industry": ["industry", "sector", "vertical", "industry type", "industry_type"],
    "location": ["location", "address", "full address", "full_address"],
    "city": ["city", "town", "municipality"],
    "state": ["state", "province", "region", "territory"],
    "country": ["country", "nation"],
    "postal_code": ["postal_code", "postal code", "zip", "zip code", "zip_code", "pincode", "pin code", "pin_code"],
    "company_size": ["company_size", "company size", "employees", "employee count", "employee_count", "size", "company employees"],
    "revenue": ["revenue", "annual revenue", "annual_revenue", "turnover", "sales", "company revenue"],
    "products_services": ["products_services", "products/services", "products", "services", "product/service", "offering", "offerings"],
    "notes": ["notes", "note", "comments", "remarks", "additional notes", "additional_notes", "description"],
}


def normalize_headers(headers: list[str]) -> dict[str, str]:
    """Map CSV header names to canonical field names."""
    mapping = {}
    for h in headers:
        h_clean = h.strip().lower()
        matched = False
        for canonical, aliases in COLUMN_MAP.items():
            if h_clean in aliases:
                mapping[h] = canonical
                matched = True
                break
        if not matched:
            mapping[h] = h_clean.replace(" ", "_").replace("-", "_")
    return mapping


def parse_csv(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return []

    col_map = normalize_headers(reader.fieldnames)
    leads = []
    for row in reader:
        lead: dict[str, Any] = {}
        for csv_col, val in row.items():
            if not val or not val.strip():
                continue
            canonical = col_map.get(csv_col, csv_col)
            lead[canonical] = val.strip()

        lead.setdefault("source", "csv")
        if lead.get("email") or lead.get("first_name") or lead.get("company"):
            leads.append(lead)
    return leads


def validate_lead_row(row: dict) -> list[str]:
    errors = []
    if not row.get("email") and not row.get("first_name") and not row.get("company"):
        errors.append("Row must have at least an email, first_name, or company")
    return errors
