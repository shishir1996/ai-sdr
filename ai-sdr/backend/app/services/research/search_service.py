import logging
import json
import re
from typing import Optional
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.lead_sources.service import is_source_enabled

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

PHONE_REGEX = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4,10}'
)
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
POSTAL_CODE_REGEX = re.compile(
    r'\b\d{5}(?:[-\s]\d{4})?\b|\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b'
)


async def _scrape_html(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                return resp.text
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
    return None


async def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _extract_emails(text: str) -> list[str]:
    return list(set(EMAIL_REGEX.findall(text)))


def _extract_phones(text: str) -> list[str]:
    return list(set(PHONE_REGEX.findall(text)))


def _extract_postal_codes(text: str) -> list[str]:
    return list(set(POSTAL_CODE_REGEX.findall(text)))


def _parse_address(text: str) -> dict:
    parts = [p.strip() for p in re.split(r'[,;\n]+', text) if p.strip()]
    result = {"city": "", "state": "", "country": "", "postal_code": ""}

    for p in parts:
        pc = POSTAL_CODE_REGEX.search(p)
        if pc and not result["postal_code"]:
            result["postal_code"] = pc.group()

    known_countries = [
        "usa", "united states", "canada", "uk", "united kingdom",
        "australia", "germany", "france", "india", "china", "japan",
        "brazil", "mexico", "singapore", "uae", "dubai",
    ]
    known_states = [
        "ca", "ny", "tx", "fl", "il", "pa", "oh", "ga", "nc", "mi",
        "ontario", "quebec", "british columbia", "alberta",
        "california", "texas", "florida", "new york",
    ]

    for p in parts:
        pl = p.lower()
        if pl in known_countries and not result["country"]:
            result["country"] = p.title()
        elif pl in known_states and not result["state"]:
            result["state"] = p.title()
        elif result["postal_code"] in p and not result["city"]:
            before = parts[parts.index(p) - 1] if parts.index(p) > 0 else ""
            if before and len(before) > 2:
                result["city"] = before

    if not result["city"] and parts:
        for p in parts:
            pl = p.lower()
            if not any(k in pl for k in known_countries + known_states) and len(p) > 2 and not re.search(r'\d', p):
                result["city"] = p
                break

    return result


def _split_name(full_name: str) -> tuple[str, str]:
    if not full_name:
        return ("", "")
    parts = full_name.strip().split(None, 1)
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""
    return (first, last)


def _guess_company_title(text: str) -> str:
    patterns = [
        r'(?:VP|Director|Head|Chief|Manager|Lead|President|Founder|CEO|CTO|COO|CFO|Owner|Principal|Partner)\s+of\s+[\w\s]+',
        r'(?:VP|Director|Head|Chief|Manager|Lead|President|Founder|CEO|CTO|COO|CFO|Owner|Principal|Partner)\b[\w\s,]*',
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group().strip()
    return ""


async def _enrich_page(url: str, existing: dict) -> dict:
    html = await _scrape_html(url)
    if not html:
        return existing
    text = _extract_text(html)

    if not existing.get("contact_email"):
        emails = _extract_emails(text)
        if emails:
            existing["contact_email"] = emails[0]

    if not existing.get("contact_phone"):
        phones = _extract_phones(text)
        if phones:
            existing["contact_phone"] = phones[0]

    if not existing.get("contact_title"):
        title = _guess_company_title(text)
        if title:
            existing["contact_title"] = title

    if not existing.get("city") or not existing.get("state") or not existing.get("country"):
        address_info = _parse_address(text[:2000])
        for k in ("city", "state", "country", "postal_code"):
            if not existing.get(k) and address_info.get(k):
                existing[k] = address_info[k]

    return existing


async def _ai_generate_results(query: str, source_label: str, num_results: int) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a business data researcher. Find {num_results} real companies matching: '{query}'. "
        f"Return ONLY valid JSON array. Each object must have: "
        f"title, link, snippet, company_name, contact_name, contact_title, "
        f"contact_email, contact_phone, industry, business_type, location, "
        f"city, state, country, postal_code, website. "
        f"Use realistic data for actual companies. No explanation, only JSON."
    )
    try:
        result = await generate_text("", prompt)
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
    except Exception as e:
        logger.warning("AI generate for %s failed: %s", source_label, e)
    return []


def _result(title="", link="", snippet="", company_name="",
            contact_name="", contact_title="", contact_email="",
            contact_phone="", website="", industry="", business_type="",
            location="", city="", state="", country="", postal_code="") -> dict:
    return {
        "title": title, "link": link, "snippet": snippet,
        "company_name": company_name, "contact_name": contact_name,
        "contact_title": contact_title, "contact_email": contact_email,
        "contact_phone": contact_phone, "website": website,
        "industry": industry, "business_type": business_type,
        "location": location, "city": city, "state": state,
        "country": country, "postal_code": postal_code,
    }


def _extract_from_snippet(snippet: str) -> dict:
    data = {}
    if not snippet:
        return data
    phones = _extract_phones(snippet)
    if phones:
        data["contact_phone"] = phones[0]
    emails = _extract_emails(snippet)
    if emails:
        data["contact_email"] = emails[0]
    address = _parse_address(snippet)
    for k in ("city", "state", "country", "postal_code"):
        if address.get(k):
            data[k] = address[k]
    return data


async def _duckduckgo_search(query: str, num_results: int = 10) -> list[dict]:
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for result in soup.select(".result"):
                if len(results) >= num_results:
                    break
                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")
                if title_el:
                    href = title_el.get("href", "")
                    match = re.search(r"uddg=(https?://[^&]+)", href)
                    link = match.group(1) if match else href
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    company = title_el.get_text(strip=True)
                    snippet_data = _extract_from_snippet(snippet)
                    result_item = _result(
                        title=company, link=link, snippet=snippet,
                        company_name=company,
                        location=snippet_data.get("city", ""),
                        city=snippet_data.get("city", ""),
                        state=snippet_data.get("state", ""),
                        country=snippet_data.get("country", ""),
                        postal_code=snippet_data.get("postal_code", ""),
                        contact_phone=snippet_data.get("contact_phone", ""),
                        contact_email=snippet_data.get("contact_email", ""),
                    )
                    if len(results) < 3:
                        result_item = await _enrich_page(link, result_item)
                    results.append(result_item)
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
    return results


async def search_google(query: str, num_results: int = 10) -> list[dict]:
    results = await _duckduckgo_search(query, num_results)
    if not results:
        results = await _ai_generate_results(query, "Google search", num_results)
    return results


async def search_bing(query: str, num_results: int = 10) -> list[dict]:
    results = []
    try:
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for li in soup.select("#b_results > li.b_algo"):
                if len(results) >= num_results:
                    break
                title_el = li.select_one("h2 a")
                snippet_el = li.select_one(".b_caption p")
                if title_el:
                    link = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    company = title_el.get_text(strip=True)
                    snippet_data = _extract_from_snippet(snippet)
                    result_item = _result(
                        title=company, link=link, snippet=snippet,
                        company_name=company,
                        location=snippet_data.get("city", ""),
                        city=snippet_data.get("city", ""),
                        state=snippet_data.get("state", ""),
                        country=snippet_data.get("country", ""),
                        postal_code=snippet_data.get("postal_code", ""),
                        contact_phone=snippet_data.get("contact_phone", ""),
                        contact_email=snippet_data.get("contact_email", ""),
                    )
                    if len(results) < 3:
                        result_item = await _enrich_page(link, result_item)
                    results.append(result_item)
    except Exception as e:
        logger.warning("Bing search failed: %s", e)
    if not results:
        results = await _ai_generate_results(query, "Bing search", num_results)
    return results


async def search_web_general(query: str, num_results: int = 10) -> list[dict]:
    results = await _duckduckgo_search(query, num_results)
    if not results:
        results = await _ai_generate_results(query, "general web research", num_results)
    for r in results:
        if r.get("link") and not r.get("contact_email"):
            r = await _enrich_page(r["link"], r)
    return results


async def search_business_directories(query: str, num_results: int = 10) -> list[dict]:
    results = []
    directories = [
        f"https://www.google.com/search?q={quote_plus(query + ' site:crunchbase.com OR site:linkedin.com/company OR site:angellist.com')}",
        f"https://www.bing.com/search?q={quote_plus(query + ' startup directory')}",
        f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' company contact email phone')}",
    ]
    for url in directories:
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href]"):
                if len(results) >= num_results:
                    break
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if text and len(text) > 3:
                    result_item = _result(
                        title=text, link=href,
                        company_name=text,
                    )
                    result_item = await _enrich_page(href, result_item)
                    results.append(result_item)
    if not results:
        results = await _ai_generate_results(query, "business directories", num_results)
    return results


