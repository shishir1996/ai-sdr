import json
from typing import Optional
from app.services.ai.model_client import generate_text


def draft_email(
    lead_info: dict,
    campaign_context: str,
    tone: str = "professional",
    api_key: Optional[str] = None,
) -> dict:
    system_prompt = f"""You are a B2B sales email writer. Write a {tone} cold outreach email.
Return JSON with: subject (under 60 chars), body (plain text, 3-4 sentences).
Personalize using lead variables. Include a clear CTA."""

    user_prompt = f"""Write an email for:
Name: {lead_info.get('first_name', '')} {lead_info.get('last_name', '')}
Title: {lead_info.get('title', 'N/A')}
Company: {lead_info.get('company', 'N/A')}
Industry: {lead_info.get('industry', 'N/A')}

Campaign context: {campaign_context}

Return valid JSON with keys: subject, body"""

    raw = generate_text(system_prompt, user_prompt, max_tokens=512, temperature=0.7, api_key=api_key)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"subject": f"Quick question, {lead_info.get('first_name', '')}", "body": raw}
