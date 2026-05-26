from typing import Optional
from app.config import get_settings

settings = get_settings()

_client: Optional[object] = None
_current_key: Optional[str] = None


def get_client(api_key_override: Optional[str] = None):
    global _client, _current_key
    key = api_key_override or settings.TOGETHER_API_KEY
    if not key:
        raise ValueError("Together AI API key not configured. Set it in Admin > Integrations.")
    if _client is None or key != _current_key:
        from together import Together
        _client = Together(api_key=key)
        _current_key = key
    return _client


def generate_text(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    client = get_client(api_key)
    response = client.chat.completions.create(
        model=settings.TOGETHER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
