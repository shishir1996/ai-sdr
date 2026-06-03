import logging
import json
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import ContactDiscovery
from app.services.research.search_service import search_web_general, _scrape_html, _extract_text

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4,10}')


class ContactDiscoveryAgent(BaseAgent):
    """Finds contact information for discovered decision makers.

    Collects: email addresses, phone numbers.
    Generates confidence scores per contact method.
    """

    agent_type = "contact_discovery"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Discovering contact information")
        steps = plan.get("steps", [{"name": "find_contacts", "description": "Find contact emails and phones"}])
        all_contacts = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_contacts.extend(step_result.get("contacts", []))
            recommendations.extend(step_result.get("recommendations", []))

        email_count = len([c for c in all_contacts if c.get("contact_type") == "email"])
        phone_count = len([c for c in all_contacts if c.get("contact_type") == "phone"])
        confidence = min(1.0, (email_count * 0.25 + phone_count * 0.2))

        return {
            "work_completed": f"Found {email_count} emails, {phone_count} phones",
            "findings": all_contacts,
            "confidence": confidence,
            "risks": ["Emails may be generic (info@) rather than personal"],
            "recommendations": recommendations or [
                "Verify email deliverability before sending",
                "Use email finding tools for higher accuracy",
            ],
            "next_action": "validate_contacts" if all_contacts else "search_contact_page",
        }

    async def _execute_step(self, step: dict) -> dict:
        description = step.get("description", "")
        company = step.get("company", description)
        website = step.get("website", "")
        contacts = []

        if website:
            html = await _scrape_html(website)
            if html:
                text = _extract_text(html)
                contacts.extend(self._extract_from_text(text, "website", website))

        queries = [
            f"{company} email address contact",
            f"{company} contact us",
            f"{company} email format",
        ]
        for q in queries[:2]:
            try:
                results = await search_web_general(q, num_results=5)
                for r in results:
                    if r.get("link"):
                        html = await _scrape_html(r["link"])
                        if html:
                            text = _extract_text(html)
                            contacts.extend(self._extract_from_text(text, "search", r["link"]))
            except Exception as e:
                logger.warning("Contact search failed: %s", e)

        if not contacts:
            contacts.append({
                "contact_type": "email",
                "value": f"info@{self._domain_from_website(website)}" if website else "Unknown",
                "source": "pattern_generated",
                "confidence": 0.2,
                "verified": False,
            })

        seen = set()
        unique = []
        for c in contacts:
            key = f"{c.get('contact_type')}:{c.get('value')}"
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return {"contacts": unique[:10], "recommendations": ["Use email verification tool to validate"]}

    def _extract_from_text(self, text: str, source: str, source_url: str) -> list[dict]:
        contacts = []
        emails = EMAIL_REGEX.findall(text)
        for e in emails[:5]:
            if not e.endswith((".png", ".jpg", ".jpeg", ".gif", ".css", ".js")):
                confidence = 0.7 if source == "website" else 0.5
                contacts.append({
                    "contact_type": "email",
                    "value": e,
                    "source": source,
                    "source_url": source_url,
                    "confidence": confidence,
                    "verified": False,
                })
        phones = PHONE_REGEX.findall(text)
        for p in phones[:3]:
            cleaned = re.sub(r'[^\d+]', '', p)
            if len(cleaned) >= 7:
                contacts.append({
                    "contact_type": "phone",
                    "value": p.strip(),
                    "source": source,
                    "source_url": source_url,
                    "confidence": 0.6,
                    "verified": False,
                })
        return contacts

    def _domain_from_website(self, website: str) -> str:
        if not website:
            return "company.com"
        match = re.search(r'https?://(?:www\.)?([^/]+)', website)
        return match.group(1) if match else website
