import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
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

def parse_prices(html):
    if not html:
        return {
            'Current_Price': None,
            'Minimum_Price': None,
            'Maximum_Price': None
        }

    soup = BeautifulSoup(html, "html.parser")
    result = {
        'Current_Price': None,
        'Minimum_Price': None,
        'Maximum_Price': None
    }

    divs = soup.select('div.row > div.col-md-4')
    for div in divs:
        label = div.find('h4')
        price_tag = div.find('p')
        if label and price_tag:
            text_label = label.get_text(strip=True)
            price_text = price_tag.get_text(strip=True)
            price_num = price_text.replace('₹', '').replace('/Quintal', '').replace('Rs', '').replace(',', '').strip()
            try:
                price_value = float(price_num)
                if price_value > 5500:
                    price_value = 0
            except:
                price_value = None

            if "Average Price" in text_label:
                result['Current_Price'] = price_value
            elif "Lowest Market Price" in text_label:
                result['Minimum_Price'] = price_value
            elif "Costliest Market Price" in text_label:
                result['Maximum_Price'] = price_value

    return result

async def scrape_all_states(progress_callback=None):
    all_prices = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        for state in states:
            if progress_callback:
                progress_callback(state)
            print(f"🔄 Scraping Online site → {state}", flush=True)

            html = None
            try:
                url = f"https://www.commodityonline.com/mandiprices/potato/{state}"
                await page.goto(url, timeout=10000)
                await page.wait_for_selector("div.mandi_highlight", timeout=10000)
                html = await page.inner_html("div.mandi_highlight")
            except:
                pass  # suppress error messages

            prices = parse_prices(html)
            prices["State"] = state
            avg = prices['Current_Price']
            min_ = prices['Minimum_Price']
            max_ = prices['Maximum_Price']
            print(f"   ↳ ₹{avg} / ₹{min_} / ₹{max_}", flush=True)
            all_prices.append(prices)

        await browser.close()

    return all_prices
