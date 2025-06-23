import asyncio, json, re
from statistics import mean
from collections import defaultdict
from playwright.async_api import async_playwright
import nest_asyncio

nest_asyncio.apply()

def parse_price(text):
    match = re.search(r"[\d,.]+", text)
    return float(match.group(0).replace(",", "")) if match else None

async def retry(action, label="", attempts=3, wait=1000):
    for i in range(attempts):
        try:
            return await action()
        except Exception as e:
            print(f"Retry {i+1}/{attempts} failed: {label} → {e}")
            await asyncio.sleep(wait / 1000)
    raise Exception(f"Failed after {attempts} attempts: {label}")

async def select_if_needed(page, label_text, desired_option):
    try:
        await page.wait_for_timeout(1000)
        button = page.locator(f'button[role="combobox"]:has-text("{label_text}")')
        await retry(lambda: button.wait_for(timeout=8000), f"wait for dropdown '{label_text}'")
        current = await button.inner_text()
        if desired_option.lower() in current.lower():
            print(f"Already selected: '{desired_option}'")
            return
        print(f"Selecting '{desired_option}' from '{label_text}'")
        await button.click()
        await retry(lambda: page.get_by_role("option", name=desired_option, exact=True).is_visible(), f"wait for option '{desired_option}'", wait=1000)
        await page.get_by_role("option", name=desired_option, exact=True).click()
        await page.wait_for_timeout(1500)

        # 🧠 Confirm selection applied
        confirmed = await button.inner_text()
        if desired_option.lower() not in confirmed.lower():
            raise Exception(f"Post-check failed: '{desired_option}' not selected in '{label_text}' → got '{confirmed}'")
    except Exception as e:
        print(f"Error: Dropdown failed [{label_text} → {desired_option}]: {e}")
        raise

async def scrape_mandiprices(return_results=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await retry(lambda: page.goto("https://www.mandiprices.in/", timeout=60000), "navigate to site")
            await page.wait_for_timeout(3000)

            await select_if_needed(page, "All Commodities", "Potato")
            await select_if_needed(page, "All States", "All States")
            await select_if_needed(page, "Price in", "Price in Quintal")
            await select_if_needed(page, "Paginated", "Scroll")

            await retry(lambda: page.wait_for_selector("table tbody tr", timeout=15000), "wait for table")
            await page.wait_for_timeout(3000)

            rows = await page.query_selector_all("table tbody tr")
            print(f"Found {len(rows)} table rows")

            raw_data = []
            for idx, row in enumerate(rows):
                try:
                    cols = await row.query_selector_all("td")
                    if len(cols) < 11:
                        continue
                    try:
                        text = [await col.inner_text() for col in cols]
                    except Exception as e:
                        print(f"Error: Failed to extract row #{idx}: {e}")
                        continue

                    raw_data.append({
                        "State": text[1].strip(),
                        "Minimum_Price": parse_price(text[8]),
                        "Maximum_Price": parse_price(text[9]),
                        "Modal_Price": parse_price(text[10])
                    })
                except Exception as e:
                    print(f"Error: Row #{idx} failed: {e}")
                    continue

        except Exception as e:
            print(f"Critical scrape failure: {e}")
            await browser.close()
            return []

        await browser.close()

        grouped = defaultdict(list)
        for item in raw_data:
            grouped[item["State"]].append(item)

        averaged_data = []
        for state, items in grouped.items():
            min_vals = [i["Minimum_Price"] for i in items if i["Minimum_Price"] and i["Minimum_Price"] <= 5500]
            max_vals = [i["Maximum_Price"] for i in items if i["Maximum_Price"] and i["Maximum_Price"] <= 5500]
            modal_vals = [i["Modal_Price"] for i in items if i["Modal_Price"] and i["Modal_Price"] <= 5500]

            averaged_data.append({
                "State": state,
                "Minimum_Price": round(mean(min_vals)) if min_vals else 0,
                "Maximum_Price": round(mean(max_vals)) if max_vals else 0,
                "Current_Price": round(mean(modal_vals)) if modal_vals else 0
            })

        states = [
            "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", "chattisgarh",
            "delhi", "gujarat", "haryana", "himachal-pradesh", "jharkhand",
            "karnataka", "kerala", "madhya-pradesh", "maharashtra", "manipur",
            "meghalaya", "mizoram", "nagaland", "odisha", "punjab",
            "rajasthan", "sikkim", "tamil-nadu", "telangana", "tripura",
            "uttar-pradesh", "uttrakhand", "west-bengal"
        ]

        normalized = {}
        mapping = {"nct-of-delhi": "delhi", "uttarakhand": "uttrakhand"}

        for item in averaged_data:
            raw = item["State"].strip().lower().replace(" ", "-")
            name = mapping.get(raw, raw)
            normalized[name] = {
                "State": name,
                "Minimum_Price": item["Minimum_Price"],
                "Maximum_Price": item["Maximum_Price"],
                "Current_Price": item["Current_Price"]
            }

        final = []
        for state in states:
            final.append(normalized.get(state, {
                "State": state,
                "Minimum_Price": 0,
                "Maximum_Price": 0,
                "Current_Price": 0
            }))

        return final

if __name__ == "__main__":
    asyncio.run(scrape_mandiprices())
