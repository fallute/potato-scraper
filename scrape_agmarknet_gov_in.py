import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

import asyncio
import json
import os
import random
import difflib
from collections import defaultdict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

states_required = [
    "andhra-pradesh", "assam", "bihar", "chandigarh", "chattisgarh",
    "delhi", "gujarat", "haryana", "himachal-pradesh", "jharkhand",
    "karnataka", "kerala", "madhya-pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
    "rajasthan", "tamil-nadu", "telangana", "tripura",
    "uttar-pradesh", "uttrakhand", "west-bengal"
]

import requests
print("🔎 Checking Tor IP...")
try:
    ip = requests.get("http://check.torproject.org/api/ip", proxies={
        'http': 'socks5h://127.0.0.1:9050',
        'https': 'socks5h://127.0.0.1:9050'
    }, timeout=10).json()
    print(f"✅ Tor IP: {ip['IP']} | IsTor: {ip['IsTor']}")
except Exception as e:
    print(f"❌ Tor check failed: {e}")


script_dir = os.path.dirname(__file__)
with open(os.path.join(script_dir, "data/Indian-states-districts.json"), "r", encoding="utf-8") as f:
    state_district_data = json.load(f)

district_to_state = {}
for entry in state_district_data:
    state = entry.get("name", "").strip()
    for district in entry.get("districts", []):
        district_lower = district.strip().lower()
        if district_lower:
            district_to_state[district_lower] = state

known_districts = list(district_to_state.keys())

def get_state_from_district(district_name):
    if not district_name:
        return "Unknown"
    name = district_name.strip().lower()

    # First try exact match
    if name in district_to_state:
        return district_to_state[name]

    # Then try fuzzy match if exact match fails
    match = difflib.get_close_matches(name, known_districts, n=1, cutoff=0.7)
    if match:
        return district_to_state[match[0]]

    return "Unknown"

async def scrape_all_states():
    print("Opening Agmarknet...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        for attempt in range(3):
            print(f"Navigating to Agmarknet (Attempt {attempt+1}/3)...")
            try:
                await page.goto("https://agmarknet.gov.in/", timeout=30000)
                print("Page loaded.")
                os.makedirs("debug", exist_ok=True)
                await page.screenshot(path="debug/debug_github.png", full_page=True)
            except PlaywrightTimeoutError:
                print("Timeout during page load.")

            try:
                for _ in range(10):
                    dropdown = page.locator("#ddlArrivalPrice")
                    if await dropdown.count() > 0:
                        print("Dropdown found.")
                        break
                    await asyncio.sleep(1)
                else:
                    raise Exception("Dropdown not found after 10 seconds.")
                break
            except Exception as e:
                print(f"Attempt {attempt+1}/3 failed: {e}")
                if attempt == 2:
                    await browser.close()
                    raise RuntimeError("Page loaded but dropdown not found after 3 attempts.")
                await asyncio.sleep(2)

        await asyncio.sleep(random.uniform(2, 3))
        if await page.input_value("#ddlArrivalPrice") != "0":
            await page.select_option("#ddlArrivalPrice", value="0")

        await asyncio.sleep(random.uniform(2, 3))
        if await page.input_value("#ddlCommodity") != "24":
            await page.select_option("#ddlCommodity", value="24")

        await asyncio.sleep(random.uniform(2, 3))
        await page.click("#btnGo")

        for attempt in range(3):
            try:
                await page.wait_for_selector("#cphBody_GridPriceData", timeout=20000)
                await asyncio.sleep(4)
                break
            except PlaywrightTimeoutError:
                print(f"Table wait failed (Attempt {attempt+1}/3)")
                if attempt < 2:
                    await page.click("#btnGo")
                    await asyncio.sleep(2)
                else:
                    await browser.close()
                    raise RuntimeError("Table did not load after 3 tries.")

        html = await page.inner_html("#cphBody_GridPriceData")
        await browser.close()

    soup = BeautifulSoup(html, "html.parser")
    headers = [th.text.strip() for th in soup.select("tr th")]
    data = []

    for row in soup.select("tr")[1:]:
        cols = [td.text.strip() for td in row.select("td")]
        if len(cols) == len(headers):
            row_data = dict(zip(headers, cols))
            district = row_data.get("District Name", row_data.get("District", "")).strip()
            state = get_state_from_district(district)
            if state == "Unknown":
                continue
            try:
                min_price = int(row_data.get("Min Price (Rs./Quintal)", "0"))
                max_price = int(row_data.get("Max Price (Rs./Quintal)", "0"))
                modal_price = int(row_data.get("Modal Price (Rs./Quintal)", "0"))
            except ValueError:
                continue

            data.append({
                "State": state.replace(" ", "-").lower(),
                "Minimum_Price": min_price,
                "Maximum_Price": max_price,
                "Current_Price": modal_price
            })

    if not data:
        raise RuntimeError("No valid price data found.")

    grouped = defaultdict(lambda: {"min": [], "max": [], "current": []})
    for row in data:
        if row["Minimum_Price"] > 0:
            grouped[row["State"]]["min"].append(row["Minimum_Price"])
        if row["Maximum_Price"] > 0:
            grouped[row["State"]]["max"].append(row["Maximum_Price"])
        if row["Current_Price"] > 0:
            grouped[row["State"]]["current"].append(row["Current_Price"])

    result = {}
    for state, prices in grouped.items():
        if prices["min"] and prices["max"] and prices["current"]:
            result[state] = {
                "Minimum_Price": sum(prices["min"]) // len(prices["min"]),
                "Maximum_Price": sum(prices["max"]) // len(prices["max"]),
                "Current_Price": sum(prices["current"]) // len(prices["current"]),
            }

    final_result = []
    extra_states = []

    result_keys = list(result.keys())
    for state in states_required:
        match = difflib.get_close_matches(state, result_keys, n=1, cutoff=0.8)
        if match:
            matched = match[0]
            final_result.append({
                "State": state,
                "Minimum_Price": result[matched]["Minimum_Price"],
                "Maximum_Price": result[matched]["Maximum_Price"],
                "Current_Price": result[matched]["Current_Price"],
            })
        else:
            final_result.append({
                "State": state,
                "Minimum_Price": 0,
                "Maximum_Price": 0,
                "Current_Price": 0,
            })

    for scraped in result_keys:
        match = difflib.get_close_matches(scraped, states_required, n=1, cutoff=0.8)
        if not match:
            final_result.append({
                "State": scraped,
                "Minimum_Price": result[scraped]["Minimum_Price"],
                "Maximum_Price": result[scraped]["Maximum_Price"],
                "Current_Price": result[scraped]["Current_Price"],
            })
            extra_states.append(scraped)

    if extra_states:
        print("Extra states detected (not in required list):")
        for s in sorted(extra_states):
            print("  -", s)

    final_result.sort(key=lambda x: x["State"])
    await asyncio.sleep(2)
    return final_result

if __name__ == "__main__":
    import time
    start = time.time()

    asyncio.run(scrape_all_states())

    duration = time.time() - start
    print(f"\n Finished scraping {len(results)} states.")
    print(f" Total execution time: {duration:.2f} seconds")

