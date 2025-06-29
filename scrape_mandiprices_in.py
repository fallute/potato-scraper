import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


# ... your existing imports and logic ...

import asyncio, re, random
from statistics import mean
from collections import defaultdict
from playwright.async_api import async_playwright
import nest_asyncio

nest_asyncio.apply()

def parse_price(text):
    match = re.search(r"[\d,.]+", text)
    return float(match.group(0).replace(",", "")) if match else None

async def wait_random(label=None):
    delay = random.randint(5, 8)
    print(f"Waiting {delay}s" + (f" after {label}" if label else ""))
    await asyncio.sleep(delay)

async def retry(action, label="", attempts=2, wait=1000):
    for i in range(attempts):
        try:
            return await action()
        except Exception as e:
            print(f"Retry {i+1}/{attempts} failed: {label} → {e}")
            await asyncio.sleep(wait / 1000)
    raise Exception(f"Failed after {attempts} attempts: {label}")

async def select_by_label(page, label_text, desired_option):
    try:
        await wait_random(f"{label_text} dropdown")

        buttons = page.locator('xpath=//button[@role="combobox"]')
        count = await buttons.count()
        target = None

        for i in range(count):
            try:
                span = buttons.nth(i).locator("xpath=.//span")
                text = await span.inner_text()
                if label_text.lower() in text.lower():
                    current_text = await buttons.nth(i).text_content() or ""
                    if desired_option.lower() in current_text.lower():
                        print(f"Already selected: '{desired_option}'")
                        return
                    target = buttons.nth(i)
                    break
            except:
                continue

        if target is None:
            for i in range(count):
                try:
                    current_text = await buttons.nth(i).text_content() or ""
                    if desired_option.lower() in current_text.lower():
                        print(f"Already selected: '{desired_option}'")
                        return
                except:
                    continue
            print(f"Skipping: Dropdown button with label containing '{label_text}' not found")
            return

        print(f"Selecting '{desired_option}' from '{label_text}'")
        await target.click()

        if label_text.lower() == "all commodities":
            print("'All Commodities' dropdown opened, waiting 11s before selecting 'Potato'")
            await asyncio.sleep(11)
        elif label_text.lower() == "paginated":
            print("'Paginated' dropdown opened, waiting 11s before selecting 'Scroll'")
            await asyncio.sleep(11)
        else:
            await retry(
                lambda: page.locator('xpath=//div[@data-radix-popper-content-wrapper]').wait_for(state="visible", timeout=10000),
                f"wait for dropdown '{label_text}' content to appear"
            )
            delay = random.randint(5, 8)
            print(f"'{label_text}' visible, waiting extra {delay}s before selecting '{desired_option}'...")
            await asyncio.sleep(delay)

        await retry(
            lambda: page.locator(f'xpath=//div[@role="option" and contains(.,"{desired_option}")]').first.wait_for(state="visible", timeout=8000),
            f"wait for option '{desired_option}' to be visible"
        )
        option = page.locator(f'xpath=//div[@role="option" and contains(.,"{desired_option}")]').first
        await retry(lambda: option.scroll_into_view_if_needed(), f"scroll '{desired_option}' into view")
        await retry(lambda: option.click(), f"click option '{desired_option}'")

        await wait_random(f"after selecting '{desired_option}'")

        confirmed = await target.text_content() or ""
        if desired_option.lower() not in confirmed.lower():
            print(f"Warning: Confirmed selection is '{confirmed}', expected '{desired_option}'")

        # Re-check Potato if we just selected Scroll
        if label_text.lower() == "paginated":
            print("Re-checking 'All Commodities' → 'Potato' after Scroll selection")
            await select_by_label(page, "All Commodities", "Potato")

    except Exception as e:
        print(f"Error: Dropdown failed [{label_text} → {desired_option}]: {e}")

async def scrape_mandiprices(return_results=False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await retry(lambda: page.goto("https://www.mandiprices.in/", timeout=60000), "navigate to site")
            await retry(lambda: page.locator('xpath=//button[@role="combobox"]').first.wait_for(state="visible", timeout=10000), "wait for page to stabilize")
            await wait_random("after page load")

            await select_by_label(page, "All Commodities", "Potato")
            await select_by_label(page, "All States", "All States")
            await select_by_label(page, "Price in Kg", "Price in Quintal")
            await select_by_label(page, "Paginated", "Scroll")

            await retry(lambda: page.locator('xpath=//table//tbody//tr').first.wait_for(state="visible", timeout=10000), "wait for table to appear")
            await wait_random("after table appears")

            rows = await page.query_selector_all('xpath=//table//tbody//tr')
            print(f"Found {len(rows)} table rows")

            raw_data = []
            for idx, row in enumerate(rows):
                try:
                    cols = await row.query_selector_all("xpath=.//td")
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

        mapping = {"nct-of-delhi": "delhi", "uttarakhand": "uttrakhand"}
        normalized = {}

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
        for state in sorted(states):
            final.append(normalized.get(state, {
                "State": state,
                "Minimum_Price": 0,
                "Maximum_Price": 0,
                "Current_Price": 0
            }))

        print("Scraping complete. Final results prepared.")
        return final if return_results else None

if __name__ == "__main__":
    asyncio.run(scrape_mandiprices())
