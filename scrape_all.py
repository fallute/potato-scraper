import asyncio
import json
import os
import threading

from scrape_live import scrape_all_states as scrape_live
from scrape_online import scrape_all_states as scrape_online

results = {"live": None, "online": None}

def run_live():
    results["live"] = asyncio.run(scrape_live())

def run_online():
    results["online"] = asyncio.run(scrape_online())

def main():
    t1 = threading.Thread(target=run_live)
    t2 = threading.Thread(target=run_online)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    os.makedirs("static", exist_ok=True)
    with open("static/live_prices.json", "w") as f:
        json.dump(results["live"], f, indent=2)
    with open("static/online_prices.json", "w") as f:
        json.dump(results["online"], f, indent=2)

    print("✅ Scraping complete!")

if __name__ == "__main__":
    main()
