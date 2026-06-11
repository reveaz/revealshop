import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        try:
            await page.goto("https://kurs.kz/index.php?mode=almaty", wait_until="domcontentloaded", timeout=30000)
            text = await page.content()
            with open("kurs_debug.html", "w", encoding="utf-8") as f:
                f.write(text)
            print("Saved kurs_debug.html")
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
