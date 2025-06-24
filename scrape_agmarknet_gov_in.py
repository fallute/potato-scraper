import asyncio
import json
import os
import random
import difflib
from collections import defaultdict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# 🔄 Load district-state mapping from JSON file
script_dir = os.path.dirname(__file__)
with open("data/Indian-states-districts.json", "r", encoding="utf-8") as f:
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
    if name in district_to_state:
        return district_to_state[name]
    match = difflib.get_close_matches(name, known_districts, n=1, cutoff=0.8)
    if match:
        return district_to_state[match[0]]
    return "Unknown"

async def scrape_all_states():
    print("🌐 Opening Agmarknet...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for attempt in range(3):
            print(f"🧭 Navigating to Agmarknet (Attempt {attempt+1}/3)...")
            try:
                await page.goto("https://agmarknet.gov.in/", timeout=30000, wait_until="load")
                print("🌐 Page loaded.")
            except PlaywrightTimeoutError:
                print("⚠️ Timeout. Will still check dropdown...")

            try:
                dropdown = page.locator("#ddlArrivalPrice")
                if await dropdown.count() > 0:
                    print("✅ Dropdown found.")
                    break
                else:
                    raise Exception("Dropdown not found")
            except Exception as e:
                print(f"❌ Attempt {attempt+1}/3 failed: {e}")
                if attempt == 2:
                    await browser.close()
                    raise RuntimeError("❌ Page or dropdown failed after 3 attempts.")
                await asyncio.sleep(3)

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
                print(f"⚠️ Table wait failed (Attempt {attempt+1}/3)")
                if attempt < 2:
                    await page.click("#btnGo")
                    await asyncio.sleep(2)
                else:
                    await browser.close()
                    raise RuntimeError("❌ Table did not load after 3 tries.")

        html = await page.inner_html("#cphBody_GridPriceData")
        await browser.close()

    print("🧪 Parsing table...")
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
                "State": state,
                "Minimum_Price": min_price,
                "Maximum_Price": max_price,
                "Current_Price": modal_price
            })

    if not data:
        raise RuntimeError("❌ No valid price data found.")

    print("📊 Grouping and averaging by state (excluding zeros)...")
    grouped = defaultdict(lambda: {"min": [], "max": [], "current": []})

    for row in data:
        if row["Minimum_Price"] > 0:
            grouped[row["State"]]["min"].append(row["Minimum_Price"])
        if row["Maximum_Price"] > 0:
            grouped[row["State"]]["max"].append(row["Maximum_Price"])
        if row["Current_Price"] > 0:
            grouped[row["State"]]["current"].append(row["Current_Price"])

    # 🎯 Final list of known states
    given_states = [
        "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chattisgarh",
        "delhi", "gujarat", "haryana", "himachal-pradesh", "jharkhand",
        "karnataka", "kerala", "madhya-pradesh", "maharashtra", "manipur",
        "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
        "rajasthan", "sikkim", "tamil-nadu", "telangana", "tripura",
        "uttar-pradesh", "uttrakhand", "west-bengal"
    ]

    result = []
    normalized_scraped_states = {
        s.lower().replace(" ", "-"): s for s in grouped.keys()
    }

    matched_states = set()

    # ✅ Include all given states
    for given in given_states:
        match = difflib.get_close_matches(given, normalized_scraped_states.keys(), n=1, cutoff=0.8)
        if match:
            scraped_name = normalized_scraped_states[match[0]]
            matched_states.add(scraped_name)
            prices = grouped[scraped_name]
            result.append({
                "State": given,
                "Minimum_Price": sum(prices["min"]) // len(prices["min"]) if prices["min"] else 0,
                "Maximum_Price": sum(prices["max"]) // len(prices["max"]) if prices["max"] else 0,
                "Current_Price": sum(prices["current"]) // len(prices["current"]) if prices["current"] else 0,
            })
        else:
            result.append({
                "State": given,
                "Minimum_Price": 0,
                "Maximum_Price": 0,
                "Current_Price": 0
            })

    # ✅ Add extra unmatched states
    for state in grouped:
        if state not in matched_states:
            prices = grouped[state]
            result.append({
                "State": state.replace(" ", "-").lower(),
                "Minimum_Price": sum(prices["min"]) // len(prices["min"]) if prices["min"] else 0,
                "Maximum_Price": sum(prices["max"]) // len(prices["max"]) if prices["max"] else 0,
                "Current_Price": sum(prices["current"]) // len(prices["current"]) if prices["current"] else 0,
            })

    # 🔍 Print extra states that were not in the given list
    print("\n🆕 Extra states included (not in your list):")
    extra_states = []
    for state in grouped:
        normalized = state.lower().replace(" ", "-")
        match = difflib.get_close_matches(normalized, given_states, n=1, cutoff=0.8)
        if not match:
           extra_states.append(normalized)

    if extra_states:
       for s in sorted(extra_states):
        print("•", s)
    else:
         print("✅ No extra states found.")

    await asyncio.sleep(2)
    print("✅ Done.")
    return result

if __name__ == "__main__":
    asyncio.run(scrape_entire_table())
