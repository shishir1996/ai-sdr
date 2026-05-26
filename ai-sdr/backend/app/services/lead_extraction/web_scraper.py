import httpx
import re
import json
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Optional

from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)

COMMON_PATHS = ["", "/about", "/about-us", "/contact", "/contact-us", "/team", "/our-team", "/people", "/company"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
)
SOCIAL_RE = re.compile(
    r"https?://(?:www\.)?(linkedin\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|github\.com)/[a-zA-Z0-9_.\-/]+"
)

DIRECTORY_SITES = {
    "indiamart.com": "indiamart",
    "justdial.com": "justdial",
    "tradeindia.com": "tradeindia",
    "industrybuying.com": "industrybuying",
    "m.indiamart.com": "indiamart",
    "yellowpages.com": "yellowpages",
    "yellowpages.ca": "yellowpages",
    "manta.com": "manta",
    "hotfrog.com": "hotfrog",
    "kompass.com": "kompass",
    "europages.com": "europages",
}

COUNTRY_PHONE_PREFIXES = {
    "india": "+91",
    "united states": "+1",
    "united kingdom": "+44",
    "australia": "+61",
    "canada": "+1",
    "germany": "+49",
    "france": "+33",
    "singapore": "+65",
    "uae": "+971",
    "brazil": "+55",
    "japan": "+81",
    "china": "+86",
}


