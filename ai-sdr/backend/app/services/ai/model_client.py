import asyncio
from typing import Optional
from app.config import get_settings

settings = get_settings()


def generate_text(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    key = api_key
    model = settings.TOGETHER_MODEL

    if key:
        provider = _detect_provider(key)
    elif settings.OPENROUTER_API_KEY:
        key = settings.OPENROUTER_API_KEY
        model = settings.OPENROUTER_MODEL
        provider = "openrouter"
    elif settings.TOGETHER_API_KEY:
        key = settings.TOGETHER_API_KEY
        provider = "together"
    elif settings.OPENAI_API_KEY:
        key = settings.OPENAI_API_KEY
        model = "gpt-4o-mini"
        provider = "openai"
    else:
        raise ValueError("No AI provider configured. Add an API key in Admin > Integrations.")

    if provider == "openrouter":
        return _openrouter_completion(key, model, system_prompt, user_prompt, max_tokens, temperature)
    elif provider == "together":
        return _together_completion(key, model, system_prompt, user_prompt, max_tokens, temperature)
    elif provider == "openai":
        return _openai_completion(key, model, system_prompt, user_prompt, max_tokens, temperature)
    else:
        return _together_completion(key, model, system_prompt, user_prompt, max_tokens, temperature)


def _detect_provider(api_key: str) -> str:
    if api_key.startswith("sk-or-"):
        return "openrouter"
    if api_key.startswith("sk-"):
        return "openai"
    if api_key.startswith("tgp_") or api_key.startswith("tgp-"):
        return "together"
    return "together"


def _together_completion(
    key: str, model: str, system: str, user: str,
    max_tokens: int, temperature: float,
) -> str:
    from together import Together
    client = Together(api_key=key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _openai_completion(
    key: str, model: str, system: str, user: str,
    max_tokens: int, temperature: float,
) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


def _openrouter_completion(
    key: str, model: str, system: str, user: str,
    max_tokens: int, temperature: float,
) -> str:
    import httpx
    resp = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://app.offdx.in",
            "X-Title": "AI SDR",
        },
        json={
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=60,
    )
    data = resp.json()
    if "error" in data:
        raise ValueError(f"OpenRouter error: {data['error'].get('message', str(data['error']))}")
    return data["choices"][0]["message"]["content"].strip()


async def generate_text_async(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        generate_text,
        system_prompt, user_prompt, max_tokens, temperature, api_key,
    )
