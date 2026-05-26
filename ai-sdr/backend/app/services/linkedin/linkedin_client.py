import os
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"

COOKIE_FILE_TEMPLATE = "/tmp/linkedin_cookies_{hash}.json"


def _get_cookie_path(identifier: str) -> str:
    return COOKIE_FILE_TEMPLATE.format(hash=hash(identifier))


def _save_cookies(page, identifier: str):
    cookies = page.context.cookies()
    path = _get_cookie_path(identifier)
    with open(path, "w") as f:
        json.dump(cookies, f)
    logger.info(f"Saved {len(cookies)} LinkedIn cookies to {path}")


def _load_cookies(page, identifier: str) -> bool:
    path = _get_cookie_path(identifier)
    if not os.path.exists(path):
        return False
    with open(path) as f:
        cookies = json.load(f)
    page.context.add_cookies(cookies)
    logger.info(f"Loaded {len(cookies)} LinkedIn cookies")
    return True


async def login_and_save_cookies(
    email: str,
    password: str,
    headless: bool = True,
) -> bool:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(f"{LINKEDIN_BASE}/login", wait_until="networkidle")
            await page.fill("#username", email)
            await page.fill("#password", password)
            await page.click("button[type=submit]")
            await page.wait_for_timeout(5000)

            if "feed" in page.url or "checkpoint" in page.url:
                _save_cookies(page, email)
                return True
            else:
                logger.warning(f"LinkedIn login failed. URL: {page.url}")
                return False
        except Exception as e:
            logger.error(f"LinkedIn login error: {e}")
            return False
        finally:
            await browser.close()


async def _get_authenticated_page(headless: bool = True):
    from playwright.async_api import async_playwright

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=headless)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    return p, browser, context, page


async def _ensure_authenticated(page, email: str) -> bool:
    loaded = _load_cookies(page, email)
    if loaded:
        await page.goto(f"{LINKEDIN_BASE}/feed", wait_until="networkidle", timeout=30000)
        return "feed" in page.url or "checkpoint" in page.url
    return False


async def send_connection_request(
    linkedin_url: str,
    email: str,
    password: str,
    message: Optional[str] = None,
    headless: bool = True,
) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            authenticated = await _ensure_authenticated(page, email)
            if not authenticated:
                await page.goto(f"{LINKEDIN_BASE}/login", wait_until="networkidle")
                await page.fill("#username", email)
                await page.fill("#password", password)
                await page.click("button[type=submit]")
                await page.wait_for_timeout(5000)
                _save_cookies(page, email)

            await page.goto(linkedin_url, wait_until="networkidle", timeout=30000)

            connect_button = page.locator("button[aria-label*='Connect']").first
            if await connect_button.count() == 0:
                more_button = page.locator("button[aria-label*='More']").first
                if await more_button.count() > 0:
                    await more_button.click()
                    await page.wait_for_timeout(1000)
                    connect_button = page.locator("button[aria-label*='Connect']").first

            if await connect_button.count() > 0:
                await connect_button.click()
                await page.wait_for_timeout(1500)

                if message:
                    add_note = page.locator("button[aria-label*='Add a note']").first
                    if await add_note.count() > 0:
                        await add_note.click()
                        await page.wait_for_timeout(500)
                        textarea = page.locator("textarea#custom-message").first
                        if await textarea.count() > 0:
                            await textarea.fill(message[:300])

                    send_now = page.locator("button[aria-label*='Send now']").first
                    if await send_now.count() > 0:
                        await send_now.click()
                        await page.wait_for_timeout(2000)
                        return {"status": "sent", "type": "connection_request", "with_message": bool(message)}

                send_button = page.locator("button[aria-label*='Send']").first
                if await send_button.count() > 0:
                    await send_button.click()
                    await page.wait_for_timeout(2000)
                    return {"status": "sent", "type": "connection_request", "with_message": bool(message)}

            return {"status": "failed", "reason": "Connect button not found"}
        except Exception as e:
            logger.error(f"LinkedIn connection request error: {e}")
            return {"status": "error", "reason": str(e)}
        finally:
            await browser.close()


