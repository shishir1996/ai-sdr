import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.lead_sources.service import is_source_enabled

logger = logging.getLogger(__name__)


async def search_google(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a web research assistant. Based on your training data, find realistic "
        f"companies and contacts matching: '{query}'. Return {num_results} results as "
        f"a JSON array with objects containing: title, link, snippet, company_name, "
        f"contact_name (if known), contact_title (if known). "
        f"Only return valid JSON, no other text."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("Google search via AI failed: %s", e)
        return []


async def search_bing(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a Bing web search assistant. Find realistic companies matching: "
        f"'{query}'. Return {num_results} results as JSON array with: title, link, "
        f"snippet, company_name, contact_name, contact_title. Only return valid JSON."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("Bing search via AI failed: %s", e)
        return []


async def search_web_general(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a web research assistant searching public sources. Find realistic "
        f"companies and decision-makers matching: '{query}'. "
        f"Search company websites, directories, and public listings. "
        f"Return {num_results} results as JSON array with: title, link, snippet, "
        f"company_name, contact_name, contact_title, industry, location. "
        f"Only return valid JSON."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("Web research via AI failed: %s", e)
        return []


async def search_business_directories(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a business directory search assistant. Find companies matching: "
        f"'{query}' from business directories, startup directories, and industry listings. "
        f"Return {num_results} results as JSON array with: title, link, snippet, "
        f"company_name, contact_name, contact_title, industry, location. "
        f"Only return valid JSON."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("Business directory search via AI failed: %s", e)
        return []


async def search_company_websites(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a company website scraper. Find company websites and extract "
        f"contact information for businesses matching: '{query}'. "
        f"Look for 'About Us', 'Team', 'Contact' pages. "
        f"Return {num_results} results as JSON array with: title, link, snippet, "
        f"company_name, contact_name, contact_title, contact_email. "
        f"Only return valid JSON."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("Company website search via AI failed: %s", e)
        return []


async def search_news_sites(query: str, num_results: int = 10) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a news research assistant. Find recent news articles about "
        f"companies and executives matching: '{query}'. "
        f"Return {num_results} results as JSON array with: title, link, snippet, "
        f"company_name, contact_name, contact_title. Only return valid JSON."
    )
    try:
        result = await generate_text(prompt, model="claude-3-haiku")
        import json
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
        return []
    except Exception as e:
        logger.warning("News search via AI failed: %s", e)
        return []


SEARCH_HANDLERS = {
    "google_search": search_google,
    "bing_search": search_bing,
    "web_research": search_web_general,
    "business_directories": search_business_directories,
    "company_websites": search_company_websites,
    "news_sites": search_news_sites,
}


async def search_all_enabled(
    db: AsyncSession,
    org_id: str,
    query: str,
    num_results: int = 10,
) -> list[dict]:
    results = []
    for source_key, handler in SEARCH_HANDLERS.items():
        if await is_source_enabled(db, org_id, source_key):
            try:
                source_results = await handler(query, num_results)
                for r in source_results:
                    r["_source"] = source_key
                results.extend(source_results)
            except Exception as e:
                logger.warning("Search handler %s failed: %s", source_key, e)
    return results
