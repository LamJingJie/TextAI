from playwright.async_api import async_playwright, Page, BrowserContext, ElementHandle, Browser

async def get_page_data_playwright(url: str, target: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
        )

        await close(context, browser)


async def get_all_pages_playwright(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
        )
        
        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_selector('.tlui-popover')
        await page.click('.tlui-button__menu')
        dropdown_menu = await page.query_selector('.tlui-page-menu__list')
        page_list = await dropdown_menu.inner_text()
        await close(context, browser)
        return page_list.lower().split("\n")
    

async def close(context: BrowserContext, browser: Browser):
    await context.close()
    await browser.close()