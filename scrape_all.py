import asyncio
import json
import os
import threading
from collections import defaultdict
import datetime  # moved import here for cleanliness

from scrape_live import scrape_all_states as scrape_live
from scrape_online import scrape_all_states as scrape_online

results = {"live": None, "online": None}

def run_live():
    try:
        print("🚀 Starting Live scraper", flush=True)
        results["live"] = asyncio.run(scrape_live())
    except Exception as e:
        print(f"❌ Error in live scraper: {e}", flush=True)

def run_online():
    try:
        print("🚀 Starting Online scraper", flush=True)
        results["online"] = asyncio.run(scrape_online())
    except Exception as e:
        print(f"❌ Error in online scraper: {e}", flush=True)

def calculate_average(values):
    if not values:
        return None
    return round(sum(values) / len(values), 2)

def compute_per_state_averages(live_data, online_data):
    merged = defaultdict(list)

    for source in [live_data, online_data]:
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
    print("🔁 Launching both scrapers (Live & Online)...", flush=True)

    t1 = threading.Thread(target=run_live)
    t2 = threading.Thread(target=run_online)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("💾 Saving JSON to /docs", flush=True)
    os.makedirs("docs", exist_ok=True)
    with open("docs/live_prices.json", "w") as f:
        json.dump(results["live"], f, indent=2)
    with open("docs/online_prices.json", "w") as f:
        json.dump(results["online"], f, indent=2)

    per_state_avg = compute_per_state_averages(results["live"], results["online"])
    with open("docs/combined_averages.json", "w") as f:
        json.dump(per_state_avg, f, indent=2)

    # === Added: Save scraper run timestamp JSON ===
    timestamp_data = {"last_run": datetime.datetime.utcnow().isoformat() + "Z"}
    with open("docs/run_timestamp.json", "w") as f:
        json.dump(timestamp_data, f, indent=2)

    print("✅ All done!", flush=True)

if __name__ == "__main__":
    main()