async def _fetch(url: str, client: httpx.AsyncClient) -> Optional[BeautifulSoup]:
    try:
        resp = await client.get(url, timeout=20.0, follow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return None


async def _fetch_dynamic(url: str) -> Optional[BeautifulSoup]:
    if not HAS_PLAYWRIGHT:
        logger.debug("Playwright not available, skipping dynamic fetch")
        return None
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            content = await page.content()
            await browser.close()
            return BeautifulSoup(content, "lxml")
    except Exception as e:
        logger.debug(f"Failed dynamic fetch {url}: {e}")
        return None


def _extract_meta(soup: BeautifulSoup, key: str) -> str:
    for tag in soup.find_all("meta"):
        if tag.get("name", "").lower() == key or tag.get("property", "").lower() == key:
            return tag.get("content", "")
    return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _detect_directory_type(url: str) -> Optional[str]:
    for domain, dir_type in DIRECTORY_SITES.items():
        if domain in url.lower():
            return dir_type
    return None


def _get_country_phone_prefix(country: str) -> str:
    return COUNTRY_PHONE_PREFIXES.get(country.lower().strip(), "")


async def _scrape_directory_listing(url: str, soup: BeautifulSoup, client: httpx.AsyncClient, country: str = "", dynamic: bool = False) -> list[dict]:
    dir_type = _detect_directory_type(url)
    if not dir_type:
        return []

    leads = []
    domain = urlparse(url).netloc.lower()

    if "indiamart" in domain:
        for card in soup.find_all("div", class_=re.compile(r"card|list|item|result|product")):
            name_el = card.find(["h2", "h3", "h4", "a", "strong"])
            name = _clean(name_el.get_text(strip=True)) if name_el else ""

            link_el = card.find("a", href=True)
            profile_url = urljoin(url, link_el["href"]) if link_el else ""

            contact_el = card.find("span", class_=re.compile(r"contact|phone|mobile|call"))
            phone = _clean(contact_el.get_text(strip=True)) if contact_el else ""

            email_el = card.find("a", href=re.compile(r"mailto:"))
            email = email_el["href"].replace("mailto:", "") if email_el else ""

            address_el = card.find(["p", "span", "div"], class_=re.compile(r"address|location|place"))
            address = _clean(address_el.get_text(strip=True)) if address_el else ""

            if name and not any(existing.get("name") == name for existing in leads):
                leads.append({
                    "name": name,
                    "company": name,
                    "email": email,
                    "phone": phone,
                    "location": address,
                    "website": profile_url,
                    "source_url": url,
                    "directory": "IndiaMart",
                })

    elif "justdial" in domain:
        for card in soup.find_all("section", class_=re.compile(r"result|card|listing|item|jcard")):
            name_el = card.find(["h2", "h3", "h4", "a", "span"], class_=re.compile(r"name|title|store"))
            name = _clean(name_el.get_text(strip=True)) if name_el else ""

            phone_el = card.find(["a", "span"], class_=re.compile(r"call|phone|mobile|contact"))
            phone = _clean(phone_el.get_text(strip=True)) if phone_el else ""
            if phone.startswith("tel:"):
                phone = phone.replace("tel:", "")

            rating_el = card.find(class_=re.compile(r"rating|star|rate"))
            rating = _clean(rating_el.get_text(strip=True)) if rating_el else ""

            address_el = card.find(["span", "p", "div"], class_=re.compile(r"address|location|add"))
            address = _clean(address_el.get_text(strip=True)) if address_el else ""

            link_el = card.find("a", href=True)
            profile_url = urljoin(url, link_el["href"]) if link_el else ""

            if name and not any(existing.get("name") == name for existing in leads):
                leads.append({
                    "name": name,
                    "company": name,
                    "email": "",
                    "phone": phone,
                    "location": address,
                    "website": profile_url,
                    "source_url": url,
                    "directory": "JustDial",
                    "rating": rating,
                })

    elif "yellowpages" in domain:
        selectors = ["div.result", "div.listing", "div.card", "div.business", "div.info", "div.v-card", "div.search-result"]
        cards = []
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                break

        if not cards:
            for cls in ["result", "listing", "card", "business", "info", "v-card", "search-result", "organic"]:
                cards = soup.find_all("div", class_=re.compile(cls))
                if cards:
                    break

        for card in cards:
            name_el = card.find(["a", "h2", "h3", "h4", "span", "strong"], class_=re.compile(r"name|title|business|org|company"))
            if not name_el:
                name_el = card.find(["a", "h2", "h3", "h4", "span", "strong"])
            name = _clean(name_el.get_text(strip=True)) if name_el else ""

            phone_el = card.find(["a", "span"], class_=re.compile(r"phone|call|contact|num"))
            if not phone_el:
                phone_el = card.find("a", href=re.compile(r"tel:"))
            phone = _clean(phone_el.get_text(strip=True)) if phone_el else ""
            if phone.startswith("tel:"):
                phone = phone.replace("tel:", "")

            email_el = card.find("a", href=re.compile(r"mailto:"))
            email = email_el["href"].replace("mailto:", "") if email_el else ""

            website_el = card.find(["a", "span"], class_=re.compile(r"website|visit|link|url|site"))
            website = website_el["href"] if website_el and website_el.get("href") else ""
            if website_el and not website:
                website = _clean(website_el.get_text(strip=True))

            address_el = card.find(["p", "span", "div", "small"], class_=re.compile(r"address|location|street|city|zip"))
            address = _clean(address_el.get_text(strip=True)) if address_el else ""

            rating_el = card.find(class_=re.compile(r"rating|star|stars"))
            rating = _clean(rating_el.get_text(strip=True)) if rating_el else ""

            category_el = card.find(class_=re.compile(r"category|tag|type|industry"))
            category = _clean(category_el.get_text(strip=True)) if category_el else ""

            if name and len(name) > 1 and not any(existing.get("name") == name for existing in leads):
                leads.append({
                    "name": name,
                    "company": name,
                    "email": email,
                    "phone": phone,
                    "location": address,
                    "website": website,
                    "source_url": url,
                    "directory": "YellowPages",
                    "rating": rating,
                    "category": category,
                })

    elif "manta" in domain:
        for card in soup.find_all("div", class_=re.compile(r"result|card|listing|item|company")):
            name_el = card.find(["a", "h2", "h3", "h4"], class_=re.compile(r"name|title|company"))
            name = _clean(name_el.get_text(strip=True)) if name_el else ""

            phone_el = card.find(class_=re.compile(r"phone|call|contact"))
            phone = _clean(phone_el.get_text(strip=True)) if phone_el else ""

            if name and not any(existing.get("name") == name for existing in leads):
                leads.append({
                    "name": name,
                    "company": name,
                    "email": "",
                    "phone": phone,
                    "location": "",
                    "website": "",
                    "source_url": url,
                    "directory": "Manta",
                })

    else:
        text = soup.get_text(separator=" ", strip=True)
        emails = list(set(EMAIL_RE.findall(text)))
        phones = list(set(PHONE_RE.findall(text)))
        if emails or phones:
            title_tag = soup.find("title")
            site_name = _clean(title_tag.get_text(strip=True)) if title_tag else domain
            leads.append({
                "name": site_name,
                "company": site_name,
                "email": emails[0] if emails else "",
                "phone": phones[0] if phones else "",
                "location": "",
                "website": url,
                "source_url": url,
                "directory": "Directory",
            })

    return leads


async def deep_scrape_domain(base_url: str, country: str = "") -> dict:
    parsed = urlparse(base_url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    scheme = parsed.scheme or "https"
    base = f"{scheme}://{domain}"

    dir_type = _detect_directory_type(base_url)
    country_prefix = _get_country_phone_prefix(country)

    result = {
        "company": "",
        "domain": domain,
        "emails": [],
        "phones": [],
        "social_links": [],
        "description": "",
        "industry": "",
        "location": "",
        "founders": [],
        "team_members": [],
        "business_emails": [],
        "pages_scraped": 0,
        "directory_leads": [],
        "is_directory": dir_type is not None,
        "country": country,
    }

    async with httpx.AsyncClient(verify=False, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}) as client:
        soup = await _fetch(base_url, client)

        result["pages_scraped"] = 1

        if dir_type:
            directory_leads = []
            if soup:
                directory_leads = await _scrape_directory_listing(base_url, soup, client, country)

            if not directory_leads and HAS_PLAYWRIGHT:
                dyn_soup = await _fetch_dynamic(base_url)
                if dyn_soup:
                    result["pages_scraped"] += 1
                    directory_leads = await _scrape_directory_listing(base_url, dyn_soup, client, country, dynamic=True)

            result["directory_leads"] = directory_leads
            if not soup:
                soup = dyn_soup or None
            if soup:
                title_tag = soup.find("title")
                if title_tag:
                    result["company"] = _clean(title_tag.get_text(strip=True))

            ll = result["directory_leads"]
            for dl in ll:
                if dl.get("email"):
                    result["emails"].append(dl["email"])
                if dl.get("phone"):
                    result["phones"].append(dl["phone"])

            result["emails"] = list(set(result["emails"]))
            result["phones"] = list(set(result["phones"]))
            return result

        if soup is None:
            return result

        common_paths = COMMON_PATHS[:]
        for path in common_paths:
            url = urljoin(base, path)
            psoup = await _fetch(url, client)
            if psoup is None:
                continue
            result["pages_scraped"] += 1

            title = psoup.find("title")
            if title and not result["company"]:
                t = title.text.strip()
                for sep in [" | ", " - ", " — ", " – ", " :: "]:
                    parts = t.split(sep)
                    if len(parts) > 1:
                        result["company"] = parts[0].strip()
                        break
                if not result["company"]:
                    result["company"] = t

            if not result["description"]:
                desc = _extract_meta(psoup, "description") or _extract_meta(psoup, "og:description")
                if desc:
                    result["description"] = _clean(desc)

            if not result["industry"]:
                industry = _extract_meta(psoup, "industry") or _extract_meta(psoup, "business:industry")
                if industry:
                    result["industry"] = industry

            text = psoup.get_text(separator=" ", strip=True)

            for m in EMAIL_RE.finditer(text):
                email = m.group().lower()
                if email not in result["emails"]:
                    result["emails"].append(email)

            for m in PHONE_RE.finditer(text):
                phone = m.group().strip()
                if len(phone) >= 7 and phone not in result["phones"]:
                    if country_prefix and not phone.startswith("+"):
                        pass
                    result["phones"].append(phone)

            for a in psoup.find_all("a", href=True):
                href = a["href"]
                full = urljoin(url, href)
                sm = SOCIAL_RE.search(full)
                if sm and full not in result["social_links"]:
                    result["social_links"].append(full)

            if "contact" in path.lower():
                addr_patterns = [
                    r"\d+\s+[A-Za-z\s,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Circle|Cir)[,\s]+[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}",
                    r"(?:Address|Location|Office)[:\s]+(.+?)(?:\.|$)",
                    r"(?:Suite|Ste|Unit)\s+\d+[,\s]+[A-Za-z\s]+,[,\s]+[A-Z]{2}\s*\d{5}",
                ]
                for pat in addr_patterns:
                    m = re.search(pat, text, re.IGNORECASE)
                    if m:
                        result["location"] = _clean(m.group())
                        break

            if any(kw in path.lower() for kw in ["team", "people", "about", "founder"]):
                for tag in psoup.find_all(["h2", "h3", "h4", "span", "p", "div"]):
                    name = _clean(tag.get_text(strip=True))
                    if len(name.split()) >= 2 and len(name) < 60:
                        title_tag = tag.find_next(["p", "span", "div", "small"])
                        role = _clean(title_tag.get_text(strip=True)) if title_tag else ""
                        is_team = any(
                            kw in role.lower()
                            for kw in ["founder", "ceo", "cto", "vp", "director", "engineer", "manager", "lead", "head of", "president", "co-founder", "chief"]
                        ) if role else False
                        if is_team or "founder" in name.lower() or "team" in path.lower():
                            entry = {"name": name, "role": role}
                            if entry not in result["team_members"]:
                                result["team_members"].append(entry)

    result["emails"] = list(set(result["emails"]))
    result["phones"] = list(set(result["phones"]))

    generic_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "protonmail.com"}
    result["business_emails"] = [e for e in result["emails"] if e.split("@")[-1] not in generic_domains and e.split("@")[-1] != domain]
    result["business_emails"] = list(set(result["business_emails"]))

    return result