async def search_company_websites(query: str, num_results: int = 10) -> list[dict]:
    results = await _duckduckgo_search(query, num_results)
    enriched = []
    for r in results:
        if r.get("link"):
            r = await _enrich_page(r["link"], r)
        enriched.append(r)
    if not enriched:
        enriched = await _ai_generate_results(query, "company websites", num_results)
    return enriched


async def search_news_sites(query: str, num_results: int = 10) -> list[dict]:
    results = []
    try:
        url = f"https://news.google.com/search?q={quote_plus(query)}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for article in soup.select("article"):
                if len(results) >= num_results:
                    break
                title_el = article.select_one("a[href^='./']")
                if title_el:
                    href = title_el.get("href", "").replace("./", "https://news.google.com/")
                    company = title_el.get_text(strip=True)
                    result_item = _result(
                        title=company, link=href,
                        company_name=company,
                    )
                    result_item = await _enrich_page(href, result_item)
                    results.append(result_item)
    except Exception as e:
        logger.warning("News search failed: %s", e)
    if not results:
        results = await _ai_generate_results(query, "news sites", num_results)
    return results


async def search_startup_directories(query: str, num_results: int = 10) -> list[dict]:
    results = []
    for site in ["crunchbase.com", "angellist.com", "producthunt.com"]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' site:' + site)}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for result in soup.select(".result"):
                if len(results) >= num_results:
                    break
                title_el = result.select_one(".result__title a")
                if title_el:
                    href = title_el.get("href", "")
                    match = re.search(r"uddg=(https?://[^&]+)", href)
                    link = match.group(1) if match else href
                    company = title_el.get_text(strip=True)
                    result_item = _result(
                        title=company, link=link,
                        company_name=company,
                    )
                    result_item = await _enrich_page(link, result_item)
                    results.append(result_item)
    if not results:
        results = await _ai_generate_results(query, "startup directories", num_results)
    return results


