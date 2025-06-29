import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import asyncio
from playwright.async_api import async_playwright
import re
import nest_asyncio

nest_asyncio.apply()

states = [
    "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chattisgarh",
    "delhi", "gujarat", "haryana", "himachal-pradesh", "jharkhand",
    "karnataka", "kerala", "madhya-pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "sikkim", "tamil-nadu", "telangana", "tripura",
    "uttar-pradesh", "uttrakhand", "west-bengal"
]

async def scrape_state_price(page, state):
    url_state = "nct-of-delhi" if state == "delhi" else state
    url = f"https://www.commoditymarketlive.com/mandi-price-state/{url_state}/potato"
    try:
        await page.goto(url, timeout=20000)
        await page.wait_for_selector("table.pricesummarytable", timeout=10000)
        rows = await page.query_selector_all("table.pricesummarytable tbody tr")
        prices = {}
        for row in rows:
            cols = await row.query_selector_all("td")
            if len(cols) < 2:
                continue
            label = (await cols[0].inner_text()).strip()
            value = (await cols[1].inner_text()).strip()
            match = re.search(r"₹\s*([\d,\.]+)", value)
            price_value = float(match.group(1).replace(',', '')) if match else None
            if price_value is not None and price_value > 5500:
                price_value = 0
            prices[label] = price_value
        return {
            "State": state,
            "Current_Price": prices.get("Average Market Price:"),
            "Minimum_Price": prices.get("Minimum Market Price:"),
            "Maximum_Price": prices.get("Maximum Market Price:")
        }
    except:
        return {
            "State": state,
            "Current_Price": None,
            "Minimum_Price": None,
            "Maximum_Price": None
        }

async def scrape_all_states(progress_callback=None):
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for state in states:
            if progress_callback:
                progress_callback(state)
            print(f"Scraping Live site : {state}", flush=True)
            result = await scrape_state_price(page, state)
            # Modified line below (changed ₹ to numeric-only)
            print(f"   {result['Current_Price'] or 0} / {result['Minimum_Price'] or 0} / {result['Maximum_Price'] or 0}", flush=True)
            results.append(result)
        await browser.close()
    return results

# To run the script
if __name__ == "__main__":
    asyncio.run(scrape_all_states())
