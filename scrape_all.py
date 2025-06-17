import asyncio
import json
import os
import threading

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

    print("✅ All done!", flush=True)

if __name__ == "__main__":
    main()
