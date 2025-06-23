import asyncio
import json
import os
import threading
from collections import defaultdict
import datetime

from scrape_commoditymarketlive_com import scrape_all_states as scrape_all_states_commoditymarketlive
from scrape_commodityonline_com import scrape_all_states as scrape_all_states_commodityonline

results = {"commoditymarketlive": None, "commodityonline": None}

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

def calculate_average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)

def compute_per_state_averages(commoditymarketlive_data, commodityonline_data):
    merged = defaultdict(list)

    for source in [commoditymarketlive_data, commodityonline_data]:
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
    print("🔁 Launching both scrapers (CommodityMarketLive & CommodityOnline)...", flush=True)

    t1 = threading.Thread(target=run_commoditymarketlive)
    t2 = threading.Thread(target=run_commodityonline)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("💾 Saving JSON to /docs", flush=True)
    os.makedirs("docs", exist_ok=True)
    with open("docs/result_commoditymarketlive_in.json", "w") as f:
        json.dump(results["commoditymarketlive"], f, indent=2)
    with open("docs/result_commodityonline_in.json", "w") as f:
        json.dump(results["commodityonline"], f, indent=2)

    per_state_avg = compute_per_state_averages(results["commoditymarketlive"], results["commodityonline"])
    with open("docs/combined_averages.json", "w") as f:
        json.dump(per_state_avg, f, indent=2)

    timestamp_data = {"last_run": datetime.datetime.utcnow().isoformat() + "Z"}
    with open("docs/run_timestamp.json", "w") as f:
        json.dump(timestamp_data, f, indent=2)

    print("✅ All done!", flush=True)

if __name__ == "__main__":
    main()
