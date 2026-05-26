import json
from typing import Optional
from app.services.ai.model_client import generate_text


def score_lead(lead_data: dict, api_key: Optional[str] = None) -> dict:
    system_prompt = """You are a B2B lead scoring AI. Analyze the lead profile and return a JSON with:
- score: integer 0-100
- reasoning: brief explanation
- priority: "hot", "warm", or "cold"
Consider: title seniority, company fit, industry relevance, location."""

    user_prompt = f"""Score this lead:
Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
Title: {lead_data.get('title', 'N/A')}
Company: {lead_data.get('company', 'N/A')}
Industry: {lead_data.get('industry', 'N/A')}
Location: {lead_data.get('location', 'N/A')}
Company Size: {lead_data.get('company_size', 'N/A')}

Return valid JSON only."""

    raw = generate_text(system_prompt, user_prompt, max_tokens=256, temperature=0.3, api_key=api_key)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 50, "reasoning": "AI scoring failed", "priority": "warm"}