BOT_BLOCK_PATTERNS = [
    "cloudflare", "attention required", "just a moment", "checking your browser",
    "verify you are human", "ddos protection", "blocked", "access denied",
    "please enable javascript", "403 forbidden",
]


def _is_bot_blocked(data: dict) -> bool:
    company = (data.get("company") or "").lower()
    desc = (data.get("description") or "").lower()
    text = company + " " + desc
    for pat in BOT_BLOCK_PATTERNS:
        if pat in text:
            return True
    if not data.get("emails") and not data.get("phones") and not data.get("team_members") and not data.get("directory_leads"):
        if company and any(pat in company for pat in ["cloudflare", "attention", "blocked", "forbidden", "access denied"]):
            return True
    return False


async def scrape_and_create_lead(url: str, country: str = "") -> dict:
    data = await deep_scrape_domain(url, country=country)

    if _is_bot_blocked(data):
        return {
            "company": "",
            "first_name": "",
            "last_name": "",
            "title": "",
            "email": "",
            "phone": "",
            "website": f"https://{data['domain']}",
            "linkedin_url": "",
            "location": "",
            "industry": "",
            "source": "web_scrape",
            "notes": "",
            "_blocked": True,
            "_reason": "Website blocked the scraper (Cloudflare/bot protection). Try a different URL or use a company website instead of a directory homepage.",
        }

    if data["is_directory"]:
        if data["directory_leads"]:
            first = data["directory_leads"][0]
            return {
                "company": first.get("company") or data["company"] or "",
                "first_name": first.get("name", "").split(" ")[0] if first.get("name") else "",
                "last_name": " ".join(first.get("name", "").split(" ")[1:]) if first.get("name") and len(first.get("name", "").split(" ")) > 1 else "",
                "title": "",
                "email": first.get("email", ""),
                "phone": first.get("phone", ""),
                "website": first.get("website", "") or f"https://{data['domain']}",
                "linkedin_url": "",
                "location": first.get("location", ""),
                "industry": data.get("industry", ""),
                "source": f"directory_{data.get('country', '').lower() or 'unknown'}",
                "notes": f"Imported from {first.get('directory', 'directory')} | Source URL: {url} | Country: {data.get('country', '')}",
            }
        return {
            "company": data.get("company") or "",
            "first_name": "",
            "last_name": "",
            "title": "",
            "email": "",
            "phone": "",
            "website": f"https://{data['domain']}",
            "linkedin_url": "",
            "location": "",
            "industry": "",
            "source": f"directory_{data.get('country', '').lower() or 'unknown'}",
            "notes": f"No leads found on directory page. URL: {url} | Country: {data.get('country', '')}",
        }

    email = ""
    if data["business_emails"]:
        email = data["business_emails"][0]
    elif data["emails"]:
        email = data["emails"][0]

    phone = data["phones"][0] if data["phones"] else ""

    contact_name = ""
    contact_title = ""
    for member in data["team_members"]:
        if any(kw in (member["role"] or "").lower() for kw in ["founder", "ceo", "president", "owner", "director"]):
            contact_name = member["name"]
            contact_title = member["role"]
            break
    if not contact_name and data["team_members"]:
        contact_name = data["team_members"][0]["name"]
        contact_title = data["team_members"][0]["role"]

    first_name = contact_name.split(" ")[0] if contact_name else ""
    last_name = " ".join(contact_name.split(" ")[1:]) if contact_name and len(contact_name.split(" ")) > 1 else ""

    linkedin_url = ""
    for link in data["social_links"]:
        if "linkedin.com" in link:
            linkedin_url = link
            break

    notes_parts = []
    if data["description"]:
        notes_parts.append(data["description"][:500])
    if country:
        notes_parts.append(f"Country: {country}")
    notes = " | ".join(notes_parts) if notes_parts else ""

    return {
        "company": data["company"] or "",
        "first_name": first_name,
        "last_name": last_name,
        "title": contact_title,
        "email": email,
        "phone": phone,
        "website": f"https://{data['domain']}",
        "linkedin_url": linkedin_url,
        "location": data["location"],
        "industry": data["industry"],
        "source": "web_scrape",
        "notes": notes[:500] if notes else "",
    }
