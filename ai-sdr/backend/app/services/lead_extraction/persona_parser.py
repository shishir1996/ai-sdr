import json
import re
from typing import Optional
from app.services.ai.model_client import generate_text, generate_text_async

SYSTEM_PROMPT = """You are an expert B2B lead generation analyst. Given a customer persona description, you must extract structured fields that can be used to find matching leads via web scraping.

Respond ONLY with a valid JSON object (no markdown, no explanations) containing these keys:
- suggested_title: string (job title to target, e.g. "CTO", "VP of Engineering")
- suggested_industry: string (industry, e.g. "Technology", "Healthcare")
- suggested_location: string (specific location, e.g. "Bangalore", "San Francisco")
- suggested_country: string (country name, e.g. "India", "United States")
- suggested_business_category: string (business category from: Automotive, Beauty & Personal Care, Business Services, Construction & Contractors, Education, Entertainment & Recreation, Finance & Insurance, Food & Dining, Health & Medical, Home Services, IT & Technology, Legal Services, Manufacturing, Marketing & Advertising, Media & Communications, Real Estate, Retail, Shopping, Sports & Fitness, Transportation & Logistics, Travel & Hospitality)
- keywords: array of strings (search keywords relevant to finding these leads)
- directory_types: array of strings (relevant directory types, e.g. ["IndiaMart", "JustDial", "LinkedIn"])
- fields_to_extract: array of strings (which fields to prioritize: "name", "email", "phone", "company", "title", "industry", "location", "company_size", "linkedin_url", "website", "social_links", "team_members")
- description: string (a concise 1-sentence summary of the ideal lead profile)

Example output:
{
  "suggested_title": "CTO",
  "suggested_industry": "Technology",
  "suggested_location": "Bangalore",
  "suggested_country": "India",
  "suggested_business_category": "IT & Technology",
  "keywords": ["software", "SaaS", "B2B", "startup", "tech"],
  "directory_types": ["JustDial", "IndiaMart"],
  "fields_to_extract": ["name", "email", "phone", "company", "title", "industry", "location"],
  "description": "CTOs at mid-size tech companies in Bangalore who make purchasing decisions for SaaS tools"
}"""


async def parse_persona(persona_text: str, api_key: Optional[str] = None) -> dict:
    raw = await generate_text_async(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Parse this customer persona:\n\n{persona_text}",
        max_tokens=600,
        temperature=0.3,
        api_key=api_key,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "suggested_title": "",
                "suggested_industry": "",
                "suggested_location": "",
                "suggested_country": "",
                "keywords": [],
                "directory_types": [],
                "fields_to_extract": [],
                "description": "",
            }
    for key in ["suggested_title", "suggested_industry", "suggested_location", "suggested_country", "suggested_business_category", "description"]:
        if key not in result:
            result[key] = ""
    for key in ["keywords", "directory_types", "fields_to_extract"]:
        if key not in result:
            result[key] = []
    return result
