import json
from app.services.ai.model_client import generate_text


def generate_call_script(lead_info: dict, objective: str) -> dict:
    system_prompt = """You are a sales call script writer. Create a structured phone script.
Return JSON with: greeting, introduction, value_proposition, questions (list), objection_handling (dict of objection->response), closing.
Keep it conversational and natural."""

    user_prompt = f"""Create a call script for:
Name: {lead_info.get('first_name', '')} {lead_info.get('last_name', '')}
Title: {lead_info.get('title', 'N/A')}
Company: {lead_info.get('company', 'N/A')}
Objective: {objective}

Return valid JSON."""

    raw = generate_text(system_prompt, user_prompt, max_tokens=768, temperature=0.7)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"greeting": f"Hi {lead_info.get('first_name', '')}", "introduction": raw}


def analyze_reply(email_thread: str) -> dict:
    system_prompt = """Analyze the email reply and return JSON with:
- sentiment: positive/negative/neutral
- intent: interested/not_interested/meeting_request/out_of_office/other
- suggested_response: brief reply suggestion
- urgency: high/medium/low"""

    raw = generate_text(system_prompt, email_thread[:2000], max_tokens=256, temperature=0.3)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"sentiment": "neutral", "intent": "other", "suggested_response": "", "urgency": "low"}


def next_best_action(lead_state: dict) -> str:
    system_prompt = """Recommend the next best action for this lead based on their current state.
Options: send_email, make_call, send_linkedin_message, wait, move_to_deals, archive.
Respond with just the action name."""

    user_prompt = f"""Lead state: {json.dumps(lead_state)}
What is the next best action?"""

    return generate_text(system_prompt, user_prompt, max_tokens=50, temperature=0.3)
