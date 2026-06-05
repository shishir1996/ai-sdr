import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

PHONE_REGEX = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4,10}')
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
POSTAL_CODE_REGEX = re.compile(r'\b\d{5}(?:[-\s]\d{4})?\b|\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b')

PLAYWRIGHT = None
BROWSER = None


async def get_browser():
    global PLAYWRIGHT, BROWSER
    if BROWSER is None or not BROWSER.is_connected():
        PLAYWRIGHT = await async_playwright().start()
        BROWSER = await PLAYWRIGHT.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ],
        )
    return BROWSER


async def close_browser():
    global PLAYWRIGHT, BROWSER
    if BROWSER:
        await BROWSER.close()
        BROWSER = None
    if PLAYWRIGHT:
        await PLAYWRIGHT.stop()
        PLAYWRIGHT = None


async def _stealth_page(browser):
    """Create a page with stealth techniques to avoid bot detection."""
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/Chicago",
        viewport={"width": 1920, "height": 1080},
        device_scale_factor=1,
        has_touch=False,
        is_mobile=False,
    )

    page = await context.new_page()

    # Remove webdriver detection
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
        if (navigator.userAgent.indexOf('Headless') !== -1) {
            Object.defineProperty(navigator, 'userAgent', { get: () => navigator.userAgent.replace('Headless', '') });
        }
    """)

    return page, context


def _extract_emails(text: str) -> list[str]:
    seen = set()
    results = []
    for e in EMAIL_REGEX.findall(text):
        domain = e.split("@")[-1].lower()
        if domain not in ("example.com", "domain.com") and not e.endswith((".png", ".jpg", ".css", ".js", ".svg")):
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
    known_countries = ["usa", "united states", "canada", "uk", "united kingdom", "australia", "germany", "france", "india"]
    known_states = ["ca", "ny", "tx", "fl", "il", "pa", "oh", "ga", "nc", "mi", "california", "texas", "florida", "new york"]
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


async def _detect_captcha(page) -> bool:
    """Check if Google returned a CAPTCHA page."""
    title = await page.title()
    body = await page.inner_text("body")
    if "captcha" in body.lower()[:2000] or "recaptcha" in body.lower()[:2000]:
        return True
    if title and title.startswith("http"):
        return True
    return False


async def google_search(query: str, num_results: int = 10) -> list[dict]:
    """Real Google search via headless browser. Returns results with rank, title, link, snippet."""
    results = []
    browser = await get_browser()
    page, context = await _stealth_page(browser)
    try:
        search_url = f"https://www.google.com/search?q={query}&hl=en&num={num_results}"
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        if await _detect_captcha(page):
            logger.warning("Google CAPTCHA detected for '%s'", query[:50])
            return results

        rank = 0
        # Find all result containers using multiple selector strategies
        for selector in ("div.g", "div[data-hveid]", "div.tF2Cxc"):
            items = await page.query_selector_all(selector)
            if len(items) > 1:
                for item in items:
                    if len(results) >= num_results:
                        break
                    title_el = await item.query_selector("h3")
                    if not title_el:
                        continue
                    link_el = await item.query_selector("a[href]")
                    if not link_el:
                        continue
                    href = await link_el.get_attribute("href") or ""
                    if href.startswith("/") or "google.com/shopping" in href or "youtube.com" in href:
                        continue
                    title = (await title_el.inner_text()).strip()
                    rank += 1

                    snippet = ""
                    for s_sel in ("div.VwiC3b", "span.aCOpRe", "div[data-sncf]", "div.lEBKkf"):
                        s_el = await item.query_selector(s_sel)
                        if s_el:
                            snippet = (await s_el.inner_text()).strip()
                            break

                    addr = _parse_address(snippet)
                    phones = _extract_phones(snippet)
                    emails = _extract_emails(snippet)

                    results.append({
                        "title": title,
                        "link": href,
                        "snippet": snippet,
                        "company_name": title,
                        "contact_name": "",
                        "contact_email": emails[0] if emails else "",
                        "contact_phone": phones[0] if phones else "",
                        "website": href,
                        "location": addr.get("city", ""),
                        "city": addr.get("city", ""),
                        "state": addr.get("state", ""),
                        "country": addr.get("country", ""),
                        "postal_code": addr.get("postal_code", ""),
                        "search_rank": rank,
                        "_source": "google_search",
                    })
                if results:
                    break

        logger.info("Google browser search '%s': %d results", query[:50], len(results))
    except Exception as e:
        logger.warning("Google browser search failed: %s", e)
    finally:
        await page.close()
        await context.close()
    return results


async def google_business_search(query: str, num_results: int = 10) -> list[dict]:
    """Search Google Maps / local results for business listings."""
    results = []
    browser = await get_browser()
    page, context = await _stealth_page(browser)
    try:
        url = f"https://www.google.com/search?q={query}&hl=en&tbm=lcl"
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        if await _detect_captcha(page):
            logger.warning("Google business CAPTCHA detected")
            return results

        listings = await page.query_selector_all("div[data-lid], div.VkpGBb, div.uUPGi")
        for listing in listings[:num_results]:
            try:
                title_el = await listing.query_selector("div.dbg0pd, span.OSrXXb, a[jsname]")
                if not title_el:
                    continue
                company = (await title_el.inner_text()).strip()

                website = ""
                website_el = await listing.query_selector("a[href*='http']")
                if website_el:
                    website = await website_el.get_attribute("href") or ""

                phone = ""
                phone_el = await listing.query_selector("[aria-label*='Phone'], span.rllt__details")
                if phone_el:
                    phone = (await phone_el.inner_text()).strip()

                address = ""
                addr_el = await listing.query_selector("[aria-label*='Address']")
                if addr_el:
                    address = (await addr_el.get_attribute("aria-label")) or ""

                addr_data = _parse_address(address)

                results.append({
                    "title": company,
                    "link": website,
                    "snippet": f"{address} {phone}",
                    "company_name": company,
                    "contact_name": "",
                    "contact_email": "",
                    "contact_phone": phone,
                    "website": website,
                    "location": address,
                    "city": addr_data.get("city", ""),
                    "state": addr_data.get("state", ""),
                    "postal_code": addr_data.get("postal_code", ""),
                    "search_rank": len(results) + 1,
                    "_source": "google_business",
                })
            except Exception as e:
                logger.debug("GBP listing parse error: %s", e)

        logger.info("Google business search '%s': %d listings", query[:50], len(results))
    except Exception as e:
        logger.warning("Google business search failed: %s", e)
    finally:
        await page.close()
        await context.close()
    return results


async def visit_website(url: str, timeout: int = 20000) -> dict:
    """Visit a business website, extract contact info, emails, phones."""
    result = {"contact_email": "", "contact_phone": "", "city": "", "state": "", "postal_code": ""}
    browser = await get_browser()
    page, context = await _stealth_page(browser)
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(2000)
        text = (await page.inner_text("body")) or ""

        emails = _extract_emails(text)
        business_emails = [e for e in emails if not e.startswith(("info@", "hello@", "contact@", "support@"))]
        if business_emails:
            result["contact_email"] = business_emails[0]
        elif emails:
            result["contact_email"] = emails[0]

        phones = _extract_phones(text)
        if phones:
            result["contact_phone"] = phones[0]

        addr = _parse_address(text[:3000])
        for k in ("city", "state", "postal_code"):
            result[k] = result.get(k) or addr.get(k, "")

        # Try to find contact/about page
        contact_links = []
        for a in await page.query_selector_all("a[href]"):
            href = (await a.get_attribute("href")) or ""
            link_text = ((await a.inner_text()) or "").lower().strip()
            if any(w in link_text for w in ("contact", "about", "team", "our-team", "find-us")):
                if href.startswith("/") or href.startswith(urlparse(url).netloc):
                    contact_links.append(urljoin(url, href))
                elif href.startswith("http"):
                    contact_links.append(href)

        # Visit first contact page found
        if contact_links:
            try:
                await page.goto(contact_links[0], wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(1500)
                contact_text = (await page.inner_text("body")) or ""
                c_emails = _extract_emails(contact_text)
                if c_emails and not result["contact_email"]:
                    result["contact_email"] = c_emails[0]
                c_phones = _extract_phones(contact_text)
                if c_phones and not result["contact_phone"]:
                    result["contact_phone"] = c_phones[0]
            except Exception:
                pass

    except Exception as e:
        logger.debug("Website visit failed %s: %s", url, e)
    finally:
        await page.close()
        await context.close()
    return result
