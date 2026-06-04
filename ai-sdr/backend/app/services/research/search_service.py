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
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4,10}')
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
POSTAL_CODE_REGEX = re.compile(r'\b\d{5}(?:[-\s]\d{4})?\b|\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b')

_search_progress: dict[str, list[dict]] = {}


def get_search_progress(session_id: str) -> list[dict]:
    return _search_progress.get(session_id, [])


def clear_search_progress(session_id: str):
    _search_progress.pop(session_id, None)


async def _scrape_html(url: str, timeout: int = 15) -> Optional[str]:
    for ua in USER_AGENTS:
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": ua, "Accept-Language": "en-US,en;q=0.9"})
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            logger.debug("Failed to fetch %s: %s", url, e)
    return None


async def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _extract_emails(text: str) -> list[str]:
    seen = set()
    results = []
    for e in EMAIL_REGEX.findall(text):
        domain = e.split("@")[-1].lower()
        if domain not in ("example.com", "domain.com", "domain.net") and not e.endswith((".png", ".jpg", ".css", ".js")):
            if e not in seen:
                seen.add(e)
                results.append(e)
    return results


def _extract_phones(text: str) -> list[str]:
    seen = set()
    results = []
    for p in PHONE_REGEX.findall(text):
        cleaned = re.sub(r'[^\d+]', '', p)
        if 7 <= len(cleaned) <= 15 and cleaned not in seen:
            seen.add(cleaned)
            results.append(p.strip())
    return results


def _parse_address(text: str) -> dict:
    result = {"city": "", "state": "", "country": "", "postal_code": ""}
    pc = POSTAL_CODE_REGEX.search(text)
    if pc:
        result["postal_code"] = pc.group()

    known_countries = ["usa", "united states", "canada", "uk", "united kingdom", "australia", "germany", "france", "india", "china", "japan", "brazil", "mexico", "singapore", "uae"]
    known_states = ["ca", "ny", "tx", "fl", "il", "pa", "oh", "ga", "nc", "mi", "ontario", "quebec", "british columbia", "alberta", "california", "texas", "florida", "new york"]

    parts = [p.strip() for p in re.split(r'[,;\n]+', text) if p.strip()]
    for p in parts:
        pl = p.lower().strip()
        if pl in known_countries and not result["country"]:
            result["country"] = p.title()
        elif pl in known_states and not result["state"]:
            result["state"] = p.title()
    if not result["city"] and parts:
        for p in parts:
            pl = p.lower()
            if not any(k in pl for k in known_countries + known_states) and len(p) > 2 and not re.search(r'\d', p):
                result["city"] = p
                break
    return result


def _make_result(title="", link="", snippet="", company_name="",
                 contact_name="", contact_title="", contact_email="",
                 contact_phone="", website="", industry="", business_type="",
                 location="", city="", state="", country="", postal_code="",
                 search_rank=0, source="google_search") -> dict:
    return {
        "title": title, "link": link, "snippet": snippet,
        "company_name": company_name or title,
        "contact_name": contact_name, "contact_title": contact_title,
        "contact_email": contact_email, "contact_phone": contact_phone,
        "website": website or link,
        "industry": industry, "business_type": business_type,
        "location": location, "city": city, "state": state,
        "country": country, "postal_code": postal_code,
        "search_rank": search_rank, "_source": source,
    }


async def _enrich_from_website(url: str, existing: dict) -> dict:
    """Visit a business website and extract contact info thoroughly."""
    html = await _scrape_html(url, timeout=20)
    if not html:
        return existing

    text = _extract_text(html)

    if not existing.get("contact_email"):
        emails = _extract_emails(text)
        business_emails = [e for e in emails if not e.startswith(("info@", "hello@", "contact@", "support@", "admin@"))]
        if business_emails:
            existing["contact_email"] = business_emails[0]
        elif emails:
            existing["contact_email"] = emails[0]

    if not existing.get("contact_phone"):
        phones = _extract_phones(text)
        if phones:
            existing["contact_phone"] = phones[0]

    if not existing.get("city") or not existing.get("state"):
        addr = _parse_address(text[:2000])
        for k in ("city", "state", "country", "postal_code"):
            if not existing.get(k) and addr.get(k):
                existing[k] = addr[k]

    return existing


