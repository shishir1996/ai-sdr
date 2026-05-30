import logging
from typing import Optional
from app.services.ai.model_client import generate_text, generate_text_async

logger = logging.getLogger(__name__)

COUNTRY_PROFILES = {
    "us": {
        "tone": "direct and friendly",
        "greeting": "Hi",
        "communication_style": "casual professional",
        "vocabulary": ["team", "value", "growth", "results", "partnership"],
        "sales_psychology": "focus on ROI and efficiency gains",
        "formality": "moderate",
        "email_length": "concise (3-4 sentences)",
    },
    "uk": {
        "tone": "polite and understated",
        "greeting": "Dear",
        "communication_style": "formal professional",
        "vocabulary": ["whilst", "keen", "bespoke", "tailored", "opportunity"],
        "sales_psychology": "focus on credibility and relationship",
        "formality": "high",
        "email_length": "moderate (4-5 sentences)",
    },
    "india": {
        "tone": "respectful and professional",
        "greeting": "Dear",
        "communication_style": "formal but warm",
        "vocabulary": ["kindly", "regards", "opportunity", "mutually beneficial", "collaboration"],
        "sales_psychology": "focus on value and long-term relationship",
        "formality": "high",
        "email_length": "moderate (4-6 sentences)",
    },
    "australia": {
        "tone": "friendly and straightforward",
        "greeting": "G'day",
        "communication_style": "casual and no-nonsense",
        "vocabulary": ["mate", "keen", "no worries", "fair dinkum", "good on ya"],
        "sales_psychology": "focus on practical benefits and authenticity",
        "formality": "low",
        "email_length": "concise (2-4 sentences)",
    },
    "canada": {
        "tone": "polite and inclusive",
        "greeting": "Hello",
        "communication_style": "friendly professional",
        "vocabulary": ["sorry", "please", "thanks", "appreciate", "wonderful"],
        "sales_psychology": "focus on collaboration and mutual benefit",
        "formality": "moderate",
        "email_length": "moderate (3-5 sentences)",
    },
    "germany": {
        "tone": "direct and factual",
        "greeting": "Dear",
        "communication_style": "formal and precise",
        "vocabulary": ["efficiency", "quality", "engineering", "precision", "reliable"],
        "sales_psychology": "focus on data, facts, and efficiency gains",
        "formality": "high",
        "email_length": "direct (2-4 sentences)",
    },
    "uae": {
        "tone": "respectful and relationship-oriented",
        "greeting": "Dear",
        "communication_style": "formal and courteous",
        "vocabulary": ["esteemed", "partnership", "mutual growth", "respected", "collaboration"],
        "sales_psychology": "focus on relationship and mutual respect first",
        "formality": "high",
        "email_length": "moderate (4-6 sentences)",
    },
    "singapore": {
        "tone": "professional and efficient",
        "greeting": "Dear",
        "communication_style": "formal but direct",
        "vocabulary": ["efficiency", "innovation", "solutions", "partnership", "value"],
        "sales_psychology": "focus on efficiency and proven results",
        "formality": "high",
        "email_length": "moderate (3-5 sentences)",
    },
}

DEFAULT_PROFILE = {
    "tone": "professional",
    "greeting": "Hi",
    "communication_style": "professional",
    "vocabulary": ["solution", "value", "help", "grow"],
    "sales_psychology": "focus on value proposition",
    "formality": "moderate",
    "email_length": "moderate (3-5 sentences)",
}

COUNTRY_KEYWORDS = {
    "us": ["united states", "usa", "america", "us", "north america", "@gmail.com", "@yahoo.com", "@outlook.com"],
    "uk": ["united kingdom", "uk", "england", "britain", "london", "europe", "@co.uk"],
    "india": ["india", "bangalore", "mumbai", "delhi", "pune", "hyderabad", "chennai", "@gmail.com", "@yahoo.co.in"],
    "australia": ["australia", "sydney", "melbourne", "brisbane", "perth", "@gmail.com", "@outlook.com"],
    "canada": ["canada", "toronto", "vancouver", "montreal", "calgary"],
    "germany": ["germany", "berlin", "munich", "hamburg", "frankfurt", ".de"],
    "uae": ["uae", "dubai", "abudhabi", "sharjah", "united arab emirates"],
    "singapore": ["singapore", "sg"],
}


def detect_country(location: str, email: str = "", company: str = "") -> str:
    combined = f"{location} {email} {company}".lower()
    scores = {}
    for country, keywords in COUNTRY_KEYWORDS.items():
        score = sum(2 if kw in combined else 0 for kw in keywords)
        if score > 0:
            scores[country] = score
    if scores:
        return max(scores, key=scores.get)
    return "us"


def get_country_profile(country_code: str) -> dict:
    return COUNTRY_PROFILES.get(country_code, DEFAULT_PROFILE)


async def adapt_outreach_for_country(
    message_text: str,
    country_code: str,
    lead_name: str,
    ai_key: Optional[str] = None,
) -> str:
    profile = get_country_profile(country_code)
    system_prompt = f"""You are a sales communication expert. Adapt this outreach message for a {country_code.upper()} audience.

Country Profile:
- Tone: {profile['tone']}
- Greeting style: {profile['greeting']}
- Communication style: {profile['communication_style']}
- Vocabulary preference: {', '.join(profile['vocabulary'])}
- Sales psychology: {profile['sales_psychology']}
- Formality level: {profile['formality']}

Rules:
- Make it sound naturally from someone in {country_code.upper()}
- Use country-appropriate phrasing and vocabulary
- Maintain the core message but adapt the delivery
- Never use robotic or overly formal language
- The message should feel written by a human from that country
- Keep the same length and key points
- Return ONLY the adapted message text, no explanation or metadata."""

    user_prompt = f"Adapt this message for {lead_name} in {country_code.upper()}:\n\n{message_text}"

    try:
        adapted = await generate_text_async(system_prompt, user_prompt, max_tokens=512, temperature=0.5, api_key=ai_key)
        return adapted.strip()
    except Exception as e:
        logger.warning(f"Country adaptation failed: {e}")
        return message_text
