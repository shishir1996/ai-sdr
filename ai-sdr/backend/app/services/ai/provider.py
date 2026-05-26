from typing import Optional, Literal
from dataclasses import dataclass
from app.config import get_settings

settings = get_settings()


AiProvider = Literal["openai", "claude", "gemini", "together"]


@dataclass
class AiModel:
    provider: AiProvider
    model_id: str
    display_name: str
    max_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float


AVAILABLE_MODELS: dict[str, AiModel] = {
    "gpt-4o": AiModel("openai", "gpt-4o", "GPT-4o", 128000, 0.005, 0.015),
    "gpt-4o-mini": AiModel("openai", "gpt-4o-mini", "GPT-4o Mini", 128000, 0.00015, 0.0006),
    "gpt-3.5-turbo": AiModel("openai", "gpt-3.5-turbo", "GPT-3.5 Turbo", 16385, 0.0015, 0.002),
    "claude-3.5-sonnet": AiModel("claude", "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet", 200000, 0.003, 0.015),
    "claude-3-haiku": AiModel("claude", "claude-3-haiku-20240307", "Claude 3 Haiku", 200000, 0.00025, 0.00125),
    "gemini-1.5-pro": AiModel("gemini", "gemini-1.5-pro", "Gemini 1.5 Pro", 1000000, 0.0035, 0.0105),
    "gemini-1.5-flash": AiModel("gemini", "gemini-1.5-flash", "Gemini 1.5 Flash", 1000000, 0.00035, 0.00105),
    "llama-3.1-8b": AiModel("together", "meta-llama/Llama-3.1-8B-Instruct", "Llama 3.1 8B", 8192, 0.0002, 0.0002),
    "llama-3.1-70b": AiModel("together", "meta-llama/Llama-3.1-70B-Instruct", "Llama 3.1 70B", 8192, 0.0009, 0.0009),
    "mixtral-8x7b": AiModel("together", "mistralai/Mixtral-8x7B-Instruct-v0.1", "Mixtral 8x7B", 32768, 0.0006, 0.0006),
}

DEFAULT_MODEL = "llama-3.1-8b"


def get_model(model_id: str) -> AiModel:
    return AVAILABLE_MODELS.get(model_id, AVAILABLE_MODELS[DEFAULT_MODEL])


async def generate_text(
    system_prompt: str,
    user_prompt: str,
    model_id: str = DEFAULT_MODEL,
    max_tokens: int = 512,
    temperature: float = 0.7,
    api_key: Optional[str] = None,
) -> str:
    model = get_model(model_id)

    if model.provider == "together":
        return await _together_generate(system_prompt, user_prompt, model, max_tokens, temperature, api_key)
    elif model.provider == "openai":
        return await _openai_generate(system_prompt, user_prompt, model, max_tokens, temperature, api_key)
    elif model.provider == "claude":
        return await _claude_generate(system_prompt, user_prompt, model, max_tokens, temperature, api_key)
    elif model.provider == "gemini":
        return await _gemini_generate(system_prompt, user_prompt, model, max_tokens, temperature, api_key)
    else:
        raise ValueError(f"Unsupported provider: {model.provider}")


async def _together_generate(
    system_prompt: str,
    user_prompt: str,
    model: AiModel,
    max_tokens: int,
    temperature: float,
    api_key: Optional[str],
) -> str:
    from together import Together
    key = api_key or settings.TOGETHER_API_KEY
    if not key:
        raise ValueError("Together AI API key not configured")
    client = Together(api_key=key)
    response = client.chat.completions.create(
        model=model.model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


async def _openai_generate(
    system_prompt: str,
    user_prompt: str,
    model: AiModel,
    max_tokens: int,
    temperature: float,
    api_key: Optional[str],
) -> str:
    from openai import OpenAI
    key = api_key or settings.OPENAI_API_KEY
    if not key:
        raise ValueError("OpenAI API key not configured")
    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model.model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


async def _claude_generate(
    system_prompt: str,
    user_prompt: str,
    model: AiModel,
    max_tokens: int,
    temperature: float,
    api_key: Optional[str],
) -> str:
    import anthropic
    key = api_key or settings.ANTHROPIC_API_KEY
    if not key:
        raise ValueError("Anthropic API key not configured")
    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=model.model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text.strip()


async def _gemini_generate(
    system_prompt: str,
    user_prompt: str,
    model: AiModel,
    max_tokens: int,
    temperature: float,
    api_key: Optional[str],
) -> str:
    import google.generativeai as genai
    key = api_key or settings.GOOGLE_AI_API_KEY
    if not key:
        raise ValueError("Google AI API key not configured")
    genai.configure(api_key=key)
    gen_model = genai.GenerativeModel(
        model.model_id,
        system_instruction=system_prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    response = gen_model.generate_content(user_prompt)
    return response.text.strip()