async def _search_google(query: str, num_results: int = 10) -> list[dict]:
    """Real Google search via www.google.com/search."""
    results = []
    try:
        url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en&num={num_results}"
        html = await _scrape_html(url)
        if not html:
            logger.warning("Google search returned no HTML for: %s", query[:50])
            return results

        soup = BeautifulSoup(html, "html.parser")

        # Try multiple selector patterns for Google search results
        selectors = [
            "div.g",                # Standard
            "div[data-hveid]",      # Modern
            "div.Gx5Zad",           # Mobile/responsive
            "div.tF2Cxc",           # Another variant
            "div.yuRUbf",           # Title container parent
        ]

        rank = 0
        for selector in selectors:
            divs = soup.select(selector)
            if len(divs) > 1:
                for div in divs:
                    if len(results) >= num_results:
                        break

                    title_el = div.select_one("h3")
                    if not title_el:
                        continue

                    link_el = div.select_one("a[href]")
                    if not link_el:
                        continue

                    href = link_el.get("href", "")
                    if href.startswith("/"):
                        continue

                    snippet_el = div.select_one("div.VwiC3b, span.aCOpRe, div[data-sncf], div.lEBKkf")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    title = title_el.get_text(strip=True)
                    rank += 1

                    # Skip known non-business results
                    if any(s in href for s in ("google.com/shopping", "youtube.com", "maps.google.com")):
                        continue

                    snippet_data = _parse_address(snippet)
                    snippet_phones = _extract_phones(snippet)
                    snippet_emails = _extract_emails(snippet)

                    result = _make_result(
                        title=title, link=href, snippet=snippet,
                        company_name=title,
                        location=snippet_data.get("city", ""),
                        city=snippet_data.get("city", ""),
                        state=snippet_data.get("state", ""),
                        postal_code=snippet_data.get("postal_code", ""),
                        contact_phone=snippet_phones[0] if snippet_phones else "",
                        contact_email=snippet_emails[0] if snippet_emails else "",
                        search_rank=rank,
                        source="google_search",
                    )

                    # Enrich by visiting the website (top results only to avoid timeouts)
                    if rank <= 5 and href.startswith("http"):
                        result = await _enrich_from_website(href, result)

                    results.append(result)

                if results:
                    break  # Found results with this selector

        logger.info("Google search '%s': found %d results", query[:50], len(results))

    except Exception as e:
        logger.warning("Google search failed for '%s': %s", query[:50], e)

    return results


async def _search_google_business(query: str, num_results: int = 10) -> list[dict]:
    """Search Google Maps / Google Business Profiles."""
    results = []
    try:
        # Two approaches: direct Google search for GBP listings + maps
        url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en&num={num_results}&tbm=lcl"
        html = await _scrape_html(url)
        if not html:
            return results

        soup = BeautifulSoup(html, "html.parser")

        # Google local search results
        for div in soup.select("div[data-lid], div.VkpGBb, div.uUPGi"):
            title_el = div.select_one("div.dbg0pd, span.OSrXXb, a[jsname]")
            if not title_el:
                continue

            website_el = div.select_one("a[href*='http']")
            phone_el = div.select_one("span.rllt__details, div[aria-label*='Phone']")
            address_el = div.select_one("div[aria-label*='Address'], div.Qh1C ub sK")

            company = title_el.get_text(strip=True)
            website = website_el.get("href", "") if website_el else ""
            phone = phone_el.get_text(strip=True) if phone_el else ""
            address = address_el.get_text(strip=True) if address_el else ""

            addr_data = _parse_address(address)
            result = _make_result(
                title=company, link=website, company_name=company,
                contact_phone=phone, location=address,
                city=addr_data.get("city", ""), state=addr_data.get("state", ""),
                postal_code=addr_data.get("postal_code", ""),
                search_rank=len(results) + 1,
                source="google_business",
            )
            results.append(result)

        # Also try maps.google.com
        if len(results) < 3:
            maps_url = f"https://www.google.com/maps/search/{quote_plus(query)}/"
            maps_html = await _scrape_html(maps_url)
            if maps_html:
                maps_soup = BeautifulSoup(maps_html, "html.parser")
                for section in maps_soup.select("div[jsaction], div.section-result"):
                    name_el = section.select_one("h1, h2, h3, span.section-result-title")
                    if name_el:
                        company = name_el.get_text(strip=True)
                        result = _make_result(
                            title=company, company_name=company,
                            search_rank=len(results) + 1,
                            source="google_business",
                        )
                        results.append(result)

    except Exception as e:
        logger.warning("Google business search failed: %s", e)

    return results