async def send_dm(
    linkedin_url: str,
    email: str,
    password: str,
    message: str,
    headless: bool = True,
) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            authenticated = await _ensure_authenticated(page, email)
            if not authenticated:
                await page.goto(f"{LINKEDIN_BASE}/login", wait_until="networkidle")
                await page.fill("#username", email)
                await page.fill("#password", password)
                await page.click("button[type=submit]")
                await page.wait_for_timeout(5000)
                _save_cookies(page, email)

            await page.goto(linkedin_url, wait_until="networkidle", timeout=30000)

            message_button = page.locator("button[aria-label*='Message']").first
            if await message_button.count() == 0:
                more_button = page.locator("button[aria-label*='More']").first
                if await more_button.count() > 0:
                    await more_button.click()
                    await page.wait_for_timeout(1000)
                    message_button = page.locator("button[aria-label*='Message']").first

            if await message_button.count() > 0:
                await message_button.click()
                await page.wait_for_timeout(2000)

                msg_box = page.locator("div[role='textbox'][aria-label*='message']").first
                if await msg_box.count() == 0:
                    msg_box = page.locator("div.msg-form__contenteditable").first

                if await msg_box.count() > 0:
                    await msg_box.click()
                    await msg_box.fill(message)
                    await page.wait_for_timeout(500)

                    send_button = page.locator("button[aria-label*='Send']").first
                    if await send_button.count() == 0:
                        send_button = page.locator("button.msg-form__send-button").first

                    if await send_button.count() > 0:
                        await send_button.click()
                        await page.wait_for_timeout(2000)
                        return {"status": "sent", "type": "dm"}
                    else:
                        await page.keyboard.press("Enter")
                        await page.wait_for_timeout(2000)
                        return {"status": "sent", "type": "dm", "method": "keyboard"}

            return {"status": "failed", "reason": "Message button not found"}
        except Exception as e:
            logger.error(f"LinkedIn DM error: {e}")
            return {"status": "error", "reason": str(e)}
        finally:
            await browser.close()


async def like_post(
    post_url: str,
    email: str,
    password: str,
    headless: bool = True,
) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            authenticated = await _ensure_authenticated(page, email)
            if not authenticated:
                await page.goto(f"{LINKEDIN_BASE}/login", wait_until="networkidle")
                await page.fill("#username", email)
                await page.fill("#password", password)
                await page.click("button[type=submit]")
                await page.wait_for_timeout(5000)
                _save_cookies(page, email)

            await page.goto(post_url, wait_until="networkidle", timeout=30000)

            like_button = page.locator("button[aria-label*='Like']").first
            if await like_button.count() > 0:
                await like_button.click()
                await page.wait_for_timeout(2000)
                return {"status": "liked", "type": "like"}

            return {"status": "failed", "reason": "Like button not found"}
        except Exception as e:
            logger.error(f"LinkedIn like error: {e}")
            return {"status": "error", "reason": str(e)}
        finally:
            await browser.close()


async def comment_on_post(
    post_url: str,
    email: str,
    password: str,
    comment_text: str,
    headless: bool = True,
) -> dict:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            authenticated = await _ensure_authenticated(page, email)
            if not authenticated:
                await page.goto(f"{LINKEDIN_BASE}/login", wait_until="networkidle")
                await page.fill("#username", email)
                await page.fill("#password", password)
                await page.click("button[type=submit]")
                await page.wait_for_timeout(5000)
                _save_cookies(page, email)

            await page.goto(post_url, wait_until="networkidle", timeout=30000)

            comment_box = page.locator("div[aria-label*='Comment']").first
            if await comment_box.count() == 0:
                comment_box = page.locator("div[role='textbox'][aria-label*='comment']").first

            if await comment_box.count() > 0:
                await comment_box.click()
                await page.wait_for_timeout(500)
                await comment_box.fill(comment_text)
                await page.wait_for_timeout(500)

                post_button = page.locator("button[aria-label*='Post']").first
                if await post_button.count() > 0:
                    await post_button.click()
                    await page.wait_for_timeout(2000)
                    return {"status": "commented", "type": "comment"}

            return {"status": "failed", "reason": "Comment box not found"}
        except Exception as e:
            logger.error(f"LinkedIn comment error: {e}")
            return {"status": "error", "reason": str(e)}
        finally:
            await browser.close()
