import asyncio
import json
import os
import threading
from collections import defaultdict
import datetime

from scrape_commoditymarketlive_com import scrape_all_states as scrape_all_states_commoditymarketlive
from scrape_commodityonline_com import scrape_all_states as scrape_all_states_commodityonline
from scrape_mandiprices_in import scrape_mandiprices
from scrape_agmarknet_gov_in import scrape_all_states as scrape_all_states_agmarknet

results = {
    "commoditymarketlive": None,
    "commodityonline": None,
    "mandiprices": None,
    "agmarknet": None
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

def run_agmarknet():
    try:
        print("🚀 Starting Agmarknet scraper", flush=True)
        results["agmarknet"] = asyncio.run(scrape_all_states_agmarknet())
    except Exception as e:
        print(f"❌ Error in Agmarknet scraper: {e}", flush=True)

def calculate_average(values):
    valid = [v for v in values if isinstance(v, (int, float)) and v > 0]
    if not valid:
        return 0
    return round(sum(valid) / len(valid), 2)

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
            values = [e.get(key, 0) for e in entries if isinstance(e.get(key), (int, float))]
            avg_entry[key] = calculate_average(values)
        output.append(avg_entry)

    return sorted(output, key=lambda x: x["State"])

def main():
    print("🔁 Launching all scrapers...", flush=True)

    t1 = threading.Thread(target=run_commoditymarketlive)
    t2 = threading.Thread(target=run_commodityonline)
    t3 = threading.Thread(target=run_mandiprices)
    t4 = threading.Thread(target=run_agmarknet)

    t1.start()
    t2.start()
    t3.start()
    t4.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()

    print("💾 Saving JSON to /docs", flush=True)
    os.makedirs("docs", exist_ok=True)

    if results["commoditymarketlive"]:
        with open("docs/result_commoditymarketlive_in.json", "w") as f:
            json.dump(results["commoditymarketlive"], f, indent=2)

    if results["commodityonline"]:
        with open("docs/result_commodityonline_in.json", "w") as f:
            json.dump(results["commodityonline"], f, indent=2)

    if results["mandiprices"]:
        with open("docs/result_mandiprices_in.json", "w") as f:
            json.dump(results["mandiprices"], f, indent=2)

    if results["agmarknet"]:
        with open("docs/result_agmarknet_gov_in.json", "w") as f:
            json.dump(results["agmarknet"], f, indent=2)

    # ✅ Combine all for per-state average
    per_state_avg = compute_per_state_averages(
        results["commoditymarketlive"],
        results["commodityonline"],
        results["mandiprices"],
        results["agmarknet"]
    )
    with open("docs/combined_averages.json", "w") as f:
        json.dump(per_state_avg, f, indent=2)

    # ✅ Save run timestamp
    timestamp_data = {"last_run": datetime.datetime.utcnow().isoformat() + "Z"}
    with open("docs/run_timestamp.json", "w") as f:
        json.dump(timestamp_data, f, indent=2)

    # ✅ Save failure report
    failed = {}
    for key in results:
        if results[key] is None:
            failed[f"{key}_scraper"] = "Failed"

    with open("docs/status_report.json", "w") as f:
        json.dump(failed if failed else None, f, indent=2)

    print("✅ All done!", flush=True)

if __name__ == "__main__":
    main()
