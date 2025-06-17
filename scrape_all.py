import asyncio
import json
import os
import threading

from scrape_live import scrape_all_states as scrape_live
from scrape_online import scrape_all_states as scrape_online

results = {"live": None, "online": None}

def run_live():
    print("🚀 Starting Live scraper")
    results["live"] = asyncio.run(scrape_live())

def run_online():
    print("🚀 Starting Online scraper")
    results["online"] = asyncio.run(scrape_online())

def main():
    print("🔄 Launching both scrapers (Live & Online)...")
    t1 = threading.Thread(target=run_live)
    t2 = threading.Thread(target=run_online)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    os.makedirs("docs", exist_ok=True)
    with open("docs/live_prices.json", "w") as f:
        json.dump(results["live"], f, indent=2)
    with open("docs/online_prices.json", "w") as f:
        json.dump(results["online"], f, indent=2)

    print("✅ Scraping complete! JSON files saved to /docs")

if __name__ == "__main__":
    main()