async def _search_bing(query: str, num_results: int = 10) -> list[dict]:
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
                    link = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    company = title_el.get_text(strip=True)
                    snippet_data = _parse_address(snippet)
                    snippet_phones = _extract_phones(snippet)
                    snippet_emails = _extract_emails(snippet)
                    result = _make_result(
                        title=company, link=link, snippet=snippet,
                        company_name=company,
                        location=snippet_data.get("city", ""),
                        city=snippet_data.get("city", ""),
                        state=snippet_data.get("state", ""),
                        country=snippet_data.get("country", ""),
                        postal_code=snippet_data.get("postal_code", ""),
                        contact_phone=snippet_phones[0] if snippet_phones else "",
                        contact_email=snippet_emails[0] if snippet_emails else "",
                        search_rank=i + 1, source="bing_search",
                    )
                    if len(results) < 3 and link.startswith("http"):
                        result = await _enrich_from_website(link, result)
                    results.append(result)
    except Exception as e:
        logger.warning("Bing search failed: %s", e)
    return results


async def _search_duckduckgo(query: str, num_results: int = 10) -> list[dict]:
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
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                    company = title_el.get_text(strip=True)
                    snippet_data = _parse_address(snippet)
                    snippet_phones = _extract_phones(snippet)
                    snippet_emails = _extract_emails(snippet)
                    result = _make_result(
                        title=company, link=link, snippet=snippet,
                        company_name=company,
                        location=snippet_data.get("city", ""),
                        city=snippet_data.get("city", ""),
                        state=snippet_data.get("state", ""),
                        postal_code=snippet_data.get("postal_code", ""),
                        contact_phone=snippet_phones[0] if snippet_phones else "",
                        contact_email=snippet_emails[0] if snippet_emails else "",
                        search_rank=i + 1, source="web_research",
                    )
                    if len(results) < 3 and link.startswith("http"):
                        result = await _enrich_from_website(link, result)
                    results.append(result)
    except Exception as e:
        logger.warning("DuckDuckGo search failed: %s", e)
    return results


async def _search_business_directories(query: str, num_results: int = 10) -> list[dict]:
    results = []
    dir_queries = [
        f"{query} site:yellowpages.com OR site:superpages.com OR site:merchantcircle.com",
        f"{query} business directory listing",
        f"{query} company contact",
    ]
    for q in dir_queries[:2]:
        try:
            r = await _search_duckduckgo(q, num_results // 2)
            for item in r:
                item["_source"] = "business_directories"
            results.extend(r)
        except Exception:
            pass
    return results[:num_results]


SEARCH_HANDLERS = {
    "google_search": _search_google,
    "google_business": _search_google_business,
    "bing_search": _search_bing,
    "web_research": _search_duckduckgo,
    "business_directories": _search_business_directories,
}


async def search_all_enabled(
    db: AsyncSession,
    org_id: str,
    query: str,
    num_results: int = 10,
    progress_session: Optional[str] = None,
) -> list[dict]:
    results = []
    seen_links = set()

    search_order = ["google_search", "google_business", "bing_search", "web_research", "business_directories"]

    for source_key in search_order:
        handler = SEARCH_HANDLERS.get(source_key)
        if not handler:
            continue
        if not await is_source_enabled(db, org_id, source_key):
            continue

        try:
            source_results = await handler(query, num_results)
            for r in source_results:
                link = r.get("link") or r.get("title", "")
                if link not in seen_links:
                    seen_links.add(link)
                    r["_source"] = source_key
                    results.append(r)

            # Log progress
            if progress_session:
                session_progress = _search_progress.setdefault(progress_session, [])
                session_progress.append({
                    "source": source_key,
                    "query": query[:60],
                    "found": len(source_results),
                    "total_so_far": len(results),
                })

            logger.info("%s returned %d results for '%s'", source_key, len(source_results), query[:60])

        except Exception as e:
            logger.warning("Search handler %s failed: %s", source_key, e)

    return results
