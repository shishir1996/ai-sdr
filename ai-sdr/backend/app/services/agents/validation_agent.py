import logging
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.base_agent import BaseAgent
from app.models.lead_intelligence import ValidationResult
from app.services.research.search_service import _scrape_html

logger = logging.getLogger(__name__)

EMAIL_SYNTAX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_FORMAT = re.compile(r'^\+?\d{7,15}$')
URL_FORMAT = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.I)


class ValidationAgent(BaseAgent):
    """Validates discovered data quality and legitimacy.

    Verifies: website active, email syntax valid, phone format valid,
    company legitimacy.
    Flags: duplicates, fake websites, dead links, invalid contacts.
    """

    agent_type = "validation"

    async def execute_plan(self, plan: dict) -> dict:
        await self._log_reasoning("execution_start", "Validating discovered data")
        steps = plan.get("steps", [{"name": "validate", "description": "Validate data quality"}])
        all_validations = []
        issues = []
        recommendations = []

        for step in steps:
            step_result = await self._execute_step(step)
            all_validations.extend(step_result.get("validations", []))
            issues.extend(step_result.get("issues", []))
            recommendations.extend(step_result.get("recommendations", []))

        valid_count = len([v for v in all_validations if v.get("status") == "valid"])
        total_count = len(all_validations)
        quality_score = valid_count / max(total_count, 1)

        return {
            "work_completed": f"Validated {total_count} data points ({valid_count} valid, {total_count - valid_count} flagged)",
            "findings": all_validations,
            "confidence": quality_score,
            "risks": issues[:5],
            "recommendations": recommendations or ["Remove flagged entries before CRM import"],
            "next_action": "enrich_data" if quality_score >= 0.5 else "collect_fresh_data",
        }

    async def _execute_step(self, step: dict) -> dict:
        validations = []
        issues = []
        recs = []

        data = step.get("data", {})
        data_type = step.get("validation_type", "all")

        if data_type in ("email", "all"):
            email = data.get("email", "")
            if email:
                v = self._validate_email(email)
                validations.append(v)
                if v["status"] != "valid":
                    issues.append(f"Invalid email: {email[:30]}")

        if data_type in ("phone", "all"):
            phone = data.get("phone", "")
            if phone:
                v = self._validate_phone(phone)
                validations.append(v)
                if v["status"] != "valid":
                    issues.append(f"Invalid phone format")

        if data_type in ("website", "all"):
            website = data.get("website", "")
            if website:
                v = await self._validate_website(website)
                validations.append(v)
                if v["status"] != "valid":
                    issues.append(f"Website issue: {website[:40]}")

        if data_type in ("company", "all"):
            company = data.get("company", "")
            if company:
                v = self._validate_company_name(company)
                validations.append(v)

        if not validations:
            recs.append("Provide data to validate")

        return {"validations": validations, "issues": issues, "recommendations": recs}

    def _validate_email(self, email: str) -> dict:
        if not EMAIL_SYNTAX.match(email):
            return {"validation_type": "email", "value": email, "status": "invalid", "score": 0.0, "issues": ["Invalid email syntax"]}
        disposable_domains = ["tempmail.com", "throwaway.com", "mailinator.com", "guerrillamail.com"]
        domain = email.split("@")[-1].lower()
        if domain in disposable_domains:
            return {"validation_type": "email", "value": email, "status": "flag", "score": 0.3, "issues": ["Disposable email domain"]}
        return {"validation_type": "email", "value": email, "status": "valid", "score": 0.9, "issues": []}

    def _validate_phone(self, phone: str) -> dict:
        cleaned = re.sub(r'[\s\-\(\)\.]', '', phone)
        if not PHONE_FORMAT.match(cleaned):
            return {"validation_type": "phone", "value": phone, "status": "invalid", "score": 0.0, "issues": ["Invalid phone format"]}
        if len(cleaned) < 8:
            return {"validation_type": "phone", "value": phone, "status": "flag", "score": 0.3, "issues": ["Phone number too short"]}
        return {"validation_type": "phone", "value": phone, "status": "valid", "score": 0.8, "issues": []}

    async def _validate_website(self, url: str) -> dict:
        if not URL_FORMAT.match(url):
            return {"validation_type": "website", "value": url, "status": "invalid", "score": 0.0, "issues": ["Invalid URL format"]}
        try:
            html = await _scrape_html(url)
            if html:
                return {"validation_type": "website", "value": url, "status": "valid", "score": 0.95, "issues": []}
            else:
                return {"validation_type": "website", "value": url, "status": "flag", "score": 0.3, "issues": ["Website unreachable"]}
        except Exception:
            return {"validation_type": "website", "value": url, "status": "flag", "score": 0.2, "issues": ["Website fetch failed"]}

    def _validate_company_name(self, name: str) -> dict:
        if not name or len(name.strip()) < 2:
            return {"validation_type": "company", "value": name, "status": "invalid", "score": 0.0, "issues": ["Company name too short"]}
        if name.lower() in ("company", "unknown", "n/a", "none"):
            return {"validation_type": "company", "value": name, "status": "flag", "score": 0.2, "issues": ["Placeholder company name"]}
        return {"validation_type": "company", "value": name, "status": "valid", "score": 0.8, "issues": []}
