import asyncio
import json
import os
import threading
from collections import defaultdict
import datetime

from scrape_commoditymarketlive_com import scrape_all_states as scrape_all_states_commoditymarketlive
from scrape_commodityonline_com import scrape_all_states as scrape_all_states_commodityonline
from scrape_mandiprices_in import scrape_mandiprices

results = {
    "commoditymarketlive": None,
    "commodityonline": None,
    "mandiprices": None
}

def run_commoditymarketlive():
    try:
        print("🚀 Starting CommodityMarketLive scraper", flush=True)
        results["commoditymarketlive"] = asyncio.run(scrape_all_states_commoditymarketlive())
    except Exception as e:
        print(f"❌ Error in CommodityMarketLive scraper: {e}", flush=True)

def run_commodityonline():
    try:
        print("🚀 Starting CommodityOnline scraper", flush=True)
        results["commodityonline"] = asyncio.run(scrape_all_states_commodityonline())
    except Exception as e:
        print(f"❌ Error in CommodityOnline scraper: {e}", flush=True)

def run_mandiprices():
    try:
        print("🚀 Starting MandiPrices scraper", flush=True)
        results["mandiprices"] = asyncio.run(scrape_mandiprices(return_results=True))
    except Exception as e:
        print(f"❌ Error in MandiPrices scraper: {e}", flush=True)

def calculate_average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)

def compute_per_state_averages(*sources):
    merged = defaultdict(list)
    for source in sources:
        for entry in source or []:
            state = entry.get("State")
            if state:
                merged[state].append(entry)

    output = []
    for state, entries in merged.items():
        avg_entry = {"State": state}
        for key in ["Current_Price", "Minimum_Price", "Maximum_Price"]:
            values = [e[key] for e in entries if e.get(key) is not None]
            avg_entry[key] = calculate_average(values)
        output.append(avg_entry)

    return sorted(output, key=lambda x: x["State"])

def main():
    print("🔁 Launching all scrapers...", flush=True)

    t1 = threading.Thread(target=run_commoditymarketlive)
    t2 = threading.Thread(target=run_commodityonline)
    t3 = threading.Thread(target=run_mandiprices)
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()

    print("💾 Saving JSON to /docs", flush=True)
    os.makedirs("docs", exist_ok=True)
    with open("docs/result_commoditymarketlive_in.json", "w") as f:
        json.dump(results["commoditymarketlive"], f, indent=2)
    with open("docs/result_commodityonline_in.json", "w") as f:
        json.dump(results["commodityonline"], f, indent=2)
    with open("docs/result_mandiprices_in.json", "w") as f:
        json.dump(results["mandiprices"], f, indent=2)

    per_state_avg = compute_per_state_averages(
        results["commoditymarketlive"],
        results["commodityonline"],
        results["mandiprices"]
    )
    with open("docs/combined_averages.json", "w") as f:
        json.dump(per_state_avg, f, indent=2)

    timestamp_data = {"last_run": datetime.datetime.utcnow().isoformat() + "Z"}
    with open("docs/run_timestamp.json", "w") as f:
        json.dump(timestamp_data, f, indent=2)

    print("✅ All done!", flush=True)

if __name__ == "__main__":
    main()
