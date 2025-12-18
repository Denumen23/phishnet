import asyncio
from playwright.async_api import async_playwright
import httpx

async def get_html(url: str) -> str:
    """
    Fetches the HTML content of a given URL asynchronously.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            print(f"Error fetching HTML for {url}: {e}")
            return ""

async def get_screenshot(url: str, filepath: str = "screenshot.png") -> None:
    """
    Takes a screenshot of a given URL and saves it to a file.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.screenshot(path=filepath)
            print(f"Screenshot saved to {filepath}")
        except Exception as e:
            print(f"Error taking screenshot for {url}: {e}")
        finally:
            await browser.close()

async def main():
    # Example usage
    test_url = "http://www.google.com"

    # Test HTML fetching
    html_content = await get_html(test_url)
    if html_content:
        print(f"Successfully fetched HTML from {test_url}")

    # Test screenshot
    await get_screenshot(test_url)

if __name__ == '__main__':
    asyncio.run(main())
