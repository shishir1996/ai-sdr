import re
import logging
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


BUSINESS_CATEGORIES = [
    "Automotive",
    "Beauty & Personal Care",
    "Business Services",
    "Construction & Contractors",
    "Education",
    "Entertainment & Recreation",
    "Finance & Insurance",
    "Food & Dining",
    "Health & Medical",
    "Home Services",
    "IT & Technology",
    "Legal Services",
    "Manufacturing",
    "Marketing & Advertising",
    "Media & Communications",
    "Real Estate",
    "Retail",
    "Shopping",
    "Sports & Fitness",
    "Transportation & Logistics",
    "Travel & Hospitality",
    "Other",
]


async def search_google_maps(query: str, location: str, api_key: str = "") -> list[dict]:
    if api_key:
        try:
            from app.services.lead_extraction.google_places import search_places
            results = await search_places(query, location, api_key)
            if results:
                return results
        except Exception as e:
            logger.warning("Google Places API failed, falling back to Playwright: %s", e)

    if not HAS_PLAYWRIGHT:
        logger.error("Playwright not available for Google Maps scraping")
        return []

    search_term = quote(f"{query} in {location}")
    url = f"https://www.google.com/maps/search/{search_term}/"

    businesses = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)

            scrollable = page.locator('div[role="feed"]')
            if await scrollable.count() > 0:
                for _ in range(3):
                    await scrollable.evaluate("el => el.scrollBy(0, el.scrollHeight)")
                    await page.wait_for_timeout(2000)

            cards = page.locator('a[href*="/maps/place/"]')
            count = await cards.count()
            seen_names = set()

            for i in range(min(count, 20)):
                try:
                    card = cards.nth(i)
                    card_text = await card.inner_text()
                    card_html = await card.inner_html()

                    lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                    name = lines[0] if lines else ""
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)

                    rating = ""
                    reviews = ""
                    address = ""
                    category = ""
                    phone = ""
                    website = ""
                    hours = ""

                    for j, line in enumerate(lines[1:], 1):
                        if re.match(r"^\d+(\.\d+)?$", line) and j < len(lines):
                            rating = line
                            if j + 1 < len(lines) and "reviews" in lines[j + 1].lower():
                                reviews = lines[j + 1].split(" ")[0]
                        elif re.match(r".+\d{3,}", line) and not phone:
                            if any(c.isdigit() for c in line) and len(line) > 6:
                                phone = line
                        elif re.match(r"^[A-Za-z].*,\s*[A-Z]{2}", line) and not address:
                            address = line

                    href = await card.get_attribute("href") or ""
                    place_id = ""
                    if "place/" in href:
                        place_id_match = re.search(r"place/([^/]+)", href)
                        if place_id_match:
                            place_id = place_id_match.group(1)

                    soup = BeautifulSoup(card_html, "lxml")
                    for tag in soup.find_all(class_=re.compile(r"category|type|tag|kind")):
                        category = _clean(tag.get_text(strip=True))
                        break

                    businesses.append({
                        "name": name,
                        "rating": rating,
                        "reviews": reviews,
                        "address": address,
                        "phone": phone,
                        "category": category,
                        "website": website,
                        "place_id": place_id,
                        "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else href,
                        "source": "google_business",
                    })
                except Exception as e:
                    logger.debug(f"Error parsing card {i}: {e}")
                    continue

            await browser.close()
    except Exception as e:
        logger.error(f"Google Maps scraping failed: {e}")

    if not businesses and HAS_PLAYWRIGHT:
        logger.info("Google Maps returned no results - likely blocked by anti-bot protection")

    return businesses
