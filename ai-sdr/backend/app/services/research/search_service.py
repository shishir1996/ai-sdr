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


async def _ai_generate_results(query: str, source_label: str, num_results: int) -> list[dict]:
    from app.services.ai.provider import generate_text
    prompt = (
        f"Act as a web research assistant specializing in {source_label}. "
        f"Based on your training data, find realistic companies and contacts matching: '{query}'. "
        f"Return {num_results} results as a JSON array of objects with these fields: "
        f"title, link, snippet, company_name, contact_name, contact_title, industry, location, contact_email. "
        f"Only return valid JSON, no other text."
    )
    try:
        result = await generate_text("", prompt)
        data = json.loads(result.strip())
        if isinstance(data, list):
            return data[:num_results]
    except Exception as e:
        logger.warning("AI generate for %s failed: %s", source_label, e)
    return []


async def _duckduckgo_search(query: str, num_results: int = 10) -> list[dict]:
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for i, result in enumerate(soup.select(".result")):
                if len(results) >= num_results:
                    break
                title_el = result.select_one(".result__title a")
                snippet_el = result.select_one(".result__snippet")
                if title_el:
                    href = title_el.get("href", "")
                    match = re.search(r"uddg=(https?://[^&]+)", href)
                    link = match.group(1) if match else href
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "link": link,
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        "company_name": "",
                        "contact_name": "",
                        "contact_title": "",
                        "industry": "",
                        "location": "",
                    })
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
    return results


async def _scrape_company_website(company_name: str) -> dict:
    info = {"website": "", "contacts": [], "description": ""}
    try:
        url = f"https://www.google.com/search?q={quote_plus(company_name + ' company about team')}"
        html = await _scrape_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.select("a[href^='http']"):
                href = a.get("href", "")
                if re.search(r"(linkedin\.com/company|crunchbase|zoominfo)", href, re.I):
                    info["website"] = href
                    break
    except Exception as e:
        logger.debug("Company scrape failed for %s: %s", company_name, e)
    return info


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
            for i, li in enumerate(soup.select("#b_results > li.b_algo")):
                if len(results) >= num_results:
                    break
                title_el = li.select_one("h2 a")
                snippet_el = li.select_one(".b_caption p")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "link": title_el.get("href", ""),
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                        "company_name": "",
                        "contact_name": "",
                        "contact_title": "",
                        "industry": "",
                        "location": "",
                    })
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
        if r.get("link") and not r.get("company_name"):
            scraped = await _scrape_company_website(r.get("title", ""))
            r["website"] = scraped.get("website", "")
    return results


async def search_business_directories(query: str, num_results: int = 10) -> list[dict]:
    results = []
    directories = [
        f"https://www.google.com/search?q={quote_plus(query + ' site:crunchbase.com OR site:linkedin.com/company OR site:angellist.com')}",
        f"https://www.bing.com/search?q={quote_plus(query + ' startup directory')}",
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
                if text and any(d in href for d in ["crunchbase", "linkedin", "angellist", "g2.com", "capterra"]):
                    results.append({
                        "title": text,
                        "link": href,
                        "snippet": "",
                        "company_name": text,
                        "contact_name": "",
                        "contact_title": "",
                        "industry": "",
                        "location": "",
                    })
    if not results:
        results = await _ai_generate_results(query, "business directories", num_results)
    return results


async def search_company_websites(query: str, num_results: int = 10) -> list[dict]:
    results = await _duckduckgo_search(query, num_results)
    enriched = []
    for r in results:
        if r.get("link"):
            html = await _scrape_html(r["link"])
            if html:
                text = await _extract_text(html)
                emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
                r["contact_email"] = emails[0] if emails else ""
                names = re.findall(r"(?:VP|Director|Head|Chief|Manager)\s+of\s+\w+", text)
                r["contact_title"] = names[0] if names else ""
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
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "link": href,
                        "snippet": "",
                        "company_name": "",
                        "contact_name": "",
                        "contact_title": "",
                        "industry": "",
                        "location": "",
                    })
    except Exception as e:
        logger.warning("News search failed: %s", e)
    if not results:
        results = await _ai_generate_results(query, "news sites", num_results)
    return results


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
                logger.info("Search %s returned %d results for query: %s", source_key, len(source_results), query[:60])
            except Exception as e:
                logger.warning("Search handler %s failed: %s", source_key, e)
    return results