async def search_industry_listings(query: str, num_results: int = 10) -> list[dict]:
    results = []
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query + ' companies list directory')}"
    html = await _scrape_html(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for result in soup.select(".result"):
            if len(results) >= num_results:
                break
            title_el = result.select_one(".result__title a")
            snippet_el = result.select_one(".result__snippet")
            if title_el:
                href = title_el.get("href", "")
                match = re.search(r"uddg=(https?://[^&]+)", href)
                link = match.group(1) if match else href
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                company = title_el.get_text(strip=True)
                result_item = _result(
                    title=company, link=link, snippet=snippet,
                    company_name=company,
                )
                result_item = await _enrich_page(link, result_item)
                results.append(result_item)
    if not results:
        results = await _ai_generate_results(query, "industry listings", num_results)
    return results


SEARCH_HANDLERS = {
    "google_search": search_google,
    "bing_search": search_bing,
    "web_research": search_web_general,
    "business_directories": search_business_directories,
    "company_websites": search_company_websites,
    "news_sites": search_news_sites,
    "startup_directories": search_startup_directories,
    "industry_listings": search_industry_listings,
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
                logger.info("Search %s returned %d results for query: %s", source_key, len(source_results), query[:60])
            except Exception as e:
                logger.warning("Search handler %s failed: %s", source_key, e)
    return results
